import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from urllib.parse import parse_qs
from spaces.models import BaseSpace
from .models import ChatRoom, Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """ WebSocket 연결 시 실행되는 함수 """
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.user = self.scope["user"]  # JWT 인증된 사용자

        # ✅ 인증되지 않은 사용자는 연결 차단
        if self.user.is_anonymous:
            await self.close()
            return

        # ✅ 채팅방 정보 가져오기
        try:
            self.chatroom = await sync_to_async(
                ChatRoom.objects.select_related('checkin__user', 'basespace').get
            )(id=self.room_id)
        except ChatRoom.DoesNotExist:
            await self.close()
            return

            # 체크인된 고객, 관리자 또는 호텔 매니저(해당 호텔의 매니저)만 접근 가능하도록 조건 수정
        chatroom_checkin_user = await sync_to_async(lambda: self.chatroom.checkin.user)()
        user_role = await sync_to_async(lambda: self.user.profile.role)()

        # 만약 연결하는 사용자가 체크인한 고객이 아니라면...
        if self.user != chatroom_checkin_user:
            if user_role == 'ADMIN':
                # 관리자이면 허용
                pass
            elif user_role == 'MANAGER':
                # 매니저인 경우, 해당 호텔(BaseSpace)의 매니저 목록에 포함되어 있는지 확인
                is_manager = await sync_to_async(
                    lambda: self.chatroom.basespace.managers.filter(id=self.user.id).exists()
                )()
                if not is_manager:
                    await self.send(json.dumps({"error": "해당 호텔의 매니저만 접근할 수 있습니다."}))
                    await self.close()
                    return
            else:
                await self.send(json.dumps({"error": "접근 권한이 없습니다."}))
                await self.close()
                return

        # ✅ 채팅방이 비활성화된 경우 읽기 전용 (체크아웃된 경우)
        if not self.chatroom.is_active:
            await self.send(json.dumps({"error": "이 채팅방은 비활성화되었습니다."}))
            await self.close()
            return

        # ✅ 채팅방 입장
        self.room_group_name = f"chat_{self.room_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """ 클라이언트로부터 메시지를 받았을 때 실행되는 함수 """
        try:
            data = json.loads(text_data)
            content = data.get('content', "")
            file_url = data.get('file_url', None)
            file_name = data.get('file_name', None)
            file_type = data.get('file_type', None)


            if not self.chatroom.is_active:
                await self.send(json.dumps({"error": "체크아웃된 고객은 메시지를 보낼 수 없습니다."}))
                return

            # ✅ 메시지 저장
            message = await sync_to_async(Message.objects.create)(
                room=self.chatroom,
                sender=self.user,
                content=content,
                file_url=file_url,
                file_name=file_name,
                file_type=file_type
            )

            channel_layer = get_channel_layer()

            await channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'sender': self.user.username,
                    'content': content,
                    'file_url': file_url,
                    'file_name': file_name,
                    'file_type': file_type,
                    'created_at': str(message.created_at)
                }
            )

            # basespace의 매니저 그룹에도 알림 전송
            await channel_layer.group_send(
                f"manager_{self.chatroom.basespace.id}",
                {
                    "type": "manager_notification",
                    "chat_room": self.chatroom.id,
                    "sender": self.user.username,
                    "content": content,
                    "created_at": str(message.created_at),
                }
            )

        except json.JSONDecodeError as e:
            print(f"🚨 JSON 디코딩 오류: {e}")
        except Exception as e:
            print(f"🚨 알 수 없는 오류 발생: {e}")

    async def chat_message(self, event):
        """ 채팅방에 메시지를 전달하는 함수 """
        await self.send(text_data=json.dumps(event, ensure_ascii=False))


class ManagerConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return

        # URL에서 basespace_id 가져오기 (라우팅에서 설정)
        self.basespace_id = self.scope["url_route"]["kwargs"].get("basespace_id")
        if not self.basespace_id:
            await self.close()
            return

        # 해당 basespace가 존재하는지 확인
        try:
            basespace = await sync_to_async(BaseSpace.objects.get)(id=self.basespace_id)
        except BaseSpace.DoesNotExist:
            await self.close()
            return

        # 사용자 역할 확인: 관리자(ADMIN) 또는 매니저(MANAGER)여야 함
        user_role = await sync_to_async(lambda: self.user.profile.role)()
        if user_role not in ['ADMIN', 'MANAGER']:
            await self.send(json.dumps({"error": "매니저나 관리자가 아닙니다."}))
            await self.close()
            return

        # 만약 매니저라면 해당 basespace의 매니저 목록에 포함되어 있는지 확인
        if user_role == 'MANAGER':
            is_manager = await sync_to_async(
                lambda: basespace.managers.filter(id=self.user.id).exists()
            )()
            if not is_manager:
                await self.send(json.dumps({"error": "해당 호텔의 매니저가 아닙니다."}))
                await self.close()
                return

        # 매니저 그룹 이름: 예) "manager_3" (basespace id가 3인 경우)
        self.group_name = f"manager_{self.basespace_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send(json.dumps({"message": "매니저 웹소켓 연결 성공"}))

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def manager_notification(self, event):
        """
        백엔드에서 매니저 그룹으로 전송한 알림 메시지를 클라이언트에 전달합니다.
        페이로드에 chat_room, sender, content, created_at 등이 포함됩니다.
        """
        await self.send(text_data=json.dumps(event, ensure_ascii=False))


class MultiplexConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return

        # 쿼리 문자열에서 room_id와 basespace_id 가져오기
        qs = parse_qs(self.scope.get("query_string", b"").decode())
        self.groups_to_join = []

        # room_id가 있으면 고객용 채팅방 그룹에 가입
        room_ids = qs.get("room_id")
        if room_ids:
            self.room_id = room_ids[0]
            self.chat_group_name = f"chat_{self.room_id}"
            self.groups_to_join.append(self.chat_group_name)

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
        }))

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

            payload = {
                "type": "multiplex_message",  # 아래 multiplex_message 메서드가 처리합니다.
                "sender": self.user.username,
                "content": content,
                "file_url": file_url,
                "file_name": file_name,
                "file_type": file_type,
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
        except Exception as e:
            await self.send(json.dumps({"error": str(e)}))

    async def multiplex_message(self, event):
        # 그룹에서 전송된 메시지를 클라이언트에 그대로 전달
        await self.send(text_data=json.dumps(event, ensure_ascii=False))

    async def manager_notification(self, event):
        """ 매니저에게 알림을 전달하는 함수 """
        await self.send(text_data=json.dumps(event, ensure_ascii=False))