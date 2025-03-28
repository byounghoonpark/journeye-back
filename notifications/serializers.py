from django.contrib.auth import get_user_model
from rest_framework import serializers

from spaces.models import BaseSpacePhoto
from .models import Notification, NotificationType, NotificationReadStatus
from django.utils.timezone import localtime, now
from django.utils.translation import gettext_lazy as _
from datetime import timedelta

User = get_user_model()

class NotificationUserSerializer(serializers.ModelSerializer):
    """알림 수신자 정보 시리얼라이저"""
    class Meta:
        model = User
        fields = ['id', 'username']

class NotificationSerializer(serializers.ModelSerializer):
    sender = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    hotel_photo = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'sender', 'title', 'content', 'notification_type', 'created_at', 'hotel_photo', 'is_read', 'unread_count', 'chat_room']

    def get_sender(self, obj):
        managed_spaces = obj.sender.managed_spaces.all()
        if managed_spaces.exists():
            return managed_spaces.first().name  # 첫 번째 관리하는 공간의 이름 반환
        return None

    def get_created_at(self, obj):
        created_at = localtime(obj.created_at)
        today = localtime(now()).date()

        if created_at.date() == today:
            return created_at.strftime("%I:%M %p")
        elif created_at.date() == today - timedelta(days=1):
            return _("Yesterday")
        else:
            return created_at.strftime("%m/%d/%Y")

    def get_hotel_photo(self, obj):
        managed_spaces = obj.sender.managed_spaces.all()
        if managed_spaces.exists():
            hotel = managed_spaces.first()
            photo = BaseSpacePhoto.objects.filter(basespace=hotel).first()
            if photo:
                return photo.image.url
        return None

    def get_is_read(self, obj):
        read_status = obj.read_statuses.filter(recipient=self.context['request'].user).first()
        return 0 if read_status and read_status.read_at else 1

    def get_unread_count(self, obj):
        if obj.notification_type == NotificationType.MESSAGE.name:
            return NotificationReadStatus.objects.filter(
                notification__notification_type=NotificationType.MESSAGE.name,
                notification__sender=obj.sender,
                recipient=self.context['request'].user,
                read_at__isnull=True
            ).count()
        return 0