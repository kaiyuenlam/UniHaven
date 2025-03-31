from rest_framework import serializers
from .models import (
    Accommodation, AccommodationPhoto, HKUMember, CEDARSSpecialist,
    Reservation, Rating, Notification, HKUCampus
)

class HKUCampusSerializer(serializers.ModelSerializer):
    class Meta:
        model = HKUCampus
        fields = '__all__'

class AccommodationPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccommodationPhoto
        fields = ['id', 'image', 'caption']

class AccommodationSerializer(serializers.ModelSerializer):
    photos = AccommodationPhotoSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = Accommodation
        fields = [
            'id', 'name', 'building_name', 'description', 'type',
            'num_bedrooms', 'num_beds', 'address', 'geo_address',
            'latitude', 'longitude', 'available_from', 'available_to',
            'monthly_rent', 'owner_name', 'owner_email', 'owner_phone',
            'is_available', 'photos', 'average_rating'
        ]

    def get_average_rating(self, obj):
        ratings = obj.ratings.all()
        if not ratings:
            return None
        return sum(rating.score for rating in ratings) / len(ratings)

class HKUMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = HKUMember
        fields = ['id', 'name', 'email', 'phone']

class CEDARSSpecialistSerializer(serializers.ModelSerializer):
    class Meta:
        model = CEDARSSpecialist
        fields = ['id', 'name', 'email', 'phone']

class ReservationSerializer(serializers.ModelSerializer):
    accommodation_name = serializers.ReadOnlyField(source='accommodation.name')
    member_name = serializers.ReadOnlyField(source='member.name')

    class Meta:
        model = Reservation
        fields = [
            'id', 'accommodation', 'accommodation_name', 'member', 'member_name',
            'reserved_from', 'reserved_to', 'status', 'created_at', 'updated_at'
        ]

class RatingSerializer(serializers.ModelSerializer):
    member_name = serializers.ReadOnlyField(source='member.name')

    class Meta:
        model = Rating
        fields = [
            'id', 'accommodation', 'member', 'member_name', 'reservation',
            'score', 'comment', 'created_at'
        ]

class NotificationSerializer(serializers.ModelSerializer):
    reservation_details = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'specialist', 'reservation', 'reservation_details',
            'type', 'is_read', 'created_at'
        ]

    def get_reservation_details(self, obj):
        return {
            'accommodation': obj.reservation.accommodation.name,
            'member': obj.reservation.member.name,
            'status': obj.reservation.status
        }