from django.db import models
from django.contrib.auth.models import User

# 호텔 관리자와 일반 사용자 간의 1:1 채팅만 지원 (예: 호텔 관련 문의 등)
class ChatRoom(models.Model):
    hotel_admin = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="admin_chatrooms",
        limit_choices_to={"type": "hotel_admin"},
        verbose_name="호텔 관리자",
        null=True
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_chatrooms",
        limit_choices_to={"type": "user"},
        verbose_name="사용자"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("hotel_admin", "user"),)

    def __str__(self):
        return f"ChatRoom between {self.hotel_admin.username} and {self.user.username}"

# Message: 해당 채팅방 내의 메시지
class Message(models.Model):
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="보낸 사람")
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender.username} at {self.timestamp}"