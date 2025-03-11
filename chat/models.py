from django.db import models
from django.contrib.auth.models import User
from spaces.models import BaseSpace
from bookings.models import CheckIn

class ChatRoom(models.Model):
    id = models.AutoField(primary_key=True)
    basespace = models.ForeignKey(BaseSpace, on_delete=models.CASCADE, related_name="chat_rooms")
    checkin = models.ForeignKey(CheckIn, on_delete=models.CASCADE, related_name="chat_rooms")
    is_active = models.BooleanField(default=True, verbose_name="채팅방 활성화 여부")  # 체크아웃 시 False
    is_answered = models.BooleanField(default=True, verbose_name="답변 완료 여부")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat Room - {self.checkin.user.username} ({self.basespace.name})"

class ChatRoomParticipant(models.Model):
    chatroom = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chatroom_participations')
    last_read_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.chatroom} - {self.user.username}"

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(blank=True, null=True)
    translated_content = models.TextField(blank=True, null=True)
    file_url = models.URLField(blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    file_type = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.room.basespace.name}] {self.sender.username}: {self.content}"
