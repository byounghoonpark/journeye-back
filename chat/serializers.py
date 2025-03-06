from rest_framework import serializers
from .models import ChatRoom, Message
from datetime import datetime

class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.StringRelatedField(read_only=True)
    room = serializers.PrimaryKeyRelatedField(write_only=True, queryset=ChatRoom.objects.all())
    # 클라이언트 입력용 파일 필드 (write_only)
    file = serializers.FileField(write_only=True, required=False)
    # 저장 후 자동으로 채워지는 필드들은 read_only
    file_url = serializers.CharField(read_only=True)
    file_name = serializers.CharField(read_only=True)
    file_type = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Message
        fields = [
            'id', 'room', 'sender', 'content', 'file',
            'file_url', 'file_name', 'file_type', 'created_at'
        ]

    def create(self, validated_data):
        # file 필드는 Message 모델에 없으므로 삭제합니다.
        validated_data.pop('file', None)
        return super().create(validated_data)

class ChatRoomSerializer(serializers.ModelSerializer):
    # 채팅방에 연결된 메시지 목록
    messages = MessageSerializer(many=True, read_only=True)
    # basespace와 checkin 필드에 대해 간단한 문자열 표현을 사용 (필요시 더 상세한 Serializer로 교체 가능)
    basespace = serializers.StringRelatedField()
    checkin = serializers.StringRelatedField()

    class Meta:
        model = ChatRoom
        fields = ['id', 'basespace', 'checkin', 'is_active', 'created_at', 'messages']

class ChatRoomListSerializer(serializers.ModelSerializer):
    room_number = serializers.CharField(source='checkin.hotel_room.room_number')
    room_type = serializers.CharField(source='checkin.hotel_room.room_type.name')
    guest_name = serializers.CharField(source='checkin.user.username')
    guest_nationality = serializers.CharField(source='checkin.user.profile.nationality')
    last_message = serializers.SerializerMethodField()
    last_message_time = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ['id', 'room_number', 'room_type', 'guest_name', 'guest_nationality', 'last_message', 'last_message_time']

    def get_last_message(self, obj):
        last_message = Message.objects.filter(room=obj).order_by('-created_at').first()
        return last_message.content if last_message else None

    def get_last_message_time(self, obj):
        last_message = Message.objects.filter(room=obj).order_by('-created_at').first()
        if last_message:
            now = datetime.now()
            if last_message.created_at.date() == now.date():
                return last_message.created_at.strftime('%I:%M %p')
            else:
                return last_message.created_at.strftime('%d/%m/%Y')
        return None
