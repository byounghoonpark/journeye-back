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
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices(),
        default=NotificationType.MESSAGE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    def mark_as_read(self):
        """알림을 읽음 처리하는 헬퍼 메서드"""
        self.read_at = timezone.now()
        self.save()

    def __str__(self):
        return f"[{self.get_notification_type_display()}] {self.title}"
