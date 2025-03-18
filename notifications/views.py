from django.contrib.auth import get_user_model
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Notification, NotificationType, NotificationReadStatus
from bookings.models import CheckIn
from .serializers import NotificationSerializer

User = get_user_model()

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """현재 로그인한 사용자의 알림만 조회"""
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()
        return Notification.objects.filter(read_statuses__recipient=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        """알림을 생성하고 WebSocket으로 전송"""
        notification = serializer.save(sender=self.request.user)  # 공지 내용은 한 번만 저장됨

        if notification.notification_type == NotificationType.EVENT.name:
            User.objects.filter(userprofile__role='general')


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