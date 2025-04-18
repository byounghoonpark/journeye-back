from django.urls import path,include
from .views import (
    HotelRoomTypeViewSet,
    HotelViewSet,
    HotelRoomViewSet,
    FloorViewSet,
    HotelRoomMemoViewSet,
    HotelRoomHistoryViewSet,
    FacilityViewSet, FeaturedBaseSpaceListView,
)
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'hotel-rooms', HotelRoomViewSet)
router.register(r'room-types', HotelRoomTypeViewSet)
router.register(r'hotels', HotelViewSet)
router.register(r'floors', FloorViewSet)
router.register(r'hotel-room-memo', HotelRoomMemoViewSet)
router.register(r'hotel-room-history', HotelRoomHistoryViewSet)
router.register(r'facilities', FacilityViewSet)
urlpatterns = [
    path('', include(router.urls)),
    path('featured-spaces/', FeaturedBaseSpaceListView.as_view(), name='featured-spaces'),
]
