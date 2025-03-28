from drf_yasg.utils import swagger_auto_schema
from django.db.models import Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404

from accounts.permissions import IsAdminOrManager
from spaces.models import Space
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
        if self.action in ['list', 'retrieve', 'detail_by_pk']:
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

        # 가격 정보와 Full Charge 계산
        assignments = ConciergeAssignment.objects.filter(concierge=concierge)
        spaces = Space.objects.filter(basespace__concierge_assignments__in=assignments)
        space_prices = SpaceSerializer(spaces, many=True).data

        full_charge = spaces.aggregate(Sum('price'))['price__sum']

        response_data['space_prices'] = space_prices
        response_data['full_charge'] = full_charge

        return Response(response_data)


class ConciergeAssignmentViewSet(viewsets.ModelViewSet):
    queryset = ConciergeAssignment.objects.all()
    serializer_class = ConciergeAssignmentCreateSerializer

