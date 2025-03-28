from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AIConciergeViewSet, ConciergeAssignmentViewSet

router = DefaultRouter()
router.register(r'concierges', AIConciergeViewSet, basename='ai_concierge')
router.register(r'assignments', ConciergeAssignmentViewSet, basename='concierge_assignment')

urlpatterns = [
    path('', include(router.urls)),
]