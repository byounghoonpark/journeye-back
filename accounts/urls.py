from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,  # 액세스 토큰 갱신
    TokenVerifyView,  # JWT 토큰 유효성 검사
)
from .views import (
    UserRegistrationView,
    AssignSpaceManagerView,
    EmailVerificationView,
    SendEmailVerificationView,
    LoggedInUserDetailView,
    EmailTokenObtainPairView,
    EmailCodeLoginView
)

urlpatterns = [
    path("register/", UserRegistrationView.as_view(), name="user-register"),
    path("send-email/", SendEmailVerificationView.as_view(), name="resend-email-verification"),
    path("email-verify/", EmailVerificationView.as_view(), name="email-verify"),
    path("assign-space-manager/<int:user_id>/", AssignSpaceManagerView.as_view(), name="assign-hotel-manager"),
    path("login/", EmailTokenObtainPairView.as_view(), name="로그인"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),  # 액세스 토큰 갱신
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),  # 토큰 검증
    path('user/me/', LoggedInUserDetailView.as_view(), name='내 정보 조회'),
    path('login/email-code/', EmailCodeLoginView.as_view(), name='email_code_login'),
]
