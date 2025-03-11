from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatRoomViewSet, MessageViewSet, UnreadChatRoomsCountView

router = DefaultRouter()
router.register(r'chatrooms', ChatRoomViewSet, basename='chatroom')
router.register(r'messages', MessageViewSet, basename='message')

urlpatterns = [
    path('', include(router.urls)),
    path('chatroom/<int:pk>/mark_as_answered/', ChatRoomViewSet.as_view({'post': 'mark_as_answered'}), name='mark-as-answered'),
    path('unread_chat_rooms_count/', UnreadChatRoomsCountView.as_view(), name='unread-chat-rooms-count'),
]
