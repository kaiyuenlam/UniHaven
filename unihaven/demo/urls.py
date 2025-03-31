# urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.views import (
    AccommodationViewSet, ReservationViewSet, RatingViewSet,
    NotificationViewSet, HKUMemberViewSet, CEDARSSpecialistViewSet,
    HKUCampusViewSet,
    # 导入api_view函数
    search_accommodations, reserve_accommodation, get_location_data,
    cancel_reservation, rate_accommodation, mark_notification_read,
    get_member_reservations, get_specialist_notifications
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

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/accommodations/search/', search_accommodations, name='accommodation-search'),
    path('api/accommodations/<int:pk>/reserve/', reserve_accommodation, name='accommodation-reserve'),
    path('api/accommodations/location-data/', get_location_data, name='location-data'),
    path('api/reservations/<int:pk>/cancel/', cancel_reservation, name='reservation-cancel'),
    path('api/reservations/<int:pk>/rate/', rate_accommodation, name='reservation-rate'),
    path('api/notifications/<int:pk>/mark-read/', mark_notification_read, name='notification-mark-read'),
    path('api/members/<int:pk>/reservations/', get_member_reservations, name='member-reservations'),
    path('api/specialists/<int:pk>/notifications/', get_specialist_notifications, name='specialist-notifications'),
    path('api/', include(router.urls)),


]