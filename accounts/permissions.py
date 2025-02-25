# permissions.py
from rest_framework.permissions import BasePermission, IsAdminUser


class IsAdminOrManager(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.profile.role == "SPACE_MANAGER" or IsAdminUser().has_permission(request, view)
        )
class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return obj.user == request.user