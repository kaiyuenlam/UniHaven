from django.contrib import admin
from .models import (
    Accommodation, AccommodationPhoto, HKUMember, CEDARSSpecialist,
    Reservation, Rating, Notification, HKUCampus, Owner
)

@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'address')
    search_fields = ('name', 'email')

@admin.register(HKUCampus)
class HKUCampusAdmin(admin.ModelAdmin):
    list_display = ('name', 'latitude', 'longitude')

@admin.register(Accommodation)
class AccommodationAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'num_bedrooms', 'num_beds', 'monthly_rent', 'is_available')
    list_filter = ('type', 'is_available', 'num_bedrooms')
    search_fields = ('name', 'building_name', 'address')

@admin.register(AccommodationPhoto)
class AccommodationPhotoAdmin(admin.ModelAdmin):
    list_display = ('accommodation', 'caption')

@admin.register(HKUMember)
class HKUMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone')
    search_fields = ('name', 'email')

@admin.register(CEDARSSpecialist)
class CEDARSSpecialistAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone')
    search_fields = ('name', 'email')

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('accommodation', 'member', 'reserved_from', 'reserved_to', 'status')
    list_filter = ('status',)
    search_fields = ('accommodation__name', 'member__name')

@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('accommodation', 'member', 'score', 'created_at')
    list_filter = ('score',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('specialist', 'type', 'is_read', 'created_at')
    list_filter = ('type', 'is_read')