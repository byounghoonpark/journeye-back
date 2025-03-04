from django.urls import path, include
from .views import CheckInAndOutViewSet, ReviewViewSet, RoomUsageViewSet, HotelRoomStatusViewSet
from rest_framework import routers
router = routers.DefaultRouter()
router.register(r'reviews', ReviewViewSet)
router.register(r'room-usages', RoomUsageViewSet, basename='room-usage')
router.register(r'hotel-rooms-status', HotelRoomStatusViewSet, basename='hotel-room-status')
urlpatterns = [
    path("checkin/", CheckInAndOutViewSet.as_view({"post": "check_in"}), name="checkin"),
    path("checkout/", CheckInAndOutViewSet.as_view({"post": "check_out"}), name="checkout"),
    path('', include(router.urls)),
]