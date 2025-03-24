from django.urls import path, include
from .views import CheckInAndOutViewSet, ReviewViewSet, RoomUsageViewSet, HotelRoomStatusViewSet, ReservationViewSet, \
    ReservationListView, CheckInReservationView
from rest_framework import routers
router = routers.DefaultRouter()
router.register(r'reviews', ReviewViewSet)
router.register(r'room-usages', RoomUsageViewSet, basename='room-usage')
router.register(r'hotel-rooms-status', HotelRoomStatusViewSet, basename='hotel-room-status')
router.register(r'reservations', ReservationViewSet, basename='reservation')
urlpatterns = [
    path("checkin/", CheckInAndOutViewSet.as_view({"post": "check_in", "patch": "update_check_in"}), name="checkin"),
    path("checkout/", CheckInAndOutViewSet.as_view({"post": "check_out"}), name="checkout"),
    path("guest_info/", CheckInAndOutViewSet.as_view({"patch": "update_customer_info"}), name="guest_info"),
    path('reservations/', ReservationListView.as_view(), name='reservation-list'),
    path("checkin/<int:checkin_id>/reservation/", CheckInReservationView.as_view(), name="checkin-reservation"),
    path('', include(router.urls)),
]