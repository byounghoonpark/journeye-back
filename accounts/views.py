from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from accounts.models import UserProfile
from .serializers import UserRegistrationSerializer, SpaceManagerAssignSerializer, UserDetailSerializer, EmailTokenObtainPairSerializer
from rest_framework.generics import get_object_or_404, RetrieveAPIView
from rest_framework.parsers import MultiPartParser, FormParser
import random
from hotel_admin import settings

class UserRegistrationView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

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
                        "first_name": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 이름"),
                        "last_name": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 성"),
                        "email": openapi.Schema(type=openapi.TYPE_STRING, description="이메일"),
                        "access_token": openapi.Schema(type=openapi.TYPE_STRING, description="액세스 토큰"),
                        "refresh_token": openapi.Schema(type=openapi.TYPE_STRING, description="리프레시 토큰"),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, description="응답 메시지"),
                    },
                ),
            ),
            400: openapi.Response(description="잘못된 요청"),
        },
        manual_parameters=[
            openapi.Parameter(
                'profile_picture', openapi.IN_FORM, type=openapi.TYPE_FILE, description='사진 업로드'
            )
        ]
    )
    def post(self, request):
        """JWT 기반 회원가입 및 6자리 이메일 인증번호 전송 API"""
        with transaction.atomic():
            serializer = UserRegistrationSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()

                # JWT 토큰 생성
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                refresh_token = str(refresh)

                # 6자리 인증번호 생성

                verification_code = str(random.randint(100000, 999999))

                # UserProfile에 인증번호 저장 (모델에 email_verification_code 필드 필요)
                profile = user.profile
                profile.email_code = verification_code
                profile.save()

                # 이메일 전송
                subject = '이메일 인증 6자리 코드'
                message = f'아래의 6자리 코드를 입력하여 이메일 인증을 완료해주세요:\n{verification_code}'

                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [user.email]
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)

                return Response({
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "message": "회원가입이 완료되었습니다. 이메일로 전송된 6자리 코드를 확인해주세요."
                }, status=status.HTTP_201_CREATED)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class ResendEmailVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="이메일 인증 코드 재발송 API",
        responses={
            200: openapi.Response(description="이메일 인증 코드가 재발송되었습니다."),
            400: openapi.Response(description="잘못된 요청")
        }
    )
    def post(self, request):
        """로그인한 유저를 기반으로 이메일 인증 코드 재발송 API"""
        user = request.user
        profile = user.profile

        # 6자리 인증번호 생성
        verification_code = str(random.randint(100000, 999999))

        # UserProfile에 인증번호 저장
        profile.email_code = verification_code
        profile.save()

        # 이메일 전송
        subject = '이메일 인증 6자리 코드 재발송'
        message = f'아래의 6자리 코드를 입력하여 이메일 인증을 완료해주세요:\n{verification_code}'

        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user.email]
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)

        return Response({"message": "이메일 인증 코드가 재발송되었습니다."}, status=status.HTTP_200_OK)


class EmailVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="이메일 인증 API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "verification_code": openapi.Schema(type=openapi.TYPE_STRING, description="인증번호")
            }
        ),
        responses={
            200: openapi.Response(description="이메일 인증이 완료되었습니다."),
            400: openapi.Response(description="잘못된 요청")
        }
    )
    def post(self, request):
        """
        요청 예시 (JSON):
        {
            "verification_code": "123456"
        }
        """
        code = request.data.get("verification_code")
        if not code:
            return Response({"message": "인증번호를 입력해주세요."},
                            status=status.HTTP_400_BAD_REQUEST)

        profile = request.user.profile
        if profile.email_code == code:
            profile.email_verified = True
            # 인증 완료 후 인증번호 초기화
            profile.email_verification_code = ""
            profile.save()
            return Response({"message": "이메일 인증이 완료되었습니다."}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "인증번호가 올바르지 않습니다."}, status=status.HTTP_400_BAD_REQUEST)


class LoggedInUserDetailView(RetrieveAPIView):
    serializer_class = UserDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class AssignSpaceManagerView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]  # 어드민만 접근 가능

    @swagger_auto_schema(
        operation_description="유저를 공간 관리자로 변경하는 API (어드민만 가능)",
        responses={
            200: openapi.Response(description="공간 관리자로 설정됨"),
            400: openapi.Response(description="잘못된 요청"),
            403: openapi.Response(description="권한 없음 (어드민만 가능)"),
        },
    )
    def post(self, request, user_id):
        """ JWT 기반 공간 관리자 권한 부여 API """
        user = get_object_or_404(User, id=user_id)
        user_profile = get_object_or_404(UserProfile, user=user)

        if user_profile.role == "SPACE_MANAGER":
            return Response({"message": "이미 공간 관리자입니다."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SpaceManagerAssignSerializer(user_profile, data={"role": "SPACE_MANAGER"}, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": f"{user.username}님이 공간 관리자로 설정되었습니다."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer

    @swagger_auto_schema(
        operation_description="이메일과 비밀번호를 이용한 JWT 토큰 발급 API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description="이메일"),
                'password': openapi.Schema(type=openapi.TYPE_STRING, format="password", description="비밀번호"),
            },
            required=['email', 'password']
        ),
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'access': openapi.Schema(type=openapi.TYPE_STRING, description="액세스 토큰"),
                    'refresh': openapi.Schema(type=openapi.TYPE_STRING, description="리프레시 토큰"),
                }
            ),
            400: "잘못된 요청"
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)