# App-Level URL Conf
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from core.views import *

# Create a default router and register viewsets:
router = DefaultRouter()
router.register(r'accommodations', AccommodationViewSet)
router.register(r'reservations', ReservationViewSet)
router.register(r'ratings', RatingViewSet)
router.register(r'members', HKUMemberViewSet, basename='members')
router.register(r'specialists', CEDARSSpecialistViewSet)
router.register(r'campuses', HKUCampusViewSet)
router.register(r'photos', AccommodationPhotoViewSet)

urlpatterns = [
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    path('action-logs/', get_action_logs, name='get_action_logs'),
    path('', include(router.urls)),
]
