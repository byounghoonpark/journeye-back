# notifications/consumers.py
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            # 익명 사용자는 연결 차단
            await self.close()
        else:
            # 사용자별 그룹에 가입: 그룹명 = "notifications_{user_id}"
            self.group_name = f"notifications_{self.user.id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            logger.info(f"✅ WebSocket 연결됨: {self.user.id} (그룹: {self.group_name})")

    async def disconnect(self, close_code):
        # 그룹에서 탈퇴
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.info(f"🔌 WebSocket 연결 종료됨: {self.user.id}")

    async def send_notification(self, event):
        # WebSocket을 통해 알림 전송 (JSON 형태)
        message = event["message"]
        await self.send(text_data=json.dumps(message, ensure_ascii=False))
        logger.info(f"📩 WebSocket 알림 전송됨: {message}")
