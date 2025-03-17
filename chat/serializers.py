import pytz
from rest_framework import serializers
from .models import ChatRoom, Message, ChatRoomParticipant
from django.utils import timezone

from .utils import translate_text


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
    translated_content = serializers.CharField(read_only=True)

    class Meta:
        model = Message
        fields = [
            'id', 'room', 'sender', 'content', 'translated_content', 'file',
            'file_url', 'file_name', 'file_type', 'created_at'
        ]

    def create(self, validated_data):
        validated_data.pop('file', None)
        message = super().create(validated_data)
        if message.content:
            target_lang = 'KO' if message.sender.profile.language != 'KO' else message.sender.profile.language
            message.translated_content = translate_text(message.content, target_lang)
            message.save()
        return message

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
    unread_count = serializers.SerializerMethodField()
    is_answered = serializers.BooleanField()

    class Meta:
        model = ChatRoom
        fields = ['id', 'room_number', 'room_type', 'guest_name', 'guest_nationality',
                  'last_message', 'last_message_time', 'unread_count', 'is_answered']

    def get_last_message(self, obj):
        last_message = Message.objects.filter(room=obj).order_by('-created_at').first()
        return last_message.content if last_message else None

    def get_last_message_time(self, obj):
        last_message = Message.objects.filter(room=obj).order_by('-created_at').first()
        if last_message:
            now_time = timezone.localtime(timezone.now())
            last_time = timezone.localtime(last_message.created_at)
            if last_time.date() == now_time.date():
                return last_time.strftime('%I:%M %p')
            else:
                return last_time.strftime('%d/%m/%Y')
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request:
            return 0
        user = request.user
        try:
            participant = obj.participants.get(user=user)
        except ChatRoomParticipant.DoesNotExist:
            # 참여 기록이 없으면 읽지 않은 메시지가 없다고 간주
            return Message.objects.filter(room=obj).count()

        # 만약 last_read_time이 기록되어 있다면, 그 시간 이후의 메시지 개수를 반환
        if participant.last_read_time:
            count = Message.objects.filter(room=obj, created_at__gt=participant.last_read_time).count()
        else:
            # 기록이 없으면 모든 메시지를 미확인으로 간주
            count = Message.objects.filter(room=obj).count()
        return count


class ManagerChatRoomSerializer(serializers.ModelSerializer):
    room_number = serializers.CharField(source='checkin.hotel_room.room_number')
    room_type = serializers.CharField(source='checkin.hotel_room.room_type.name')
    guest_nationality = serializers.CharField(source='checkin.user.profile.nationality')
    guest_profile_image = serializers.ImageField(source='checkin.user.profile.profile_picture', required=False)
    hotel_profile_image = serializers.ImageField(source='checkin.hotel_room.room_type.basespace.photos.first.image', required=False)
    messages = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ['id', 'room_number', 'room_type', 'guest_nationality', 'guest_profile_image', 'hotel_profile_image', 'messages']

    def get_messages(self, obj):
        messages = Message.objects.filter(room=obj).order_by('created_at')
        grouped_messages = {}
        for message in messages:
            date = message.created_at.date()
            if date not in grouped_messages:
                grouped_messages[date] = []
            grouped_messages[date].append(self.format_message(message))
        return [{'date': date, 'messages': msgs} for date, msgs in grouped_messages.items()]

    def format_message(self, message):
        korea_tz = pytz.timezone('Asia/Seoul')
        local_time = message.created_at.astimezone(korea_tz)
        formatted_time = local_time.strftime('%I:%M %p')
        message_data = MessageSerializer(message).data
        message_data['created_at'] = formatted_time
        return message_data


class CustomerChatRoomSerializer(serializers.ModelSerializer):
    hotel_profile_image = serializers.ImageField(source='checkin.hotel_room.room_type.basespace.photos.first.image', required=False)
    messages = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ['id', 'hotel_profile_image', 'messages']

    def get_messages(self, obj):
        messages = Message.objects.filter(room=obj).order_by('created_at')
        grouped_messages = {}
        for message in messages:
            date = message.created_at.date()
            if date not in grouped_messages:
                grouped_messages[date] = []
            grouped_messages[date].append(self.format_message(message, obj))
        return [{'date': date, 'messages': msgs} for date, msgs in grouped_messages.items()]

    def format_message(self, message, chat_room):
        request = self.context.get('request')
        korea_tz = pytz.timezone('Asia/Seoul')
        local_time = message.created_at.astimezone(korea_tz)
        formatted_time = local_time.strftime('%I:%M %p')
        message_data = MessageSerializer(message).data
        message_data['created_at'] = formatted_time
        if request:
            if message.sender == request.user:
                message_data['sender'] = message.sender.username
            else:
                message_data['sender'] = chat_room.checkin.hotel_room.room_type.basespace.name
                message_data['content'] = message_data.get('translated_content')
        return message_data