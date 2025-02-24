from django.urls import path
from .views import HotelCreateView

urlpatterns = [
    path("hotels/create/", HotelCreateView.as_view(), name="hotel-create"),
]
