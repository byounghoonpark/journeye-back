import random
import string
from datetime import timedelta

from rest_framework.views import APIView

from hotel_admin import settings

from .models import CheckIn, Reservation, HotelRoom, Review, ReviewPhoto
from django.contrib.auth.models import User
from spaces.models import BaseSpace, HotelRoomUsage, HotelRoomMemo, HotelRoomHistory
from chat.models import ChatRoom
from accounts.models import UserProfile
from accounts.permissions import IsAdminOrManager

from django.db import transaction
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.utils.timezone import now

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from rest_framework import viewsets, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action

from .serializers import CheckInRequestSerializer, CheckInSerializer, CheckOutRequestSerializer, ReviewSerializer, \
    CheckInUpdateSerializer, CheckInCustomerUpdateSerializer, ReservationSerializer, UserReservationSerializer, \
    CheckInReservationSerializer


def generate_unique_temp_code():
    """DB에 없는 6자리 숫자 임시코드를 생성"""
    while True:
        temp_code = ''.join(random.choices(string.digits, k=6))
        if not CheckIn.objects.filter(temp_code=temp_code).exists():
            return temp_code


class CheckInAndOutViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    @swagger_auto_schema(
        request_body=CheckInRequestSerializer,
        responses={
            201: CheckInSerializer,
            400: openapi.Response(description="잘못된 요청 또는 만료된 예약"),
            403: openapi.Response(description="체크인 권한 없음"),
        },
        operation_summary="체크인 처리",
        operation_description="예약된 고객 또는 워크인 고객의 체크인을 처리합니다.",
    )
    @transaction.atomic
    def check_in(self, request):
        """체크인 생성 로직"""
        user = request.user
        serializer = CheckInRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # 호텔 및 객실 조회
        hotel, room = self.get_hotel_and_room(validated_data["hotel_id"], validated_data["room_id"])

        # 권한 체크
        if not (user.is_staff or hotel.managers.filter(id=user.id).exists()):
            return Response({"error": "체크인 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        # 예약된 고객 체크인
        if validated_data.get("reservation_id") and validated_data.get("user_id"):
            return self.check_in_reserved_customer(validated_data, room)

        # 워크인 고객 체크인
        return self.check_in_walkin_customer(validated_data, room)

    @swagger_auto_schema(
        request_body=CheckOutRequestSerializer,
        responses={
            200: openapi.Response(description="체크아웃 완료"),
            400: openapi.Response(description="잘못된 요청 (체크인 내역 없음)"),
            403: openapi.Response(description="권한 없음"),
        },
        operation_summary="체크아웃 처리",
        operation_description="객실 번호를 입력하면 해당 객실의 현재 체크인 고객을 체크아웃합니다.",
    )
    @transaction.atomic
    def check_out(self, request):
        """객실 번호로 체크아웃 처리"""
        serializer = CheckOutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # 현재 체크인 중인 고객 찾기 (체크아웃되지 않은 고객)
        check_in = CheckIn.objects.filter(
            hotel_room__id=validated_data["room_id"],
            checked_out=False
        ).order_by('-check_in_date').first()  # 가장 최근 체크인한 고객 우선 선택

        if not check_in:
            return Response({"error": "현재 체크인 중인 고객이 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 현재 시간 기준으로 체크아웃 처리
        check_in.check_out_date = now().date()
        check_in.check_out_time = now().time()
        check_in.checked_out = True
        check_in.save()

        # 객실 상태 변경 및 로그 기록
        self.update_room_status(check_in.hotel_room, "체크 아웃")

        chat_room = ChatRoom.objects.filter(checkin=check_in).first()
        if chat_room:
            chat_room.is_active = False
            chat_room.save()

        return Response({
            "message": "체크아웃 완료" + (" 및 채팅방 비활성화됨" if chat_room else ""),
            "chat_room_status": "비활성화됨" if chat_room else "채팅방 없음"
        }, status=status.HTTP_200_OK)

    def get_hotel_and_room(self, hotel_id, room_id):
        """호텔 및 객실 정보 조회"""
        hotel = get_object_or_404(BaseSpace, id=hotel_id)
        room = get_object_or_404(HotelRoom, id=room_id, room_type__basespace=hotel)
        return hotel, room

    def check_in_reserved_customer(self, validated_data, room):
        """예약된 고객 체크인 처리"""
        existing_check_in = CheckIn.objects.filter(
            hotel_room=room,
            checked_out=False
        ).exists()

        if existing_check_in:
            return Response({"error": "현재 체크인된 고객이 있어 체크인할 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        reservation = get_object_or_404(
            Reservation,
            id=validated_data["reservation_id"],
            user_id=validated_data["user_id"],
            space=room.room_type
        )

        if reservation.end_date < now().date():
            return Response({"error": "만료된 예약입니다."}, status=status.HTTP_400_BAD_REQUEST)

        check_in = self.create_check_in(user=reservation.user, room=room, reservation=reservation,
                                        end_date=validated_data["end_date"], end_time=validated_data["end_time"], is_day_use=validated_data["is_day_use"])

        return Response({"message": "체크인 완료", "temp_code": check_in.temp_code}, status=status.HTTP_201_CREATED)

    def check_in_walkin_customer(self, validated_data, room):
        """워크인 고객 체크인 처리"""
        existing_check_in = CheckIn.objects.filter(
            hotel_room=room,
            checked_out=False
        ).exists()

        if existing_check_in:
            return Response({"error": "현재 체크인된 고객이 있어 체크인할 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        temp_code = generate_unique_temp_code()

        new_user = User.objects.create_user(
            username=validated_data["guest_name"],
            password=generate_unique_temp_code(),
            email=validated_data["email"],
        )

        UserProfile.objects.create(
            user=new_user,
            phone_number=validated_data["phone"],
            nationality=validated_data["nationality"],
            language=validated_data["language"],
            email_code=temp_code
        )

        reservation = Reservation.objects.create(
            user=new_user,
            space=room.room_type,
            start_date=validated_data["start_date"],
            start_time=validated_data["start_time"],
            end_date=validated_data["end_date"],
            end_time=validated_data["end_time"],
            people=1
        )

        check_in = self.create_check_in(
            user=new_user, room=room, reservation=reservation, end_date=validated_data["end_date"],
            end_time=validated_data["end_time"], is_day_use=validated_data["is_day_use"], temp_code=temp_code
        )

        self.send_checkin_email(validated_data["email"], temp_code)

        return Response({"message": "워크인 고객 체크인 완료", "user_id": new_user.id, "temp_code": check_in.temp_code}, status=status.HTTP_201_CREATED)

    def create_check_in(self, user, room, reservation, end_date, end_time, is_day_use, temp_code=None):
        """체크인 객체 생성"""
        check_in = CheckIn.objects.create(
            user=user,
            hotel_room=room,
            reservation=reservation,
            check_in_date=now().date(),
            check_in_time=now().time(),
            check_out_date=end_date,
            check_out_time=end_time,
            temp_code=temp_code,
            is_day_use=is_day_use
        )

        # 객실 상태 변경 및 로그 기록
        self.update_room_status(room, "체크인")

        return check_in

    def update_room_status(self, room, status):
        """객실 상태 업데이트 및 로그 추가"""
        HotelRoomUsage.objects.create(
            hotel_room=room,
            usage_content=status
        )

    def send_checkin_email(self, email, temp_code):
        """체크인 이메일 발송"""
        send_mail(
            subject="호텔 체크인 임시 코드 발급",
            message=f"안녕하세요,\n\n임시 로그인 코드는 {temp_code} 입니다.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

    @swagger_auto_schema(
        request_body=CheckInUpdateSerializer,
        responses={
            200: CheckInSerializer,
            400: openapi.Response(description="잘못된 요청"),
            403: openapi.Response(description="권한 없음"),
            404: openapi.Response(description="체크인 정보 없음"),
        },
        operation_summary="체크인 정보 수정",
        operation_description="체크인 키값을 받아 is_day_use, 체크인 날짜, 체크아웃 날짜, 인원을 수정합니다.",
    )
    @action(detail=True, methods=['patch'], url_path='update-checkin')
    def update_check_in(self, request):
        check_in_id = request.data.get('id')
        check_in = get_object_or_404(CheckIn, pk=check_in_id)
        serializer = CheckInUpdateSerializer(check_in, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # 예약 인원 업데이트
        if 'reservation' in request.data and 'people' in request.data['reservation']:
            check_in.reservation.people = request.data['reservation']['people']
            check_in.reservation.save()

        return Response(CheckInSerializer(check_in).data, status=status.HTTP_200_OK)


    @swagger_auto_schema(
        request_body=CheckInCustomerUpdateSerializer,
        responses={
            200: CheckInSerializer,
            400: openapi.Response(description="잘못된 요청"),
            403: openapi.Response(description="권한 없음"),
            404: openapi.Response(description="체크인 정보 없음"),
        },
        operation_summary="체크인 고객 정보 수정",
        operation_description="체크인 키값을 받아 고객의 이름, 이메일, 전화번호, 국적을 수정합니다.",
    )
    @action(detail=True, methods=['patch'], url_path='update-customer-info')
    def update_customer_info(self, request):
        check_in_id = request.data.get('id')
        check_in = get_object_or_404(CheckIn, pk=check_in_id)
        user = check_in.user
        user_profile = get_object_or_404(UserProfile, user=user)

        serializer = CheckInCustomerUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        if 'guest_name' in validated_data:
            user.username = validated_data['guest_name']
            user.save()

        if 'email' in validated_data:
            user.email = validated_data['email']
            user.save()

        if 'phone' in validated_data:
            user_profile.phone_number = validated_data['phone']
            user_profile.save()

        if 'nationality' in validated_data:
            user_profile.nationality = validated_data['nationality']
            user_profile.save()

        if 'language' in validated_data:
            user_profile.language = validated_data['language']
            user_profile.save()

        return Response(CheckInSerializer(check_in).data, status=status.HTTP_200_OK)


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    parser_classes = [MultiPartParser, FormParser]
    filterset_fields = ["basespace"]

    def get_queryset(self):
        queryset = Review.objects.all()
        basespace_id = self.request.query_params.get('basespace')
        if basespace_id:
            queryset = queryset.filter(check_in__reservation__space__basespace=basespace_id)
        return queryset

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated()]

    @swagger_auto_schema(
        operation_description="리뷰 리스트 조회 API",
        manual_parameters=[
            openapi.Parameter(
                'basespace',
                openapi.IN_QUERY,
                description="BaseSpace ID 필터 (예: ?basespace=1)",
                type=openapi.TYPE_INTEGER
            )
        ],
        responses={
            200: ReviewSerializer(many=True),
            400: openapi.Response(description="잘못된 요청"),
            403: openapi.Response(description="권한 없음"),
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


    @swagger_auto_schema(
        operation_description="리뷰 작성 API",
        request_body=ReviewSerializer,
        manual_parameters=[
            openapi.Parameter(
                "photos",
                openapi.IN_FORM,
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_FILE),
                description="리뷰 사진 업로드 (여러 파일 가능)"
            )
        ],
        responses={
            201: openapi.Response(description="리뷰 작성 성공"),
            400: openapi.Response(description="잘못된 요청"),
            403: openapi.Response(description="권한 없음"),
        }
    )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        check_in_id = request.data.get('check_in')
        check_in = get_object_or_404(CheckIn, id=check_in_id, user=request.user, checked_out=True)

        # 체크인 아이디당 하나의 리뷰만 작성할 수 있도록 검증
        if Review.objects.filter(check_in=check_in).exists():
            return Response({"error": "이미 이 체크인에 대한 리뷰가 존재합니다."}, status=status.HTTP_400_BAD_REQUEST)

        review = serializer.save(user=request.user, check_in=check_in)

        photos = request.FILES.getlist('photos')
        for photo in photos:
            ReviewPhoto.objects.create(review=review, image=photo)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class RoomUsageViewSet(viewsets.ViewSet):
    """
    특정 객실(pk)에 대해 오늘 기준 활성 체크인을 확인합니다.
    활성 체크인이 있으면 이용정보, 고객정보, 이용내역을 반환하고,
    없으면 객실상태, 메모, 최근 3일 이내의 객실이력을 반환합니다.
    """
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    @swagger_auto_schema(
        operation_summary="특정 객실 이용정보 조회",
        operation_description=(
                "URL의 pk로 전달된 특정 객실에 대해 오늘 기준 활성 체크인이 있는지 확인합니다. "
                "활성 체크인이 존재하면 이용정보(대실여부, 체크인/체크아웃 날짜 및 시간, 투숙인원)와 고객정보, 이용내역을 반환하며, "
                "없으면 객실상태, 메모, 최근 3일 이내의 객실이력을 반환합니다."
        ),
        responses={
            200: openapi.Response(description="조회 성공"),
            404: openapi.Response(description="해당 객실을 찾을 수 없음"),
        }
    )
    def retrieve(self, request, pk=None):
        today = now().date()
        room = get_object_or_404(HotelRoom, id=pk)

        # 오늘 기준 활성 체크인 조회
        active_checkin = CheckIn.objects.filter(
            hotel_room=room,
            # check_in_date__lte=today,
            # check_out_date__gte=today,
            checked_out=False
        ).order_by('-check_in_date').first()

        # 메모와 객실 이력은 항상 조회합니다.
        memos = HotelRoomMemo.objects.filter(hotel_room=room)
        memo_list = [
            {
                "memo_date": memo.memo_date.strftime("%Y-%m-%d"),
                "memo_content": memo.memo_content
            }
            for memo in memos
        ]
        three_days_ago = now() - timedelta(days=3)
        histories = HotelRoomHistory.objects.filter(
            hotel_room=room,
            history_date__gte=three_days_ago
        )
        history_list = [
            {
                "history_date": history.history_date.strftime("%Y-%m-%d %H:%M:%S"),
                "history_content": history.history_content
            }
            for history in histories
        ]

        data = {
            "room_status": room.status,
            "memo": memo_list,
            "room_history": history_list,
        }

        if active_checkin:
            # 활성 체크인이 있는 경우: 이용정보, 고객정보, 이용내역 추가
            usages = HotelRoomUsage.objects.filter(hotel_room=room)
            usage_list = [
                {
                    "usage_date": usage.usage_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "usage_content": usage.usage_content
                }
                for usage in usages
            ]
            user_profile = UserProfile.objects.get(user=active_checkin.user)
            usage_info = {
                "check_in_id": active_checkin.id,
                "is_day_use": active_checkin.is_day_use,
                "check_in_date": active_checkin.check_in_date.strftime("%Y-%m-%d"),
                "check_in_time": active_checkin.check_in_time.strftime(
                    "%H:%M:%S") if active_checkin.check_in_time else None,
                "check_out_date": active_checkin.check_out_date.strftime("%Y-%m-%d"),
                "check_out_time": active_checkin.check_out_time.strftime(
                    "%H:%M:%S") if active_checkin.check_out_time else None,
                "people": active_checkin.reservation.people,
            }
            guest_info = {
                "guest_name": active_checkin.user.username or active_checkin.user.get_full_name(),
                "guest_email": active_checkin.user.email,
                "guest_nationality": user_profile.nationality,
                "guest_language": user_profile.language,
                "guest_phone": user_profile.phone_number,
            }
            data["usage_info"] = usage_info
            data["guest_info"] = guest_info
            data["usage_list"] = usage_list
        else:
            data["usage_info"] = {}
            data["guest_info"] = {}
            data["usage_list"] = []

        return Response(data, status=200)


class HotelRoomStatusViewSet(viewsets.ViewSet):
    """
    특정 BaseSpace(호텔)에 대한 모든 객실 정보를 리스트로 조회합니다.
    - 호실(room_number)
    - 방타입(room_type)
    - 방 상태: 체크인 여부에 따라 '대실'/'숙박'(기간) 혹은 DB상의 객실 상태
    - 이용객 이름: 활성 체크인 시에만 표시
    - 메모: HotelRoomMemo 중 가장 최근 메모
    """
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    @swagger_auto_schema(
        operation_summary="객실 상태 리스트 조회",
        operation_description=(
                "특정 BaseSpace(호텔)에 대한 객실 상태를 조회합니다. "
                "basespace_id 쿼리 파라미터를 통해 호텔을 식별하며, "
                "객실별로 대실/숙박 여부, 이용객 이름, 메모 등을 반환합니다."
        ),
        manual_parameters=[
            openapi.Parameter(
                name='basespace_id',
                in_=openapi.IN_QUERY,
                description='BaseSpace(호텔) ID (예: ?basespace_id=1)',
                required=True,
                type=openapi.TYPE_INTEGER
            )
        ],
        responses={
            200: openapi.Response(description="객실 상태 리스트 조회 성공"),
            400: openapi.Response(description="basespace_id 파라미터 없음"),
            404: openapi.Response(description="BaseSpace 혹은 해당 객실을 찾을 수 없음")
        }
    )

    def list(self, request):
        # basespace_id를 쿼리 파라미터로 받아 특정 BaseSpace(호텔)의 객실만 조회
        basespace_id = request.query_params.get('basespace_id')
        if not basespace_id:
            return Response({"error": "basespace_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        # BaseSpace 조회
        basespace = get_object_or_404(BaseSpace, id=basespace_id)
        # 해당 BaseSpace에 속한 객실들
        rooms = HotelRoom.objects.filter(room_type__basespace=basespace)

        today = now().date()
        result = []

        for room in rooms:
            # 오늘 기준 활성 체크인(체크아웃되지 않고, 날짜 범위가 오늘을 포함)
            active_checkin = CheckIn.objects.filter(
                hotel_room=room,
                checked_out=False,
                # check_in_date__lte=today,
                # check_out_date__gte=today
            ).first()

            # 기본값 (활성 체크인이 없으면 DB상의 status 그대로)
            occupant_name = ""
            display_status = room.status
            start_date = ""
            end_date = ""
            occupant_nationality = ""

            # 활성 체크인이 있으면 상태/이용객명 갱신
            if active_checkin:
                occupant_name = active_checkin.user.get_full_name() or active_checkin.user.username
                start_date = active_checkin.check_in_date.strftime('%m/%d')
                end_date = active_checkin.check_out_date.strftime('%m/%d')
                if active_checkin.is_day_use:
                    display_status = "대실" if room.status is None else f"대실•{room.status}"
                else:
                    display_status = "숙박" if room.status is None else f"숙박•{room.status}"

                user_profile = UserProfile.objects.get(user=active_checkin.user)
                occupant_nationality = user_profile.nationality

            # 가장 최근 메모 1개만
            last_memo = HotelRoomMemo.objects.filter(hotel_room=room).order_by('-memo_date').first()
            memo_content = last_memo.memo_content if last_memo else ""

            result.append({
                "room_id": room.id,
                "room_number": room.room_number,
                "floor": room.floor.floor_number,
                "room_type": room.room_type.nickname if room.room_type.nickname else "",
                "status": display_status,  # 대실/숙박 여부 + 날짜, 또는 DB의 status
                "start_date": start_date,
                "end_date": end_date,
                "guest_name": occupant_name,
                "guest_nationality": occupant_nationality,
                "memo": memo_content,
            })

        return Response(result, status=status.HTTP_200_OK)


class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                name="basespace_id",
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="BaseSpace ID로 예약 리스트 필터링",
                required=False
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Reservation.objects.none()

        user = self.request.user
        user_profile = user.profile
        if user_profile.role == "GENERAL":
            return Reservation.objects.filter(user=user).order_by("-reservation_date")
        else:
            basespace_id = self.request.query_params.get("basespace_id")
            if basespace_id:
                return Reservation.objects.filter(
                    space__basespace_id=basespace_id
                ).order_by("-reservation_date")
            return Reservation.objects.none()


class ReservationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        reservations = Reservation.objects.filter(user=user)
        serializer = UserReservationSerializer(reservations, many=True)
        return Response(serializer.data)


class CheckInReservationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, checkin_id):
        checkin = get_object_or_404(CheckIn, id=checkin_id)
        serializer = CheckInReservationSerializer(checkin)
        return Response(serializer.data, status=status.HTTP_200_OK)
