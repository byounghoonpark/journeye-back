from django.contrib import admin
from .models import (
    BaseSpace,
    Floor,
    BaseSpacePhoto,
    Hotel,
    Service,
    Space,
    SpacePhoto,
    HotelRoomType,
    HotelRoom,
    HotelRoomMemo,
    HotelRoomHistory,
    HotelRoomUsage
)

admin.site.register(BaseSpace)
admin.site.register(Floor)
admin.site.register(BaseSpacePhoto)
admin.site.register(Hotel)
admin.site.register(Service)
admin.site.register(Space)
admin.site.register(SpacePhoto)
admin.site.register(HotelRoomType)
admin.site.register(HotelRoom)
admin.site.register(HotelRoomMemo)
admin.site.register(HotelRoomHistory)
admin.site.register(HotelRoomUsage)
