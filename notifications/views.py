from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from .models import Notification
from .serializers import NotificationSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()
        if self.request.user.is_anonymous:
            return Notification.objects.none()
        return self.queryset.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        # 알림을 생성할 때, user를 현재 로그인된 사용자로 고정
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """
        특정 알림을 읽음 처리
        """
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'status': 'marked as read'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        읽지 않은 알림 수를 반환
        """
        count = self.get_queryset().filter(read_at__isnull=True).count()
        return Response({'unread_count': count}, status=status.HTTP_200_OK)
