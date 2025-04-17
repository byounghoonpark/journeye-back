import random
import string
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from django.core.mail import send_mail
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView, get_object_or_404
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from accounts.models import UserProfile
from bookings.models import CheckIn
from chat.models import ChatRoom
from spaces.models import BaseSpace
from hotel_admin import settings

from .serializers import (
    UserRegistrationSerializer,
    SpaceManagerAssignSerializer,
    UserDetailSerializer,
    EmailTokenObtainPairSerializer,
    UserProfileUpdateSerializer
)

# ========= Utility Functions =========
def generate_verification_code(length=6):
    """Generate a numeric verification code."""
    return ''.join(random.choices(string.digits, k=length))

def get_tokens_for_user(user):
    """Generate JWT tokens for a given user."""
    refresh = RefreshToken.for_user(user)
    return {
        "access_token": str(refresh.access_token),
        "refresh_token": str(refresh)
    }

def send_email(subject, message, recipient_list):
    """Wrapper for sending email using the default settings."""
    from_email = settings.DEFAULT_FROM_EMAIL
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)

# ========= API Views =========

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
        manual_parameters=[
            openapi.Parameter(
                'profile_picture', openapi.IN_FORM, type=openapi.TYPE_FILE, description='사진 업로드'
            )
        ]
    )
    def post(self, request):
        with transaction.atomic():
            serializer = UserRegistrationSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                tokens = get_tokens_for_user(user)

                # 추가 profile 관련 초기화를 진행할 수 있음
                profile = user.profile
                profile.save()

                return Response({
                    "username": user.username,
                    "email": user.email,
                    **tokens,
                    "message": "Registration completed successfully"
                }, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SendEmailVerificationView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="이메일 인증 코드 발송 API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, description="이메일 주소")
            },
            required=["email"]
        ),
        responses={
            200: openapi.Response(description="이메일 인증 코드가 발송되었습니다."),
            400: openapi.Response(description="잘못된 요청"),
        }
    )
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"message": "이메일 주소를 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({"message": "이미 가입된 이메일입니다."}, status=status.HTTP_400_BAD_REQUEST)

        verification_code = generate_verification_code()
        subject = '이메일 인증 6자리 코드 발송'
        message = f'아래의 6자리 코드를 입력하여 이메일 인증을 완료해주세요:\n{verification_code}'

        send_email(subject, message, [email])
        # 실제 운영 환경에서는 코드 값을 응답에 포함시키지 않는 것이 좋습니다.
        return Response({
            "message": "이메일 인증 코드가 발송되었습니다.",
            "verification_code": verification_code
        }, status=status.HTTP_200_OK)

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
        code = request.data.get("verification_code")
        if not code:
            return Response({"message": "인증번호를 입력해주세요."},
                            status=status.HTTP_400_BAD_REQUEST)

        profile = request.user.profile
        # 테스트를 위한 우회 코드 "123456" 사용 가능
        if profile.email_verification_code == code or code == "123456":
            profile.email_verified = True
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
    permission_classes = [IsAuthenticated, IsAdminUser]

    @swagger_auto_schema(
        operation_description="유저를 공간 관리자로 변경하는 API (어드민만 가능)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "user_email": openapi.Schema(type=openapi.TYPE_STRING, description="유저 이메일"),
                "basespace_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="공간 ID")
            },
            required=["user_email", "basespace_id"]
        ),
        responses={
            200: openapi.Response(description="공간 관리자로 설정됨"),
            400: openapi.Response(description="잘못된 요청"),
            403: openapi.Response(description="권한 없음 (어드민만 가능)"),
            404: openapi.Response(description="유저 또는 공간을 찾을 수 없음"),
        },
    )
    def post(self, request):
        user_email = request.data.get("user_email")
        basespace_id = request.data.get("basespace_id")

        if not user_email or not basespace_id:
            return Response({"message": "유저 이메일과 공간 ID를 모두 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, email=user_email)
        user_profile = get_object_or_404(UserProfile, user=user)
        basespace = get_object_or_404(BaseSpace, id=basespace_id)

        if user_profile.role == "MANAGER":
            if basespace.managers.filter(id=user.id).exists():
                return Response({"message": f"{user.username}님은 이미 해당 공간({basespace.name})의 관리자입니다."},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            serializer = SpaceManagerAssignSerializer(user_profile, data={"role": "MANAGER"}, partial=True)
            if serializer.is_valid():
                serializer.save()

        basespace.managers.add(user)
        return Response({
            "message": f"{user.username}님이 '{basespace.name}' 공간의 관리자로 설정되었습니다."
        }, status=status.HTTP_200_OK)

class EmailLoginView(TokenObtainPairView):
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
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            user = User.objects.get(email=request.data["email"])
            managed_basespaces = BaseSpace.objects.filter(managers=user).values("id", "name")
            basespaces_list = list(managed_basespaces)
            if basespaces_list:
                response.data["managed_basespaces"] = basespaces_list
        return response

class EmailCodeLoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="이메일 코드로 로그인하여 JWT 토큰 발급 API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email_code": openapi.Schema(type=openapi.TYPE_STRING, description="이메일 인증 코드")
            },
            required=["email_code"]
        ),
        responses={
            200: openapi.Response(
                description="로그인 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "access_token": openapi.Schema(type=openapi.TYPE_STRING, description="액세스 토큰"),
                        "refresh_token": openapi.Schema(type=openapi.TYPE_STRING, description="리프레시 토큰"),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, description="응답 메시지"),
                    },
                ),
            ),
            400: openapi.Response(description="잘못된 요청"),
            404: openapi.Response(description="사용자를 찾을 수 없음"),
        }
    )
    def post(self, request):
        email_code = request.data.get("email_code")
        if not email_code:
            return Response({"message": "이메일 인증 코드를 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            # 모델 필드는 email_verification_code라고 가정합니다.
            profile = UserProfile.objects.get(email_code=email_code)
            user = profile.user
        except UserProfile.DoesNotExist:
            return Response({"message": "유효하지 않은 이메일 인증 코드입니다."}, status=status.HTTP_404_NOT_FOUND)

        tokens = get_tokens_for_user(user)
        check_in = CheckIn.objects.filter(temp_code=email_code, checked_out=False).first()

        chat_room_id = None
        basespace_id = None
        if check_in:
            basespace_id = check_in.hotel_room.room_type.basespace.id
            chat_room = ChatRoom.objects.filter(checkin=check_in).order_by('-created_at').first()
            if chat_room:
                chat_room_id = chat_room.id

        return Response({
            **tokens,
            "user_name": user.username,
            "chat_room_id": chat_room_id,
            "basespace_id": basespace_id,
            "checkin_id": check_in.id if check_in else None,
            "message": "로그인 성공"
        }, status=status.HTTP_200_OK)

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="비밀번호 변경 API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "current_password": openapi.Schema(type=openapi.TYPE_STRING, format="password", description="현재 비밀번호"),
                "new_password": openapi.Schema(type=openapi.TYPE_STRING, format="password", description="새로운 비밀번호"),
                "confirm_password": openapi.Schema(type=openapi.TYPE_STRING, format="password", description="새로운 비밀번호 확인"),
            },
            required=["current_password", "new_password", "confirm_password"]
        ),
        responses={
            200: openapi.Response(description="비밀번호 변경 성공"),
            400: openapi.Response(description="잘못된 요청"),
            403: openapi.Response(description="현재 비밀번호가 일치하지 않음"),
        }
    )
    def post(self, request):
        user = request.user
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        if not check_password(current_password, user.password):
            return Response({"message": "현재 비밀번호가 올바르지 않습니다."}, status=status.HTTP_403_FORBIDDEN)

        if new_password != confirm_password:
            return Response({"message": "새 비밀번호가 일치하지 않습니다."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        RefreshToken.for_user(user)

        return Response({"message": "비밀번호가 성공적으로 변경되었습니다."}, status=status.HTTP_200_OK)

class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="이메일을 입력하면 비밀번호를 난수로 초기화하고 메일로 전송하는 API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, description="비밀번호 초기화를 요청할 이메일")
            },
            required=["email"]
        ),
        responses={
            200: openapi.Response(description="임시 비밀번호가 이메일로 전송되었습니다."),
            400: openapi.Response(description="잘못된 요청"),
            404: openapi.Response(description="등록되지 않은 이메일")
        }
    )
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"message": "이메일을 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"message": "등록되지 않은 이메일입니다."}, status=status.HTTP_404_NOT_FOUND)

        temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        user.set_password(temp_password)
        user.save()

        subject = "비밀번호 초기화 안내"
        message = f"안녕하세요,\n\n새로운 임시 비밀번호는 다음과 같습니다:\n\n{temp_password}\n\n로그인 후 반드시 비밀번호를 변경해주세요."
        send_email(subject, message, [email])

        return Response({"message": "임시 비밀번호가 이메일로 전송되었습니다."}, status=status.HTTP_200_OK)

class UserProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="회원 프로필 수정 API: 프로필 사진, 전화번호, 국적 수정",
        request_body=UserProfileUpdateSerializer,
        responses={
            200: openapi.Response(
                description="회원 프로필 수정 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "username": openapi.Schema(type=openapi.TYPE_STRING, description="사용자 이름"),
                        "email": openapi.Schema(type=openapi.TYPE_STRING, description="이메일"),
                        "phone_number": openapi.Schema(type=openapi.TYPE_STRING, description="전화번호"),
                        "nationality": openapi.Schema(type=openapi.TYPE_STRING, description="국적"),
                        "language": openapi.Schema(type=openapi.TYPE_STRING, description="언어"),
                        "profile_picture": openapi.Schema(type=openapi.TYPE_STRING, description="프로필 사진 URL"),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, description="응답 메시지"),
                    },
                ),
            ),
            400: openapi.Response(description="잘못된 요청"),
        },
        manual_parameters=[
            openapi.Parameter(
                'profile_picture',
                openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                description='프로필 사진 파일'
            ),
            openapi.Parameter(
                'phone_number',
                openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                description='전화번호'
            ),
            openapi.Parameter(
                'nationality',
                openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                description='국적'
            ),
            openapi.Parameter(
                'language',
                openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                description='언어'
            ),
        ]
    )
    def patch(self, request):
        user = request.user
        profile = user.profile

        serializer = UserProfileUpdateSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "username": user.username,
                "email": user.email,
                "phone_number": serializer.data.get("phone_number", profile.phone_number),
                "nationality": serializer.data.get("nationality", profile.nationality),
                "language": serializer.data.get("language", profile.language),
                "profile_picture": serializer.data.get("profile_picture", profile.profile_picture.url if profile.profile_picture else None),
                "message": "Profile updated successfully"
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="JWT 토큰과 비밀번호를 이용한 비밀번호 검증 API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'password': openapi.Schema(type=openapi.TYPE_STRING, format="password", description="비밀번호"),
            },
            required=['password']
        ),
        responses={
            200: openapi.Response(description="비밀번호가 올바릅니다."),
            400: openapi.Response(description="잘못된 요청"),
            403: openapi.Response(description="비밀번호가 올바르지 않습니다."),
        }
    )
    def post(self, request):
        user = request.user
        password = request.data.get("password")
        if not password:
            return Response({"message": "비밀번호를 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        if check_password(password, user.password):
            return Response({"message": "비밀번호가 올바릅니다."}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "비밀번호가 올바르지 않습니다."}, status=status.HTTP_403_FORBIDDEN)

class CheckEmailView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="이메일 중복 및 가입 여부 확인 API",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, description="확인할 이메일 주소")
            },
            required=["email"]
        ),
        responses={
            200: openapi.Response(description="이메일 확인 결과"),
            400: openapi.Response(description="잘못된 요청")
        }
    )
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"message": "이메일 주소를 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email=email).exists():
            return Response({"message": "이미 가입된 이메일입니다."}, status=status.HTTP_200_OK)
        return Response({"message": "가입되지 않은 이메일입니다."}, status=status.HTTP_200_OK)
