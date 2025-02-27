from django.urls import path, include
from .views import CheckInViewSet
from rest_framework import routers
router = routers.DefaultRouter()
router.register(r'checkin', CheckInViewSet, basename='checkin')
urlpatterns = [
    path('', include(router.urls)),
]