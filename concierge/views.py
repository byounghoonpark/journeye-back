from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django.db.models import Sum
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from accounts.permissions import IsAdminOrManager
from spaces.models import Space, BaseSpace
from .models import AIConcierge, ConciergeAssignment
from .serializers import (
    AIConciergeCreateSerializer,
    AIConciergeSerializer,
    ConciergeAssignmentCreateSerializer, SpaceSerializer
)


class AIConciergeViewSet(viewsets.ModelViewSet):
    queryset = AIConcierge.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return AIConciergeCreateSerializer
        return AIConciergeSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'detail_by_pk', 'nearby']:
            return [AllowAny()]
        return [IsAuthenticated(), IsAdminOrManager()]

    @swagger_auto_schema(
        operation_description="AIConcierge 생성",
        request_body=AIConciergeCreateSerializer,
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='detail/(?P<pk>[^/.]+)')
    def detail_by_pk(self, request, pk=None):
        concierge = get_object_or_404(AIConcierge, pk=pk)
        serializer = self.get_serializer(concierge)
        response_data = serializer.data

        # type_name으로 변경하고 맨 위로 이동
        response_data = {'type_name': response_data.pop('name'), **response_data}

        for assignment in response_data['assignments']:
            assignment['content_name'] = assignment.pop('name')
            basespace = BaseSpace.objects.get(pk=assignment['basespace'])
            assignment['phone'] = basespace.phone

        # 가격 정보와 Full Charge 계산
        assignments = ConciergeAssignment.objects.filter(concierge=concierge)
        spaces = Space.objects.filter(basespace__concierge_assignments__in=assignments)
        space_prices = SpaceSerializer(spaces, many=True).data


        full_charge = spaces.aggregate(Sum('price'))['price__sum']

        response_data['space_prices'] = space_prices
        response_data['full_charge'] = full_charge

        return Response(response_data)

    @swagger_auto_schema(
        operation_description="위도와 경도를 기준으로 근처 AI 컨시어지들을 가까운 순서대로 최대 6개까지 반환합니다.",
        manual_parameters=[
            openapi.Parameter('latitude', openapi.IN_QUERY, type=openapi.TYPE_NUMBER, description='위도', required=True),
            openapi.Parameter('longitude', openapi.IN_QUERY, type=openapi.TYPE_NUMBER, description='경도', required=True),
        ],
        responses={200: AIConciergeSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='nearby')
    def nearby(self, request):
        latitude = request.query_params.get('latitude')
        longitude = request.query_params.get('longitude')

        if not latitude or not longitude:
            return Response({"error": "위도와 경도를 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_location = Point(float(longitude), float(latitude), srid=4326)
        except ValueError:
            return Response({"error": "위도와 경도는 숫자여야 합니다."}, status=status.HTTP_400_BAD_REQUEST)

        nearby_concierges = AIConcierge.objects.annotate(distance=Distance('location', user_location)).order_by(
            'distance')[:6]
        result = [{'pk': concierge.pk, 'name': concierge.name} for concierge in nearby_concierges]
        return Response(result, status=status.HTTP_200_OK)


class ConciergeAssignmentViewSet(viewsets.ModelViewSet):
    queryset = ConciergeAssignment.objects.all()
    serializer_class = ConciergeAssignmentCreateSerializer

