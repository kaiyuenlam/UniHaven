# urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.views import (
    AccommodationViewSet, ReservationViewSet, RatingViewSet,
    NotificationViewSet, HKUMemberViewSet, CEDARSSpecialistViewSet,
    HKUCampusViewSet, AccommodationPhotoViewSet,
    # 导入api_view函数
    search_accommodations, reserve_accommodation, get_location_data,
    cancel_reservation, rate_accommodation, mark_notification_read,
    get_member_reservations, get_specialist_notifications,

    # New Sprint 2 API endpoints
    update_reservation_status, upload_accommodation_photo, 
    get_accommodation_photos, mark_accommodation_unavailable,
    delete_accommodation,
    list_unavailable_accommodations, moderate_rating,
    get_pending_ratings, get_action_logs
)

# 设置路由器用于ViewSet
router = DefaultRouter()
router.register(r'accommodations', AccommodationViewSet)
router.register(r'reservations', ReservationViewSet)
router.register(r'ratings', RatingViewSet)
router.register(r'notifications', NotificationViewSet)
router.register(r'members', HKUMemberViewSet)
router.register(r'specialists', CEDARSSpecialistViewSet)
router.register(r'campuses', HKUCampusViewSet)
router.register(r'photos', AccommodationPhotoViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Sprint 1 API endpoints
    path('api/accommodations/search/', search_accommodations, name='accommodation-search'),
    path('api/accommodations/<int:pk>/reserve/', reserve_accommodation, name='accommodation-reserve'),
    path('api/accommodations/location-data/', get_location_data, name='location-data'),
    path('api/reservations/<int:pk>/cancel/', cancel_reservation, name='reservation-cancel'),
    path('api/reservations/<int:pk>/rate/', rate_accommodation, name='reservation-rate'),
    path('api/notifications/<int:pk>/mark-read/', mark_notification_read, name='notification-mark-read'),
    path('api/members/<int:pk>/reservations/', get_member_reservations, name='member-reservations'),
    path('api/specialists/<int:pk>/notifications/', get_specialist_notifications, name='specialist-notifications'),

    # New Sprint 2 API endpoints
    path('api/reservations/<int:pk>/update-status/', update_reservation_status, name='reservation-update-status'),
    path('api/accommodations/<int:pk>/photos/', get_accommodation_photos, name='accommodation-photos'),
    path('api/accommodations/<int:pk>/upload-photo/', upload_accommodation_photo, name='upload-accommodation-photo'),
    path('api/accommodations/<int:pk>/mark-unavailable/', mark_accommodation_unavailable, name='mark-accommodation-unavailable'),
    path('api/accommodations/<int:pk>/delete/', delete_accommodation, name='delete-accommodation'),
    path('api/accommodations/unavailable/', list_unavailable_accommodations, name='list-unavailable-accommodations'),
    path('api/ratings/<int:pk>/moderate/', moderate_rating, name='moderate-rating'),
    path('api/ratings/pending/', get_pending_ratings, name='pending-ratings'),
    path('api/logs/', get_action_logs, name='action-logs'),

    # Inculde the router URLs
    path('api/', include(router.urls)),


]