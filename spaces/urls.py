from django.urls import path,include
from .views import HotelCreateView, HotelRoomTypeViewSet
from rest_framework import routers
from .views import HotelRoomViewSet

router = routers.DefaultRouter()
router.register(r'hotelrooms', HotelRoomViewSet)
router.register(r'roomtypes', HotelRoomTypeViewSet)

urlpatterns = [
    path("hotels/create/", HotelCreateView.as_view(), name="hotel-create"),
    path('', include(router.urls)),

]
