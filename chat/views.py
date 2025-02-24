from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.http import Http404
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message
from .serializers import ChatRoomSerializer, MessageSerializer

User = get_user_model()

# 사용자 정의 예외: 즉각적인 HTTP 응답을 위해 사용합니다.
class ImmediateResponseException(Exception):
    def __init__(self, response):
        self.response = response

# 호텔 관리자와 일반 사용자 간의 채팅방 목록 조회 및 생성 API
class ChatRoomListCreateView(generics.ListCreateAPIView):
    serializer_class = ChatRoomSerializer

    def get_queryset(self):
        user_email = self.request.query_params.get('email')
        if not user_email:
            raise ValidationError('Email 파라미터가 필요합니다.')
        # hotel_admin 또는 user 필드에 해당 이메일이 있는 채팅방 모두 반환
        return ChatRoom.objects.filter(hotel_admin__email=user_email) | \
               ChatRoom.objects.filter(user__email=user_email)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
        except ImmediateResponseException as e:
            return e.response
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        # 요청 데이터로부터 호텔 관리자와 일반 사용자 이메일을 추출합니다.
        hotel_admin_email = self.request.data.get('hotel_admin_email')
        user_email = self.request.data.get('user_email')
        if not hotel_admin_email or not user_email:
            raise ValidationError('Both hotel_admin_email and user_email are required.')

        try:
            hotel_admin = User.objects.get(email=hotel_admin_email, type='hotel_admin')
        except User.DoesNotExist:
            raise ValidationError("호텔 관리자 이메일이 올바르지 않거나 존재하지 않습니다.")

        try:
            normal_user = User.objects.get(email=user_email, type='user')
        except User.DoesNotExist:
            raise ValidationError("일반 사용자 이메일이 올바르지 않거나 존재하지 않습니다.")

        # 이미 동일한 호텔 관리자와 일반 사용자 간의 채팅방이 존재하는지 확인합니다.
        existing_chatroom = ChatRoom.objects.filter(hotel_admin=hotel_admin, user=normal_user).first()
        if existing_chatroom:
            serializer = ChatRoomSerializer(existing_chatroom, context={'request': self.request})
            raise ImmediateResponseException(Response(serializer.data, status=status.HTTP_200_OK))

        # 새 채팅방 생성
        serializer.save(hotel_admin=hotel_admin, user=normal_user)

# 특정 채팅방의 메시지 목록 조회 API
class MessageListView(generics.ListAPIView):
    serializer_class = MessageSerializer

    def get_queryset(self):
        room_id = self.kwargs.get('room_id')
        if not room_id:
            raise ValidationError('room_id 파라미터가 필요합니다.')
        queryset = Message.objects.filter(chat_room_id=room_id)
        if not queryset.exists():
            raise Http404('해당 room_id로 메시지를 찾을 수 없습니다.')
        return queryset
