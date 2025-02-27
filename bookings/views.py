from django.contrib.auth.models import User
from django.core.mail import send_mail
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
from spaces.models import BaseSpace
from hotel_admin import settings
from .serializers import CheckInRequestSerializer, CheckInSerializer
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
    def create(self, request):
        user = request.user
        data = request.data
        reservation_id = data.get("reservation_id")
        user_id = data.get("user_id")
        hotel_id = data.get("hotel_id")
        room_number = data.get("room_number")
        start_date = data.get("start_date")
        start_time = data.get("start_time")
        end_date = data.get("end_date")
        end_time = data.get("end_time")
        natinality = data.get("natinality")
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        email = data.get("email")
        phone = data.get("phone")

        # 호텔 및 객실 찾기
        hotel = get_object_or_404(BaseSpace, id=hotel_id)
        room = get_object_or_404(HotelRoom, room_number=room_number, room_type__basespace=hotel)

        # 현재 요청한 사용자가 호텔 매니저 또는 어드민인지 확인
        if not (user.is_staff or hotel.managers.filter(id=user.id).exists()):
            return Response({"error": "체크인 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        # 현재 시간으로 체크인/체크아웃 시간 설정
        check_in_time = now().time()

        # 예약된 고객 체크인
        if user_id and reservation_id:
            reservation = get_object_or_404(Reservation, id=reservation_id, user_id=user_id, space=room.room_type)

            if reservation.end_date < now().date():
                return Response({"error": "만료된 예약입니다."}, status=status.HTTP_400_BAD_REQUEST)

            check_in = CheckIn.objects.create(
                user=reservation.user,
                hotel_room=room,
                reservation=reservation,
                check_in_date=now().date(),
                check_in_time=check_in_time,
                check_out_date=reservation.end_date,
                check_out_time=end_time
            )
            return Response({"message": "체크인 완료", "temp_code": check_in.temp_code}, status=status.HTTP_201_CREATED)

        # 워크인 고객 체크인 (새 유저 생성)
        temp_code = generate_unique_temp_code()
        new_user = User.objects.create_user(
            username=f"walkin_{temp_code}",
            first_name=first_name,
            last_name=last_name,
            password=generate_unique_temp_code(),
            email=email,
        )
        UserProfile.objects.create(
            user=new_user,
            phone_number=phone,
            natinality=natinality,
        )
        reservation = Reservation.objects.create(
            user=new_user,
            space=room.room_type,
            start_date=start_date,
            start_time=start_time,
            end_date=end_date,
            end_time=end_time,
            people=1
        )
        check_in = CheckIn.objects.create(
            user=new_user,
            hotel_room=room,
            reservation=reservation,
            check_in_date=now().date(),
            check_in_time=check_in_time,
            check_out_date=end_date,
            check_out_time=end_time,
            temp_code=temp_code
        )


        send_mail(
            subject="호텔 체크인 임시 코드 발급",
            message=f"안녕하세요,\n\n임시 로그인 코드는 {temp_code} 입니다.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        return Response({
            "message": "워크인 고객 체크인 완료",
            "user_id": new_user.id,
            "temp_code": check_in.temp_code
        }, status=status.HTTP_201_CREATED)
