from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Notification

User = get_user_model()

class NotificationUserSerializer(serializers.ModelSerializer):
    """알림 수신자 정보 시리얼라이저"""
    class Meta:
        model = User
        fields = ['id', 'username']

class NotificationSerializer(serializers.ModelSerializer):
    sender = NotificationUserSerializer(read_only=True)
    basespace_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Notification
        fields = '__all__'

    def create(self, validated_data):
        # basespace_id는 모델에 포함되지 않으므로 제거합니다.
        validated_data.pop('basespace_id', None)
        return super().create(validated_data)
