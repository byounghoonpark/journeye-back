from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message

User = get_user_model()

class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        try:
            # URL 경로에서 room_id를 추출합니다.
            self.room_id = self.scope['url_route']['kwargs'].get('room_id')
            if not self.room_id or not await self.check_room_exists(self.room_id):
                raise ValueError('채팅방이 존재하지 않습니다.')
            group_name = self.get_group_name(self.room_id)
            await self.channel_layer.group_add(group_name, self.channel_name)
            await self.accept()
        except ValueError as e:
            await self.send_json({'error': str(e)})
            await self.close()

    async def disconnect(self, close_code):
        try:
            group_name = self.get_group_name(self.room_id)
            await self.channel_layer.group_discard(group_name, self.channel_name)
        except Exception:
            pass

    async def receive_json(self, content):
        try:
            # 클라이언트로부터 메시지와 발신자 이메일, 호텔 관리자 및 일반 사용자 이메일을 추출합니다.
            message = content['message']
            sender_email = content['sender_email']
            hotel_admin_email = content.get('hotel_admin_email')
            user_email = content.get('user_email')

            if not hotel_admin_email or not user_email:
                raise ValueError("호텔 관리자와 일반 사용자 이메일이 모두 필요합니다.")

            # 호텔 관리자와 일반 사용자 이메일을 기준으로 채팅방을 가져오거나 생성합니다.
            room = await self.get_or_create_room(hotel_admin_email, user_email)
            self.room_id = str(room.id)
            group_name = self.get_group_name(self.room_id)

            # 메시지를 데이터베이스에 저장합니다.
            await self.save_message(room, sender_email, message)

            # 그룹 내 모든 클라이언트에 메시지를 전송합니다.
            await self.channel_layer.group_send(group_name, {
                'type': 'chat_message',
                'message': message,
                'sender_email': sender_email
            })
        except ValueError as e:
            await self.send_json({'error': str(e)})

    async def chat_message(self, event):
        try:
            message = event['message']
            sender_email = event['sender_email']
            await self.send_json({'message': message, 'sender_email': sender_email})
        except Exception:
            await self.send_json({'error': '메시지 전송 실패'})

    @staticmethod
    def get_group_name(room_id):
        return f"chat_room_{room_id}"

    @database_sync_to_async
    def get_or_create_room(self, hotel_admin_email, user_email):
        # 호텔 관리자와 일반 사용자 CustomUser를 조회합니다.
        try:
            hotel_admin = User.objects.get(email=hotel_admin_email, type='hotel_admin')
        except User.DoesNotExist:
            raise ValueError("호텔 관리자 이메일이 올바르지 않거나 존재하지 않습니다.")
        try:
            normal_user = User.objects.get(email=user_email, type='user')
        except User.DoesNotExist:
            raise ValueError("일반 사용자 이메일이 올바르지 않거나 존재하지 않습니다.")

        room, created = ChatRoom.objects.get_or_create(
            hotel_admin=hotel_admin,
            user=normal_user
        )
        return room

    @database_sync_to_async
    def save_message(self, room, sender_email, message_text):
        if not sender_email or not message_text:
            raise ValueError("발신자 이메일 및 메시지 텍스트가 필요합니다.")
        try:
            sender = User.objects.get(email=sender_email)
        except User.DoesNotExist:
            raise ValueError("발신자 이메일에 해당하는 사용자가 존재하지 않습니다.")
        Message.objects.create(chat_room=room, sender=sender, text=message_text)

    @database_sync_to_async
    def check_room_exists(self, room_id):
        return ChatRoom.objects.filter(id=room_id).exists()
