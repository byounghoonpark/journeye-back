from django.urls import path
from .views import CheckInAndOutViewSet
from rest_framework import routers
router = routers.DefaultRouter()

urlpatterns = [
    path("checkin/", CheckInAndOutViewSet.as_view({"post": "check_in"}), name="checkin"),
    path("checkout/", CheckInAndOutViewSet.as_view({"post": "check_out"}), name="checkout"),
]