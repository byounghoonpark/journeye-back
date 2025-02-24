from django.contrib.auth.models import User
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import UserProfile
from .serializers import UserRegistrationSerializer, HotelManagerAssignSerializer
from rest_framework.generics import get_object_or_404


class UserRegistrationView(APIView):
    @swagger_auto_schema(
        operation_description="사용자 회원가입 API",
        request_body=UserRegistrationSerializer,
        responses={
            201: openapi.Response(
                description="회원가입 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_INTEGER, description="유저 ID"),
                        "username": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 이름"),
                        "email": openapi.Schema(type=openapi.TYPE_STRING, description="이메일"),
                        "access_token": openapi.Schema(type=openapi.TYPE_STRING, description="액세스 토큰"),
                        "refresh_token": openapi.Schema(type=openapi.TYPE_STRING, description="리프레시 토큰"),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, description="응답 메시지"),
                    },
                ),
            ),
            400: openapi.Response(description="잘못된 요청"),
        },
    )
    def post(self, request):
        """ JWT 기반 회원가입 API """
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # JWT 토큰 생성
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            return Response({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "message": "회원가입이 완료되었습니다."
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AssignHotelManagerView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]  # 어드민만 접근 가능

    @swagger_auto_schema(
        operation_description="유저를 호텔 관리자로 변경하는 API (어드민만 가능)",
        responses={
            200: openapi.Response(description="호텔 관리자로 설정됨"),
            400: openapi.Response(description="잘못된 요청"),
            403: openapi.Response(description="권한 없음 (어드민만 가능)"),
        },
    )
    def post(self, request, user_id):
        """ JWT 기반 호텔 관리자 권한 부여 API """
        user = get_object_or_404(User, id=user_id)
        user_profile = get_object_or_404(UserProfile, user=user)

        if user_profile.role == "HOTEL_MANAGER":
            return Response({"message": "이미 호텔 관리자입니다."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = HotelManagerAssignSerializer(user_profile, data={"role": "HOTEL_MANAGER"}, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": f"{user.username}님이 호텔 관리자로 설정되었습니다."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
