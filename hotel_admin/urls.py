from django.contrib import admin
from django.urls import path, include, re_path
from django.conf.urls.static import static
from django.conf import settings
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

schema_view = get_schema_view(
    openapi.Info(
        title="hotel_admin API 문서",
        default_version='1.0.0',
        description="JWT 인증을 사용하는 API 문서",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email=""),
        license=openapi.License(name=""),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    authentication_classes=[],
)
urlpatterns = [
    re_path(r'swagger(?P<format>\.json|\.yaml)', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path(r'swagger', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path(r'redoc', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc-v1'),
    path('admin/', admin.site.urls),
    path('chat/', include('chat.urls')),  # chat 앱의 urls 포함
    path('bookings/', include('bookings.urls')),  # bookings 앱의 urls 포함
    path('accounts/',include('accounts.urls')),  # accounts 앱의 urls 포함
    path('spaces/', include('spaces.urls')),  # spaces 앱의 urls 포함
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
