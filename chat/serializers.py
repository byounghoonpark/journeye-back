from rest_framework import serializers
from .models import ChatRoom, Message

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = "__all__"

class ChatRoomSerializer(serializers.ModelSerializer):
    latest_message = serializers.SerializerMethodField()
    opponent_email = serializers.SerializerMethodField()
    hotel_admin_email = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatRoom
        fields = ('id', 'hotel_admin_email', 'user_email', 'latest_message', 'opponent_email', 'messages')

    def get_latest_message(self, obj):
        latest_msg = Message.objects.filter(chat_room=obj).order_by('-timestamp').first()
        return latest_msg.text if latest_msg else None

    def get_opponent_email(self, obj):
        request_user_email = self.context['request'].query_params.get('email', None)
        # 요청한 사용자가 호텔 관리자라면 상대는 일반 사용자, 그렇지 않으면 호텔 관리자입니다.
        if request_user_email == obj.hotel_admin.email:
            return obj.user.email
        return obj.hotel_admin.email

    def get_hotel_admin_email(self, obj):
        return obj.hotel_admin.email

    def get_user_email(self, obj):
        return obj.user.email
