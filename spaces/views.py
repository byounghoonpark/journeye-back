from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from accounts.permissions import IsAdminOrManager
from bookings.serializers import HotelRoomMemoSerializer, HotelRoomHistorySerializer
from .models import (
    HotelRoom,
    HotelRoomType,
    Hotel,
    SpacePhoto,
    Floor,
    HotelRoomHistory,
    HotelRoomMemo,
    Facility
)

from .serializers import (
    HotelRoomSerializer,
    HotelRoomTypeSerializer,
    HotelSerializer,
    FloorSerializer,
    HotelDetailSerializer,
    FacilitySerializer, FacilityDetailSerializer
)
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class HotelViewSet(ModelViewSet):
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.action in ["list", "retrieve", "get_detail"]:
            return [AllowAny()]
        return [IsAuthenticated(), IsAdminOrManager()]

    @action(detail=True, methods=['get'], url_path='detail')
    def get_detail(self, request, pk=None):
        hotel = self.get_object()
        serializer = HotelDetailSerializer(hotel)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=HotelSerializer,
        manual_parameters=[
            openapi.Parameter(
                "photos",
                openapi.IN_FORM,
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_FILE),
                description="호텔 사진 업로드 (여러 파일 가능)"
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        if request.user.profile.role not in ["MANAGER", "ADMIN"]:
            return Response({"error": "매니저만 등록할 수 있습니다."}, status=status.HTTP_403_FORBIDDEN)

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        hotel = serializer.save()
        hotel.managers.add(self.request.user)  # 자동으로 매니저 등록



class HotelRoomTypeViewSet(ModelViewSet):
    queryset = HotelRoomType.objects.all()
    serializer_class = HotelRoomTypeSerializer
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["basespace"]

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.action == "list":
            basespace_id = self.request.query_params.get("basespace_id")
            if basespace_id:
                queryset = queryset.filter(basespace_id=basespace_id)

        return queryset

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated(), IsAdminOrManager()]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "basespace_id",
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="조회할 특정 BaseSpace ID (필터링, 리스트 조회에서만 사용)",
                required=False
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=HotelRoomTypeSerializer,
        manual_parameters=[

            openapi.Parameter(
                "photos",
                openapi.IN_FORM,
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_FILE),
                description="객실 유형 사진 업로드 (여러 파일 가능)"
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        response =  super().create(request, *args, **kwargs)
        hotel_room_type = HotelRoomType.objects.get(id=response.data["id"])

        photos = request.FILES.getlist("photos")
        for image_file in photos:
            SpacePhoto.objects.create(space=hotel_room_type, image=image_file)

        return Response(HotelRoomTypeSerializer(hotel_room_type).data, status=status.HTTP_201_CREATED)


class HotelRoomViewSet(ModelViewSet):
    queryset = HotelRoom.objects.all().order_by('-id')
    serializer_class = HotelRoomSerializer
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get_queryset(self):
        queryset = super().get_queryset()
        basespace_id = self.request.query_params.get('basespace_id')
        if basespace_id:
            queryset = queryset.filter(room_type__basespace_id=basespace_id)
        return queryset

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'basespace_id',
                openapi.IN_QUERY,
                description="특정 BaseSpace ID 필터 (예: ?basespace_id=1)",
                type=openapi.TYPE_INTEGER
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'room_type': openapi.Schema(type=openapi.TYPE_INTEGER, description='객실 타입의 ID'),
                'floor': openapi.Schema(type=openapi.TYPE_INTEGER, description='층', nullable=True),
                'room_number': openapi.Schema(type=openapi.TYPE_STRING, description='호실', maxLength=50, nullable=True),
                'status': openapi.Schema(type=openapi.TYPE_STRING, description='객실 상태', maxLength=50, nullable=True),
                'non_smoking': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='금연 여부')
            },
            required=['room_type']
        )
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        response = super().partial_update(request, *args, **kwargs)

        if 'status' in request.data:
            HotelRoomHistory.objects.create(
                hotel_room=instance,
                history_content=instance.status
            )

        return response

class HotelRoomMemoViewSet(ModelViewSet):
    queryset = HotelRoomMemo.objects.all().order_by('-id')
    serializer_class = HotelRoomMemoSerializer
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get_queryset(self):
        queryset = super().get_queryset()
        room_id = self.request.query_params.get('room_id')
        if room_id:
            queryset = queryset.filter(hotel_room_id=room_id)
        return queryset

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'room_id',
                openapi.IN_QUERY,
                description="특정 방 ID 필터 (예: ?room_id=1)",
                type=openapi.TYPE_INTEGER
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class FloorViewSet(ModelViewSet):
    queryset = Floor.objects.all()
    serializer_class = FloorSerializer
    permission_classes = [IsAuthenticated, IsAdminOrManager]
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["basespace"]

    def get_queryset(self):
        queryset = super().get_queryset()
        basespace_id = self.request.query_params.get("basespace_id")
        if basespace_id:
            queryset = queryset.filter(basespace_id=basespace_id)
        return queryset

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated(), IsAdminOrManager()]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "basespace_id",
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description="조회할 특정 BaseSpace ID (필터링, 리스트 조회에서만 사용)",
                required=False
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class HotelRoomHistoryViewSet(ModelViewSet):
    queryset = HotelRoomHistory.objects.all().order_by('-id')
    serializer_class = HotelRoomHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        room_id = self.request.query_params.get('room_id')
        if room_id:
            queryset = queryset.filter(hotel_room_id=room_id)
        return queryset

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'room_id',
                openapi.IN_QUERY,
                description="특정 방 ID 필터 (예: ?room_id=1)",
                type=openapi.TYPE_INTEGER
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if response.status_code == status.HTTP_201_CREATED:
            history = HotelRoomHistory.objects.get(id=response.data['id'])
            hotel_room = history.hotel_room
            hotel_room.status = history.history_content
            hotel_room.save()
        return response


class FacilityViewSet(ModelViewSet):
    queryset = Facility.objects.all()
    serializer_class = FacilitySerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.action in ["list", "retrieve", "get_detail"]:
            return [AllowAny()]
        return [IsAuthenticated(), IsAdminOrManager()]

    @swagger_auto_schema(
        request_body=FacilitySerializer,
        manual_parameters=[
            openapi.Parameter(
                "photos",
                openapi.IN_FORM,
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_FILE),
                description="시설 사진 업로드 (여러 파일 가능)"
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        facility = Facility.objects.get(id=response.data['id'])
        facility.managers.add(request.user)  # 등록한 사람을 관리자로 추가
        return response


    @action(detail=True, methods=['get'], url_path='detail')
    def get_detail(self, request, pk=None):
        facility = self.get_object()
        serializer = FacilityDetailSerializer(facility)
        return Response(serializer.data)