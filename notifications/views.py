from django.contrib.auth import get_user_model
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from chat.models import ChatRoom
from .models import Notification, NotificationType, NotificationReadStatus
from bookings.models import CheckIn
from .serializers import NotificationSerializer
from django.utils import timezone
from rest_framework.generics import get_object_or_404

User = get_user_model()


class EmptySerializer(serializers.Serializer):
    pass

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """현재 로그인한 사용자의 읽지 않은 알림만 조회"""
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()

        # MESSAGE 타입 알림을 sender별로 묶어서 하나만 반환
        message_notifications = Notification.objects.filter(
            read_statuses__recipient=self.request.user,
            read_statuses__read_at__isnull=True,
            notification_type=NotificationType.MESSAGE.name
        ).order_by('sender', '-created_at').distinct('sender')

        other_notifications = Notification.objects.filter(
            read_statuses__recipient=self.request.user,
            read_statuses__read_at__isnull=True
        ).exclude(notification_type=NotificationType.MESSAGE.name).order_by('-created_at')

        return list(message_notifications) + list(other_notifications)


    @action(detail=True, methods=['post'], url_path='mark-notifications-read')
    def mark_notifications_read(self, request, pk=None):
        """특정 발신자의 모든 메시지 알림을 읽음 처리"""
        notification = get_object_or_404(Notification, pk=pk)

        if notification.notification_type == NotificationType.MESSAGE.name:
            # 메시지 알림일 경우 발신자의 모든 메시지 알림을 읽음 처리
            NotificationReadStatus.objects.filter(
                notification__sender=notification.sender,
                notification__chat_room=notification.chat_room,
                notification__notification_type=NotificationType.MESSAGE.name,
                recipient=request.user,
                read_at__isnull=True
            ).update(read_at=timezone.now())
        else:
            # 메시지가 아닌 경우 해당 알림만 읽음 처리
            NotificationReadStatus.objects.filter(
                notification=notification,
                recipient=request.user,
                read_at__isnull=True
            ).update(read_at=timezone.now())

        return Response({"status": "Notification marked as read"}, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        """알림을 생성하고 WebSocket으로 전송"""
        chat_room_id = self.request.data.get('chat_room_id')
        chat_room = ChatRoom.objects.get(id=chat_room_id) if chat_room_id else None
        notification = serializer.save(sender=self.request.user, chat_room=chat_room)  # 공지 내용은 한 번만 저장됨

        if notification.notification_type == NotificationType.EVENT.name:
            recipients = User.objects.filter(userprofile__role='general')

        elif notification.notification_type == NotificationType.ANNOUNCEMENT.name:
            basespace_id = self.request.data.get('basespace_id')
            if basespace_id:
                # basespace_id로 호텔룸에 연결된 basespace를 필터링하고 아직 체크아웃하지 않은 CheckIn 조회
                checkins = CheckIn.objects.filter(
                    hotel_room__floor__basespace=basespace_id,
                    checked_out=False
                )
                recipients = User.objects.filter(id__in=[checkin.user.id for checkin in checkins])
            else:
                recipients = []

        elif notification.notification_type == NotificationType.MESSAGE.name:
            recipients = [self.request.user]  # 1:1 채팅이면 특정 유저에게만 전송

        else:
            return

        read_status_entries = [
            NotificationReadStatus(notification=notification, recipient=user)
            for user in recipients
        ]
        NotificationReadStatus.objects.bulk_create(read_status_entries)  # 🚀 대량 저장

        # ✅ WebSocket으로 즉시 알림 전송
        async_to_sync(send_notification_to_users)([r.id for r in recipients], {
            "id": notification.id,
            "title": notification.title,
            "content": notification.content,
            "notification_type": notification.notification_type,
            "created_at": notification.created_at.isoformat(),
            "chat_room": chat_room_id
        })

async def send_notification_to_users(user_ids, message):
    channel_layer = get_channel_layer()
    for user_id in user_ids:
        await channel_layer.group_send(
            f"notifications_{user_id}",
            {
                "type": "send_notification",
                "message": {
                    "id": message.get("id"),
                    "title": message.get("title"),
                    "content": message.get("content"),
                    "notification_type": message.get("notification_type"),
                    "created_at": message.get("created_at")
                }
            }
        )