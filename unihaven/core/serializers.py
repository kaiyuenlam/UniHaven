from rest_framework import serializers
from django.utils import timezone
from .models import (
    Accommodation, AccommodationPhoto, HKUMember, CEDARSSpecialist,
    Reservation, Rating, Notification, HKUCampus, Owner
)

class OwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Owner
        fields = ['id', 'name', 'email', 'phone', 'address']

class HKUCampusSerializer(serializers.ModelSerializer):
    class Meta:
        model = HKUCampus
        fields = '__all__'

class AccommodationPhotoSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = AccommodationPhoto
        fields = ['id', 'accommodation', 'image', 'image_url', 'caption', 'is_primary', 'order', 'created_at']
        read_only_fields = ['image_url', 'created_at']
        
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                # Return full URL including domain
                return request.build_absolute_uri(obj.image.url)
            # Return relative URL if request context is not available
            return obj.image.url
        return None

class AccommodationSerializer(serializers.ModelSerializer):
    photos = AccommodationPhotoSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    owner_details = OwnerSerializer(source='owner', read_only=True)
    
    class Meta:
        model = Accommodation
        fields = [
            'id', 'name', 'building_name', 'description', 'type', 'type_display',
            'num_bedrooms', 'num_beds', 'address', 'geo_address',
            'latitude', 'longitude', 'available_from', 'available_to',
            'monthly_rent', 'owner', 'owner_details', 'is_available', 
            'photos', 'average_rating', 'rating_count'
        ]
        
    def get_average_rating(self, obj):
        ratings = obj.ratings.all()
        if not ratings:
            return None
        return round(sum(rating.score for rating in ratings) / len(ratings), 1)
        
    def get_rating_count(self, obj):
        return obj.ratings.count()

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
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    can_be_rated = serializers.SerializerMethodField()
    can_be_cancelled = serializers.SerializerMethodField()


    class Meta:
        model = Reservation
        fields = [
            'id', 'accommodation', 'accommodation_name', 'member', 'member_name',
            'reserved_from', 'reserved_to', 'status', 'status_display', 
            'can_be_rated', 'can_be_cancelled', 'created_at', 'updated_at'
        ]

    def get_can_be_rated(self, obj):
        return obj.can_be_rated()
        
    def get_can_be_cancelled(self, obj):
        return obj.can_be_cancelled()
    
    def validate(self, data):
        """
        Validate reservation dates and other constraints.
        """
        # Check that reserved_from is before reserved_to
        if data.get('reserved_from') and data.get('reserved_to'):
            if data['reserved_from'] > data['reserved_to']:
                raise serializers.ValidationError("End date must be after start date")
                
        # Check that reserved_from is not in the past for new reservations
        if self.instance is None and data.get('reserved_from'):
            if data['reserved_from'] < timezone.now().date():
                raise serializers.ValidationError("Reservation start date cannot be in the past")
                
        # Check that the accommodation is available for the requested dates
        if self.instance is None and data.get('accommodation'):
            accommodation = data['accommodation']
            if data.get('reserved_from') and data.get('reserved_to'):
                if data['reserved_from'] < accommodation.available_from or data['reserved_to'] > accommodation.available_to:
                    raise serializers.ValidationError(
                        "Requested dates are outside the accommodation's availability period"
                    )
        
        return data

class RatingSerializer(serializers.ModelSerializer):
    member_name = serializers.ReadOnlyField(source='member.name')

    class Meta:
        model = Rating
        fields = [
            'id', 'accommodation', 'member', 'member_name', 'reservation',
            'score', 'comment', 'created_at'
        ]

    def validate(self, data):
        """
        Check that the reservation is completed and hasn't been rated yet.
        """
        reservation = data.get('reservation')
        if reservation and not reservation.can_be_rated():
            if not reservation.status == 'COMPLETED':
                raise serializers.ValidationError("Can only rate completed reservations")
            else:
                raise serializers.ValidationError("This reservation has already been rated")
        return data

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
            'status': obj.reservation.status,
            'reserved_from': obj.reservation.reserved_from,
            'reserved_to': obj.reservation.reserved_to
        }
    