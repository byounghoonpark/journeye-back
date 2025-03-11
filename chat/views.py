import boto3
from django.conf import settings
from django.utils.timezone import now
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from bookings.models import CheckIn
from .models import ChatRoom, Message, ChatRoomParticipant
from .serializers import ChatRoomSerializer, MessageSerializer, ChatRoomListSerializer, ManagerChatRoomSerializer, \
    CustomerChatRoomSerializer

# MinIO (S3) 클라이언트 설정
s3_client = boto3.client(
    's3',
    endpoint_url=settings.AWS_S3_ENDPOINT_URL,
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
)


# 관리자/매니저 권한은 UserProfile.role로 판단한다고 가정 (예: "ADMIN", "MANAGER")
# 관리자/매니저이면 전체 활성 채팅방을 조회할 수 있도록 get_queryset에서 처리합니다.
class ChatRoomViewSet(viewsets.ModelViewSet):
    """
    - 로그인한 사용자의 현재 체크인 정보를 기준으로 채팅방을 생성하거나 반환합니다.
    - 관리자인 경우(UserProfile.role이 ADMIN 또는 MANAGER) 모든 활성 채팅방을 조회할 수 있습니다.
    """
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Swagger 스키마 생성을 위한 가짜 뷰일 경우 빈 QuerySet 반환
        if getattr(self, 'swagger_fake_view', False):
            return ChatRoom.objects.none()

        user = self.request.user
        # 인증되지 않은 사용자라면 빈 QuerySet 반환
        if not user.is_authenticated:
            return ChatRoom.objects.none()

        # 관리자나 매니저인 경우 전체 활성 채팅방 반환
        if hasattr(user, 'profile') and user.profile.role in ['ADMIN', 'MANAGER']:
            return ChatRoom.objects.filter(is_active=True)

        # 일반 사용자의 경우 체크인 정보를 기반으로 채팅방 반환
        check_in = CheckIn.objects.filter(
            user=user,
            check_in_date__lte=now().date(),
            check_out_date__gte=now().date(),
            checked_out=False
        ).first()
        if check_in:
            return ChatRoom.objects.filter(checkin=check_in)
        return ChatRoom.objects.none()


    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter(
            'basespace_id',
            openapi.IN_QUERY,
            description="베이스스페이스 ID",
            type=openapi.TYPE_INTEGER
        )
    ])
    def list(self, request, *args, **kwargs):
        basespace_id = request.query_params.get('basespace_id')
        queryset = self.get_queryset()
        if basespace_id:
            queryset = queryset.filter(basespace_id=basespace_id)
        serializer = ChatRoomListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)


    def create(self, request, *args, **kwargs):
        """
        로그인한 사용자의 현재 체크인 정보를 기준으로 채팅방을 생성합니다.
        체크인 내역이 없으면 에러를 반환합니다.
        """
        user = request.user
        check_in = CheckIn.objects.filter(
            user=user,
            # check_in_date__lte=now().date(),
            # check_out_date__gte=now().date(),
            checked_out=False
        ).first()
        if not check_in:
            return Response({"error": "현재 체크인 내역이 없습니다."}, status=status.HTTP_400_BAD_REQUEST)
        chat_room, created = ChatRoom.objects.get_or_create(
            checkin=check_in,
            basespace=check_in.hotel_room.room_type.basespace,
        )
        ChatRoomParticipant.objects.get_or_create(chatroom=chat_room, user=user)
        serializer = ChatRoomSerializer(chat_room)
        message = "채팅방이 생성되었습니다." if created else "기존 채팅방을 불러왔습니다."
        return Response({
            "chat_room_id": chat_room.id,
            "is_active": chat_room.is_active,
            "message": message,
            "chat_room": serializer.data
        }, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter(
            'is_translated',
            openapi.IN_QUERY,
            description="True일 경우 고객 메시지를 번역한 내용을 보여줍니다.",
            type=openapi.TYPE_BOOLEAN,
            required=False
        )
    ])
    def retrieve(self, request, *args, **kwargs):
        """
        특정 채팅방의 상세 정보를 반환합니다.
        체크인한 본인(또는 관리자/매니저)만 접근할 수 있습니다.
        """
        instance = self.get_object()
        # 본인의 채팅방이 아니고 관리자가 아니라면 접근 거부
        if request.user != instance.checkin.user and request.user.profile.role not in ['ADMIN', 'MANAGER']:
            return Response({"error": "채팅방에 접근할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        participant, created = ChatRoomParticipant.objects.get_or_create(
            chatroom=instance, user=request.user
        )
        participant.last_read_time = now()
        participant.save()

        is_translated = request.query_params.get("is_translated", "false").lower() == "true"

        if hasattr(request.user, 'profile') and request.user.profile.role in ['ADMIN', 'MANAGER']:
            serializer = ManagerChatRoomSerializer(instance, context={'request': request})
        else:
            serializer = CustomerChatRoomSerializer(instance, context={'request': request})

        data = serializer.data

        if is_translated and "messages" in data:
            customer_username = instance.checkin.user.username
            for message in data["messages"]:
                if message.get("sender") == customer_username:
                    message["content"] = message.get("translated_content", message.get("content"))

        return Response(data)


    @action(detail=True, methods=['post'])
    def mark_as_answered(self, request, pk=None):
        chat_room = self.get_object()
        if request.user.profile.role not in ['ADMIN', 'MANAGER']:
            return Response({"error": "권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
        chat_room.is_answered = True
        chat_room.save()
        return Response({"message": "답변 완료 상태로 변경되었습니다."}, status=status.HTTP_200_OK)


class MessageViewSet(viewsets.ModelViewSet):
    """
    - 특정 채팅방의 모든 채팅 메시지 및 파일 내역을 조회하고, 메시지(텍스트, 파일)를 전송합니다.
    - 파일 업로드 시 MinIO/S3에 업로드하고, 업로드된 파일 URL을 메시지에 포함합니다.
    - 전송 후 WebSocket을 통해 실시간 알림을 보냅니다.
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter(
            'room_id',
            openapi.IN_QUERY,
            description="채팅방 ID",
            type=openapi.TYPE_INTEGER
        )
    ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Message.objects.none()

        user = self.request.user
        if not user.is_authenticated:
            return Message.objects.none()

        room_id = self.request.query_params.get('room_id')
        if room_id:
            try:
                chat_room = ChatRoom.objects.get(id=room_id)
            except ChatRoom.DoesNotExist:
                return Message.objects.none()

            chatroom_checkin_user = chat_room.checkin.user
            user_role = user.profile.role if hasattr(user, 'profile') else None
            if user != chatroom_checkin_user:
                if user_role == 'ADMIN':
                    pass
                elif user_role == 'MANAGER':
                    is_manager = chat_room.basespace.managers.filter(id=user.id).exists()
                    if not is_manager:
                        return Message.objects.none()
                else:
                    return Message.objects.none()

            return Message.objects.filter(room=chat_room).order_by("created_at")
        return Message.objects.none()

    def create(self, request, *args, **kwargs):
        """
        로그인한 사용자가 메시지를 전송합니다.
        파일이 포함된 경우 S3에 업로드 후 메시지 생성 및 WebSocket으로 전송합니다.
        """
        user = request.user
        chat_room_id = request.data.get('room')
        if chat_room_id:
            try:
                chat_room = ChatRoom.objects.get(id=chat_room_id)
            except ChatRoom.DoesNotExist:
                return Response({"error": "채팅방이 존재하지 않습니다."}, status=status.HTTP_400_BAD_REQUEST)

            # 접근 권한 검증 (예: 체크인 고객, 해당 호텔의 관리자/매니저 등)
            chatroom_checkin_user = chat_room.checkin.user
            user_role = user.profile.role if hasattr(user, 'profile') else None
            if user != chatroom_checkin_user:
                if user_role == 'ADMIN':
                    pass  # 관리자 허용
                elif user_role == 'MANAGER':
                    is_manager = chat_room.basespace.managers.filter(id=user.id).exists()
                    if not is_manager:
                        return Response({"error": "해당 호텔의 매니저만 접근할 수 있습니다."}, status=status.HTTP_403_FORBIDDEN)
                else:
                    return Response({"error": "접근 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
        else:
            # 요청 데이터에 채팅방 ID가 없는 경우, 기본적으로 사용자의 체크인에 연결된 채팅방을 조회합니다.
            check_in = CheckIn.objects.filter(
                user=user,
                check_in_date__lte=now().date(),
                check_out_date__gte=now().date(),
                checked_out=False
            ).first()
            if not check_in:
                return Response({"error": "현재 체크인 내역이 없습니다."}, status=status.HTTP_400_BAD_REQUEST)
            chat_room = ChatRoom.objects.filter(checkin=check_in).first()
            if not chat_room:
                return Response({"error": "채팅방이 존재하지 않습니다."}, status=status.HTTP_400_BAD_REQUEST)

        file_url = None
        file_name = None
        file_type = None

        # 파일이 업로드된 경우 S3(MinIO)에 업로드
        if "file" in request.FILES:
            file = request.FILES["file"]
            s3_client.upload_fileobj(file, settings.AWS_STORAGE_BUCKET_NAME, file.name)
            file_url = f"{settings.AWS_S3_CUSTOM_DOMAIN}/{file.name}"
            file_name = file.name
            file_type = file.content_type

        # 파일 관련 항목은 request.data에서 제거(이미 별도 처리됨)
        data = request.data.dict()
        serializer = MessageSerializer(data=data)
        if serializer.is_valid():
            message = serializer.save(
                room=chat_room,
                sender=user,
                file_url=file_url,
                file_name=file_name,
                file_type=file_type
            )
            chat_room.is_answered = False
            chat_room.save()
            # WebSocket 실시간 전송
            channel_layer = get_channel_layer()
            # 채팅방에 메시지 전송
            async_to_sync(channel_layer.group_send)(
                f"chat_{chat_room.id}",
                {
                    "type": "multiplex_message",
                    "sender": message.sender.username,
                    "content": message.content,
                    "file_url": file_url,
                    "file_name": file_name,
                    "file_type": file_type,
                    "created_at": str(message.created_at),
                }
            )
            # 매니저에게 알림 전송
            async_to_sync(channel_layer.group_send)(
                f"manager_{chat_room.basespace.id}",
                {
                    "type": "manager_notification",
                    "chat_room": chat_room.id,  # 어느 채팅방에서 온 메시지인지 전달
                    "sender": message.sender.username,
                    "content": message.content,
                    "file_type": file_type,
                    "created_at": str(message.created_at),
                }
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UnreadChatRoomsCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.profile.role not in ['ADMIN', 'MANAGER']:
            return Response({"error": "권한이 없습니다."}, status=403)

        # 관리자가 참여한 모든 채팅방 조회
        chat_rooms = ChatRoom.objects.filter(participants__user=user)

        # 읽지 않은 메시지가 있는 채팅방 수 계산
        unread_chat_rooms_count = 0
        for chat_room in chat_rooms:
            participant = ChatRoomParticipant.objects.get(chatroom=chat_room, user=user)
            if participant.last_read_time:
                unread_messages_count = Message.objects.filter(
                    room=chat_room,
                    created_at__gt=participant.last_read_time
                ).count()
            else:
                unread_messages_count = Message.objects.filter(room=chat_room).count()

            if unread_messages_count > 0:
                unread_chat_rooms_count += 1

        return Response({"unread_chat_rooms_count": unread_chat_rooms_count})