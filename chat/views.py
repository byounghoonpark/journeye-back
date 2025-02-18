from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from .models import ChatRoom, Message, ShopUser, VisitorUser
from .serializers import ChatRoomSerializer, MessageSerializer
from rest_framework.exceptions import ValidationError
from django.http import Http404
from django.http import JsonResponse
from django.conf import settings
from drf_yasg import openapi


# 사용자 정의 예외 클래스, 예외 발생 시 즉각적인 HTTP 응답을 위해 사용됩니다.
class ImmediateResponseException(Exception):
    # 예외 인스턴스를 생성할 때 HTTP 응답 객체를 받습니다.
    def __init__(self, response):
        self.response = response


# 채팅방 목록 조회 및 생성을 위한 뷰 클래스로, DRF의 generics.ListCreateAPIView를 상속받습니다.
class ChatRoomListCreateView(generics.ListCreateAPIView):
    # 이 뷰에서 사용할 시리얼라이저를 지정합니다.
    serializer_class = ChatRoomSerializer

    # GET 요청에 대한 쿼리셋을 정의하는 메소드입니다.
    def get_queryset(self):
        try:
            # 요청의 쿼리 파라미터에서 'email' 값을 가져옵니다. 없다면 None을 반환합니다.
            user_email = self.request.query_params.get('email', None)

            # 이메일 파라미터가 없으면 ValidationError 예외를 발생시킵니다.
            if not user_email:
                raise ValidationError('Email 파라미터가 필요합니다.')

            # 채팅방 객체를 필터링하여, 해당 이메일을 가진 사용자가 속한 채팅방을 찾습니다.
            return ChatRoom.objects.filter(
                shop_user__shop_user_email=user_email
            ) | ChatRoom.objects.filter(
                visitor_user__visitor_user_email=user_email
            )
        except ValidationError as e:
            # ValidationError 발생 시, 상태 코드 400과 함께 에러 상세 정보를 반환합니다.
            content = {'detail': e.detail}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # 다른 종류의 예외 발생 시, 상태 코드 400과 함께 에러 상세 정보를 반환합니다.
            # 여기에서 예외 정보를 로깅할 수 있습니다.
            content = {'detail': str(e)}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)

    # 시리얼라이저의 컨텍스트를 설정하는 메소드입니다.
    def get_serializer_context(self):
        # 부모 클래스의 컨텍스트 가져오기 메소드를 호출합니다.
        context = super(ChatRoomListCreateView, self).get_serializer_context()
        # 컨텍스트에 현재의 요청 객체를 추가합니다.
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        # 요청 데이터로부터 시리얼라이저를 생성합니다.
        serializer = self.get_serializer(data=request.data)
        # 시리얼라이저의 유효성 검사를 수행합니다. 유효하지 않을 경우 예외가 발생합니다.
        serializer.is_valid(raise_exception=True)
        try:
            # 시리얼라이저를 통해 데이터 저장을 수행합니다.
            self.perform_create(serializer)
        except ImmediateResponseException as e:
            # 즉각적인 응답이 필요할 경우 예외를 통해 응답을 반환합니다.
            return e.response
        # 성공 헤더를 생성합니다.
        headers = self.get_success_headers(serializer.data)
        # 상태 코드 201를 반환하며 새로 생성된 데이터를 응답합니다.
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    # 시리얼라이저를 통해 데이터베이스에 객체를 저장하는 메소드입니다.
    def perform_create(self, serializer):
        # 요청 데이터에서 shop_user_email과 visitor_user_email을 가져옵니다.
        shop_user_email = self.request.data.get('shop_user_email')
        visitor_user_email = self.request.data.get('visitor_user_email')

        # 해당 이메일로 ShopUser와 VisitorUser를 가져오거나 없으면 생성합니다.
        shop_user, _ = ShopUser.objects.get_or_create(shop_user_email=shop_user_email)
        visitor_user, _ = VisitorUser.objects.get_or_create(visitor_user_email=visitor_user_email)

        # 동일한 shop_user_email과 visitor_user_email을 가진 채팅방이 이미 있는지 확인합니다.
        existing_chatroom = ChatRoom.objects.filter(shop_user__shop_user_email=shop_user_email,
                                                    visitor_user__visitor_user_email=visitor_user_email).first()

        # 이미 존재하는 채팅방이 있다면 해당 채팅방의 정보를 시리얼라이즈하여 응답합니다.
        if existing_chatroom:
            serializer = ChatRoomSerializer(existing_chatroom, context={'request': self.request})
            raise ImmediateResponseException(Response(serializer.data, status=status.HTTP_200_OK))

        # 새 채팅방 객체를 저장합니다.
        serializer.save(shop_user=shop_user, visitor_user=visitor_user)


# 메시지 목록을 조회하는 뷰 클래스로, DRF의 generics.ListAPIView를 상속받습니다.
class MessageListView(generics.ListAPIView):
    # 이 뷰에서 사용할 시리얼라이저를 지정합니다.
    serializer_class = MessageSerializer

    # GET 요청에 대한 쿼리셋을 정의하는 메소드입니다.
    def get_queryset(self):
        # URL 파라미터에서 'room_id' 값을 가져옵니다.
        room_id = self.kwargs.get('room_id')

        # room_id가 제공되지 않았을 경우 에러 메시지와 함께 400 상태 코드 응답을 반환합니다.
        if not room_id:
            content = {'detail': 'room_id 파라미터가 필요합니다.'}
            return Response(content, status=status.HTTP_400_BAD_REQUEST)

        # room_id에 해당하는 메시지 객체들을 쿼리셋으로 가져옵니다.
        queryset = Message.objects.filter(room_id=room_id)

        # 해당 room_id의 메시지가 존재하지 않을 경우 404 Not Found 예외를 발생시킵니다.
        if not queryset.exists():
            raise Http404('해당 room_id로 메시지를 찾을 수 없습니다.')

        # 쿼리셋을 반환합니다.
        return queryset