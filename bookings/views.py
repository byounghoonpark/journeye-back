from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils.timezone import now
import random
import string

from accounts.models import UserProfile
from accounts.permissions import IsAdminOrManager
from .models import CheckIn, Reservation, HotelRoom
from spaces.models import BaseSpace, HotelRoomLog
from hotel_admin import settings
from .serializers import CheckInRequestSerializer, CheckInSerializer, CheckOutRequestSerializer
from drf_yasg import openapi


def generate_unique_temp_code():
    """DB에 없는 6자리 숫자 임시코드를 생성"""
    while True:
        temp_code = ''.join(random.choices(string.digits, k=6))
        if not CheckIn.objects.filter(temp_code=temp_code).exists():
            return temp_code


class CheckInViewSet(viewsets.ViewSet):
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
    def create(self, request):
        """체크인 생성 로직"""
        user = request.user
        serializer = CheckInRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # 호텔 및 객실 조회
        hotel, room = self.get_hotel_and_room(validated_data["hotel_id"], validated_data["room_number"])

        # 권한 체크
        if not (user.is_staff or hotel.managers.filter(id=user.id).exists()):
            return Response({"error": "체크인 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        # 예약된 고객 체크인
        if validated_data.get("reservation_id") and validated_data.get("user_id"):
            return self.check_in_reserved_customer(validated_data, room)

        # 워크인 고객 체크인
        return self.check_in_walkin_customer(validated_data, room)

    transaction.atomic

    def check_out(self, request):
        """객실 번호로 체크아웃 처리"""
        serializer = CheckOutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # 현재 체크인 중인 고객 찾기
        check_in = CheckIn.objects.filter(
            hotel_room__room_number=validated_data["room_number"],
            check_out_date__gte=now().date()
        ).first()

        if not check_in:
            return Response({"error": "현재 체크인 중인 고객이 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 현재 시간 기준으로 체크아웃 처리
        check_in.check_out_date = now().date()
        check_in.check_out_time = now().time()
        check_in.save()

        # 객실 상태 변경 및 로그 기록
        self.update_room_status(check_in.hotel_room, check_in.user.username, "체크아웃")

        return Response({"message": "체크아웃 완료"}, status=status.HTTP_200_OK)

    def get_hotel_and_room(self, hotel_id, room_number):
        """호텔 및 객실 정보 조회"""
        hotel = get_object_or_404(BaseSpace, id=hotel_id)
        room = get_object_or_404(HotelRoom, room_number=room_number, room_type__basespace=hotel)
        return hotel, room

    @transaction.atomic
    def check_in_reserved_customer(self, validated_data, room):
        """예약된 고객 체크인 처리"""
        reservation = get_object_or_404(
            Reservation,
            id=validated_data["reservation_id"],
            user_id=validated_data["user_id"],
            space=room.room_type
        )

        if reservation.end_date < now().date():
            return Response({"error": "만료된 예약입니다."}, status=status.HTTP_400_BAD_REQUEST)

        check_in = self.create_check_in(reservation.user, room, reservation, validated_data["end_date"], validated_data["end_time"])

        return Response({"message": "체크인 완료", "temp_code": check_in.temp_code}, status=status.HTTP_201_CREATED)

    def check_in_walkin_customer(self, validated_data, room):
        """워크인 고객 체크인 처리"""
        temp_code = generate_unique_temp_code()

        new_user = User.objects.create_user(
            username=f"walkin_{temp_code}",
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            password=generate_unique_temp_code(),
            email=validated_data["email"],
        )

        UserProfile.objects.create(
            user=new_user,
            phone_number=validated_data["phone"],
            nationality=validated_data["nationality"],
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

        check_in = self.create_check_in(new_user, room, reservation, validated_data["end_date"], validated_data["end_time"], temp_code)

        self.send_checkin_email(validated_data["email"], temp_code)

        return Response({"message": "워크인 고객 체크인 완료", "user_id": new_user.id, "temp_code": check_in.temp_code}, status=status.HTTP_201_CREATED)

    def create_check_in(self, user, room, reservation, end_date, end_time, temp_code=None):
        """체크인 객체 생성"""
        check_in = CheckIn.objects.create(
            user=user,
            hotel_room=room,
            reservation=reservation,
            check_in_date=now().date(),
            check_in_time=now().time(),
            check_out_date=end_date,
            check_out_time=end_time,
            temp_code=temp_code
        )

        # 객실 상태 변경 및 로그 기록
        self.update_room_status(room, user.username, "이용중")

        return check_in

    def update_room_status(self, room, username, status):
        """객실 상태 업데이트 및 로그 추가"""
        room.status = status
        room.save()

        action = "체크인" if status == "이용중" else "체크아웃"
        HotelRoomLog.objects.create(
            hotel_room=room,
            log_content=f"{username}님이 {action}하였습니다."
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
