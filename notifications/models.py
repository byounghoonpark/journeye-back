from enum import Enum
from django.db import models
from django.conf import settings
from django.utils import timezone

class ChoiceEnum(Enum):
    @classmethod
    def choices(cls):
        return [(choice.name, choice.value) for choice in cls]

class NotificationType(ChoiceEnum):
    EVENT = "EVENT"
    ANNOUNCEMENT = "ANNOUNCEMENT"
    MESSAGE = "MESSAGE"

class Notification(models.Model):
    """공지 및 메시지 알람 모델 (공지 내용 저장)"""
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_notifications"
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices(),
        default=NotificationType.MESSAGE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.notification_type}] {self.title}"

class NotificationReadStatus(models.Model):
    """각 유저가 해당 알림을 읽었는지 추적"""
    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="read_statuses"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_notifications"
    )
    read_at = models.DateTimeField(null=True, blank=True)

    def mark_as_read(self):
        """알림을 읽음 처리하는 메서드"""
        self.read_at = timezone.now()
        self.save()
