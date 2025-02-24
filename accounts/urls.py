from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,  # 로그인 (JWT 발급)
    TokenRefreshView,  # 액세스 토큰 갱신
    TokenVerifyView,  # JWT 토큰 유효성 검사
)
from .views import UserRegistrationView, AssignHotelManagerView

urlpatterns = [
    path("register/", UserRegistrationView.as_view(), name="user-register"),
    path("assign-hotel-manager/<int:user_id>/", AssignHotelManagerView.as_view(), name="assign-hotel-manager"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),  # JWT 로그인
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),  # 액세스 토큰 갱신
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),  # 토큰 검증
]
