from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ModelViewSet

from accounts.permissions import IsAdminOrManager
from .models import HotelRoom, HotelRoomType
from .serializers import HotelCreateSerializer, HotelRoomSerializer, HotelRoomTypeSerializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class HotelCreateView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrManager]  # 로그인한 유저만 접근 가능
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        consumes=['multipart/form-data'],
        operation_description="새로운 호텔을 등록하는 API (관리자 이상만 가능)",
        request_body=HotelCreateSerializer,
        responses={
            201: openapi.Response(
                description="호텔 등록 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_INTEGER, description="호텔 ID"),
                        "name": openapi.Schema(type=openapi.TYPE_STRING, description="호텔 이름"),
                        "address": openapi.Schema(type=openapi.TYPE_STRING, description="호텔 주소"),
                        "phone": openapi.Schema(type=openapi.TYPE_STRING, description="연락처"),
                        "introduction": openapi.Schema(type=openapi.TYPE_STRING, description="호텔 소개"),
                        "latitude": openapi.Schema(type=openapi.TYPE_NUMBER, format=openapi.FORMAT_FLOAT, description="위도"),
                        "longitude": openapi.Schema(type=openapi.TYPE_NUMBER, format=openapi.FORMAT_FLOAT, description="경도"),
                        "additional_services": openapi.Schema(type=openapi.TYPE_STRING, description="추가 서비스"),
                        "facilities": openapi.Schema(type=openapi.TYPE_STRING, description="시설 정보"),
                    },
                ),
            ),
            400: openapi.Response(description="잘못된 요청"),
            403: openapi.Response(description="권한 없음 (매니저만 가능)"),
        },
        manual_parameters=[
            openapi.Parameter(
                'photos',
                openapi.IN_FORM,
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_STRING, format="binary"),
                description="호텔 사진 업로드 (여러 파일 선택 가능)"
            )
        ]
    )
    def post(self, request):
        """ 호텔 등록 API (Swagger 입력 가능) """
        if request.user.profile.role not in ["SPACE_MANAGER", "SUPER_ADMIN"]:
            return Response({"error": "매니저만 등록할 수 있습니다."}, status=status.HTTP_403_FORBIDDEN)

        serializer = HotelCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            hotel = serializer.save()
            hotel.managers.add(request.user)
            return Response({
                "id": hotel.id,
                "name": hotel.name,
                "address": hotel.address,
                "phone": hotel.phone,
                "introduction": hotel.introduction,
                "latitude": hotel.location.y,  # GeoDjango에서 y = 위도(latitude)
                "longitude": hotel.location.x,  # GeoDjango에서 x = 경도(longitude)
                "additional_services": hotel.additional_services,
                "facilities": hotel.facilities,
                "photos": [photo.image.url for photo in hotel.photos.all()],
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HotelRoomViewSet(ModelViewSet):
    queryset = HotelRoom.objects.all().order_by('-id')
    serializer_class = HotelRoomSerializer
    permission_classes = [IsAuthenticated, IsAdminOrManager]


class HotelRoomTypeViewSet(ModelViewSet):
    queryset = HotelRoomType.objects.all().order_by('-id')
    serializer_class = HotelRoomTypeSerializer
    permission_classes = [IsAuthenticated, IsAdminOrManager]
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated, IsAdminOrManager]
        return [permission() for permission in permission_classes]