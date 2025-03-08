from django.urls import re_path
from .consumers import MultiplexConsumer

websocket_urlpatterns = [
    re_path(r'ws/multiplex/$', MultiplexConsumer.as_asgi()),
]