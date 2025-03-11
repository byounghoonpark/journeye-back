from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatRoomViewSet, MessageViewSet

router = DefaultRouter()
router.register(r'chatrooms', ChatRoomViewSet, basename='chatroom')
router.register(r'messages', MessageViewSet, basename='message')

urlpatterns = [
    path('', include(router.urls)),
    path('chatroom/<int:pk>/mark_as_answered/', ChatRoomViewSet.as_view({'post': 'mark_as_answered'}), name='mark-as-answered'),
]
