# App-Level URL Conf
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.views import (
    AccommodationViewSet, ReservationViewSet, RatingViewSet,
    HKUMemberViewSet, CEDARSSpecialistViewSet,
    HKUCampusViewSet, AccommodationPhotoViewSet,
    search_accommodations, reserve_accommodation, get_location_data,
    cancel_reservation, rate_accommodation,
    get_member_reservations,
    # Sprint 2 endpoints:
    update_reservation_status, upload_accommodation_photo, 
    get_accommodation_photos, mark_accommodation_unavailable,
    delete_accommodation,
    list_unavailable_accommodations, moderate_rating,
    get_pending_ratings, get_action_logs
)

# Create a default router and register viewsets:
router = DefaultRouter()
router.register(r'accommodations', AccommodationViewSet)
router.register(r'reservations', ReservationViewSet)
router.register(r'ratings', RatingViewSet)
#router.register(r'notifications', NotificationViewSet)
router.register(r'members', HKUMemberViewSet)
router.register(r'specialists', CEDARSSpecialistViewSet)
router.register(r'campuses', HKUCampusViewSet)
router.register(r'photos', AccommodationPhotoViewSet)

urlpatterns = [
    # Sprint 1 API endpoints:
    path('accommodations/search/', search_accommodations, name='accommodation-search'),
    path('accommodations/<int:pk>/reserve/', reserve_accommodation, name='accommodation-reserve'),
    path('accommodations/location-data/', get_location_data, name='location-data'),
    path('reservations/<int:pk>/cancel/', cancel_reservation, name='reservation-cancel'),
    path('reservations/<int:pk>/rate/', rate_accommodation, name='reservation-rate'),
    #path('notifications/<int:pk>/mark-read/', mark_notification_read, name='notification-mark-read'),
    path('members/<int:pk>/reservations/', get_member_reservations, name='member-reservations'),
    #path('specialists/<int:pk>/notifications/', get_specialist_notifications, name='specialist-notifications'),
    
    # Sprint 2 API endpoints:
    path('reservations/<int:pk>/update-status/', update_reservation_status, name='reservation-update-status'),
    path('accommodations/<int:pk>/photos/', get_accommodation_photos, name='accommodation-photos'),
    path('accommodations/<int:pk>/upload-photo/', upload_accommodation_photo, name='upload-accommodation-photo'),
    path('accommodations/<int:pk>/mark-unavailable/', mark_accommodation_unavailable, name='mark-accommodation-unavailable'),
    path('accommodations/<int:pk>/delete/', delete_accommodation, name='delete-accommodation'),
    path('accommodations/unavailable/', list_unavailable_accommodations, name='list-unavailable-accommodations'),
    path('ratings/<int:pk>/moderate/', moderate_rating, name='moderate-rating'),
    path('ratings/pending/', get_pending_ratings, name='pending-ratings'),
    path('logs/', get_action_logs, name='action-logs'),
    
    # Include viewset-generated endpoints from the router:
    path('', include(router.urls)),
]
