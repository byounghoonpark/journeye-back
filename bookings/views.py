from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from django.contrib.auth.models import User
import random
import string
from rest_framework.generics import get_object_or_404
from bookings.models import Reservation
from spaces.models import Space
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class CheckInCreateView(APIView):
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_description="현장 체크인을 위한 Reservation 생성 API. "
                              "요청에 기존 유저의 user_id가 포함되어 있으면 해당 유저로 예약을 진행하며, "
                              "없으면 임시 유저를 생성하여 예약을 진행합니다.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'user_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='기존 유저 ID (선택 사항)'),
                'space_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='예약할 공간의 ID'),
                'check_in_date': openapi.Schema(type=openapi.FORMAT_DATE, description='체크인 날짜 (YYYY-MM-DD)'),
                'check_out_date': openapi.Schema(type=openapi.FORMAT_DATE, description='체크아웃 날짜 (YYYY-MM-DD)'),
                'people': openapi.Schema(type=openapi.TYPE_INTEGER, description='예약 인원수', default=1),
            },
            required=['space_id', 'check_in_date', 'check_out_date']
        ),
        responses={
            201: openapi.Response(
                description="Reservation이 성공적으로 생성됨",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='생성된 Reservation ID'),
                        'user': openapi.Schema(type=openapi.TYPE_STRING, description='예약에 사용된 유저 이름'),
                        'space': openapi.Schema(type=openapi.TYPE_STRING, description='예약한 공간 이름'),
                        'check_in_date': openapi.Schema(type=openapi.FORMAT_DATE, description='체크인 날짜'),
                        'check_out_date': openapi.Schema(type=openapi.FORMAT_DATE, description='체크아웃 날짜'),
                        'temp_code': openapi.Schema(type=openapi.TYPE_STRING, description='임시 6자리 승인번호'),
                    }
                )
            )
        }
    )

    def post(self, request):
        # 요청 데이터 추출
        user_id = request.data.get('user_id')
        space_id = request.data.get('space_id')
        check_in_date = request.data.get('check_in_date')
        check_out_date = request.data.get('check_out_date')
        people = request.data.get('people', 1)  # 예약 인원수, 기본값 1

        # user_id가 있으면 기존 유저 조회, 없으면 임시 유저 생성
        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            temp_username = 'temp_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            user = User.objects.create_user(username=temp_username, password='temporary_password')

        # 해당 space 조회
        space = get_object_or_404(Space, id=space_id)

        # Reservation 생성 (체크인과 예약을 Reservation으로 관리)
        reservation = Reservation.objects.create(
            user=user,
            space=space,
            start_date=check_in_date,
            end_date=check_out_date,
            people=people,
            temp_code=''.join(random.choices(string.digits, k=6))
        )

        return Response({
            'id': reservation.id,
            'user': reservation.user.username,
            'space': reservation.space.name,
            'check_in_date': reservation.start_date,
            'check_out_date': reservation.end_date,
            'temp_code': reservation.temp_code
        }, status=status.HTTP_201_CREATED)
