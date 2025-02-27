from http.client import responses

from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from accounts.permissions import IsAdminOrManager
from .models import HotelRoom, HotelRoomType, Hotel, BaseSpacePhoto, SpacePhoto
from .serializers import HotelRoomSerializer, HotelRoomTypeSerializer, HotelSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class HotelViewSet(ModelViewSet):
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated(), IsAdminOrManager()]

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
    filter_backends = [DjangoFilterBackend]  # ✅ 필터링 추가
    filterset_fields = ["basespace"]  # ✅ basespace_id 필터링 가능

    def get_queryset(self):
        """
        ✅ basespace_id 쿼리 파라미터가 있으면 필터링
        """
        queryset = super().get_queryset()
        basespace_id = self.request.query_params.get("basespace")
        if basespace_id:
            queryset = queryset.filter(basespace_id=basespace_id)
        return queryset

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]
        return [IsAuthenticated(), IsAdminOrManager()]

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

