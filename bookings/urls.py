from django.urls import path
from .views import CheckInCreateView

urlpatterns = [
    path('checkin/', CheckInCreateView.as_view(), name='checkin_create'),
]