from django.urls import path,include
from .views import HotelRoomTypeViewSet, HotelViewSet, HotelRoomViewSet, FloorViewSet
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'hotelrooms', HotelRoomViewSet)
router.register(r'roomtypes', HotelRoomTypeViewSet)
router.register(r'hotels', HotelViewSet)
router.register(r'floors', FloorViewSet)

urlpatterns = [
    path('', include(router.urls)),

]
