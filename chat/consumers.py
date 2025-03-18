import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from urllib.parse import parse_qs

from notifications.utils import send_notification_to_users
from spaces.models import BaseSpace
from .models import ChatRoom, Message
from .utils import translate_text
from django.utils.timezone import localtime

class MultiplexConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.groups_to_join = []  # 초기화

    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return

        # 쿼리 문자열에서 room_id와 basespace_id 가져오기
        qs = parse_qs(self.scope.get("query_string", b"").decode())

        # room_id가 있으면 고객용 채팅방 그룹에 가입
        room_ids = qs.get("room_id")
        if room_ids:
            self.room_id = room_ids[0]
            self.chat_group_name = f"chat_{self.room_id}"
            self.groups_to_join.append(self.chat_group_name)
            self.chat_room = await sync_to_async(ChatRoom.objects.get)(id=self.room_id)

        # basespace_id가 있으면 매니저용 그룹에도 가입 (매니저나 관리자 전용)
        basespace_ids = qs.get("basespace_id")
        if basespace_ids:
            self.basespace_id = basespace_ids[0]
            self.manager_group_name = f"manager_{self.basespace_id}"
            self.groups_to_join.append(self.manager_group_name)

            # 매니저용 가입 시 사용자 권한 확인
            user_role = await sync_to_async(lambda: self.user.profile.role)()
            if user_role not in ["ADMIN", "MANAGER"]:
                await self.send(json.dumps({"error": "매니저나 관리자가 아닙니다."}))
                await self.close()
                return
            if user_role == "MANAGER":
                # 해당 basespace가 존재하는지 및 매니저 권한 확인
                try:
                    basespace = await sync_to_async(BaseSpace.objects.get)(id=self.basespace_id)
                except BaseSpace.DoesNotExist:
                    await self.send(json.dumps({"error": "해당 basespace가 존재하지 않습니다."}))
                    await self.close()
                    return
                is_manager = await sync_to_async(lambda: basespace.managers.filter(id=self.user.id).exists())()
                if not is_manager:
                    await self.send(json.dumps({"error": "해당 호텔의 매니저가 아닙니다."}))
                    await self.close()
                    return

        # 모든 지정된 그룹에 가입
        for group in self.groups_to_join:
            await self.channel_layer.group_add(group, self.channel_name)
        await self.accept()
        await self.send(json.dumps({
            "message": "멀티플렉싱 소켓 연결 성공",
            "joined_groups": self.groups_to_join
        }, ensure_ascii=False))

    async def disconnect(self, close_code):
        for group in self.groups_to_join:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def receive(self, text_data):
        """
        클라이언트가 전송하는 메시지 예시:
        {
          "target": "chat",    // 또는 "manager"
          "content": "안녕하세요",
          "file_url": null,     // (옵션)
          "file_name": null,    // (옵션)
          "file_type": null     // (옵션)
        }
        """
        try:
            data = json.loads(text_data)
            target = data.get("target")
            content = data.get("content", "")
            file_url = data.get("file_url")
            file_name = data.get("file_name")
            file_type = data.get("file_type")

            sender_role = await sync_to_async(lambda: self.user.profile.role)()
            # 채팅방에 연결된 고객 (체크인 사용자의 정보)
            customer = await sync_to_async(lambda: self.chat_room.checkin.user)()
            # 고객의 언어 (없으면 기본값 "KO")
            customer_lang = await sync_to_async(lambda: getattr(customer.profile, 'language', 'KO').upper())()

            # 만약 고객 언어가 한국어이면 번역 없이 그대로 사용합니다.
            if customer_lang == "KO":
                translated_content = None
            else:
                if sender_role in ["ADMIN", "MANAGER"]:
                    # 매니저 또는 어드민이 보낼 경우: 고객이 선택한 언어로 번역
                    target_lang = customer_lang
                    translated_content = await sync_to_async(translate_text)(content, target_lang)
                else:
                    # 고객이 보낼 경우: 한국어("KO")로 번역
                    target_lang = "KO"
                    translated_content = await sync_to_async(translate_text)(content, target_lang)

            message = await sync_to_async(Message.objects.create)(
                room=self.chat_room,
                sender=self.user,
                content=content,
                translated_content=translated_content,
                file_url=file_url,
                file_name=file_name,
                file_type=file_type
            )


            message_time_kst = localtime(message.created_at)

            payload = {
                "type": "multiplex_message",  # 아래 multiplex_message 메서드가 처리합니다.
                "sender": self.user.username,
                "content": content,
                "translated_content": translated_content,
                "file_url": file_url,
                "file_name": file_name,
                "file_type": file_type,
                "created_at_date": message_time_kst.strftime("%d/%m/%Y"),
                "created_at_time": message_time_kst.strftime("%I:%M %p"),
            }
            # target 값에 따라 해당 그룹으로 메시지 전송
            if target == "chat":
                # 고객 소켓은 자신이 가입한 채팅방 그룹으로 전송
                if hasattr(self, "chat_group_name"):
                    await self.channel_layer.group_send(self.chat_group_name, payload)
                # 그리고, DB에서 채팅방 정보를 조회해서 basespace 기반의 매니저 그룹으로도 전송
                chat_room = await sync_to_async(ChatRoom.objects.select_related('basespace').get)(id=self.room_id)
                manager_group_name = f"manager_{chat_room.basespace.id}"
                payload_with_room = payload.copy()
                payload_with_room["chat_room"] = self.room_id  # 어느 채팅방에서 온 메시지인지 명시
                await self.channel_layer.group_send(manager_group_name, payload_with_room)
            elif target == "manager":
                # 만약 관리자가 직접 메시지를 보내는 경우
                if hasattr(self, "manager_group_name"):
                    payload["chat_room"] = self.room_id if hasattr(self, "room_id") else None
                    await self.channel_layer.group_send(self.manager_group_name, payload)
                else:
                    await self.send(json.dumps({"error": "매니저 그룹에 연결되어 있지 않습니다."}))
            else:
                await self.send(json.dumps({"error": "잘못된 target 값입니다."}))

            await send_notification_to_users(
                [customer.id],
                {
                    "sender": self.user,
                    "title": "새 채팅 메시지",
                    "content": content,
                    "notification_type": "MESSAGE",
                    "created_at": message.created_at.isoformat(),
                }
            )

            if self.chat_room.is_answered:
                self.chat_room.is_answered = False
                await sync_to_async(self.chat_room.save, thread_sensitive=True)()
        except Exception as e:
            await self.send(json.dumps({"error": str(e)}))

    async def multiplex_message(self, event):
        # 그룹에서 전송된 메시지를 클라이언트에 그대로 전달
        await self.send(text_data=json.dumps(event, ensure_ascii=False))

    async def manager_notification(self, event):
        """ 매니저에게 알림을 전달하는 함수 """
        await self.send(text_data=json.dumps(event, ensure_ascii=False))

    async def send_notification(self, event):
        """ 알림을 전달하는 함수 """
        await self.send(text_data=json.dumps(event, ensure_ascii=False))