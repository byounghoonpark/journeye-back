from django.contrib import admin
from .models import (
    CheckIn,
    Reservation,
    Review,
    ReviewPhoto,
    Like
)

admin.site.register(CheckIn)
admin.site.register(Reservation)
admin.site.register(Review)
admin.site.register(ReviewPhoto)
admin.site.register(Like)