from rest_framework import serializers
from django.utils import timezone
from .models import (
    Accommodation, AccommodationPhoto, HKUMember, CEDARSSpecialist,
    Reservation, Rating, HKUCampus, Owner, ActionLog
)

# -------------------- Owner --------------------
class OwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Owner
        fields = ['name', 'email', 'phone', 'address']

# -------------------- HKUCampus --------------------
class HKUCampusSerializer(serializers.ModelSerializer):
    class Meta:
        model = HKUCampus
        fields = '__all__'

# -------------------- AccommodationPhoto --------------------
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

# -------------------- Accommodation --------------------
class AccommodationSerializer(serializers.ModelSerializer):
    photos = AccommodationPhotoSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    owner_details = OwnerSerializer(write_only=True)
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = Accommodation
        fields = [
            'id', 'name', 'building_name', 'description', 'type', 'type_display',
            'num_bedrooms', 'num_beds', 'address', 'geo_address',
            'latitude', 'longitude', 'available_from', 'available_to',
            'monthly_rent', 'owner', 'owner_details', 'is_available', 
            'photos', 'average_rating', 'rating_count'
        ]

    def create(self, validated_data):
        owner_data = validated_data.pop('owner_details', None)
        if owner_data:
            owner = Owner.objects.create(**owner_data)
            validated_data['owner'] = owner
        return super().create(validated_data)
        
    def get_average_rating(self, obj):
        ratings = obj.ratings.all()
        if ratings.exists():
            try:
                avg = sum(rating.score for rating in ratings) / ratings.count()
                return round(avg, 1)
            except Exception as e:
                return None
        return None
        
    def get_rating_count(self, obj):
        return obj.ratings.count()

# -------------------- HKUMember --------------------
class HKUMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = HKUMember
        fields = ['id', 'name', 'email', 'phone']

# -------------------- CEDARSSpecialist --------------------
class CEDARSSpecialistSerializer(serializers.ModelSerializer):
    class Meta:
        model = CEDARSSpecialist
        fields = ['id', 'name', 'email', 'phone']

# -------------------- Reservation --------------------
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
        Validate reservation dates and availability.
        """
        reserved_from = data.get('reserved_from')
        reserved_to = data.get('reserved_to')
        # Check that reserved_from is before reserved_to
        if reserved_from and reserved_to:
            if reserved_from > reserved_to:
                raise serializers.ValidationError("End date must be after start date")
                
        # Check that reserved_from is not in the past for new reservations
        if self.instance is None and reserved_from:
            if reserved_from < timezone.now().date():
                raise serializers.ValidationError("Reservation start date cannot be in the past")
                
        # Check that the accommodation is available for the requested dates
        accommodation = data.get('accommodation')
        if accommodation and reserved_from and reserved_to:
            accommodation = data['accommodation']
            if data.get('reserved_from') and data.get('reserved_to'):
                if reserved_from < accommodation.available_from or reserved_to > accommodation.available_to:
                    raise serializers.ValidationError(
                        "Requested dates are outside the accommodation's availability period"
                    )
        return data

# -------------------- Rating --------------------
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
        if reservation:
            if reservation.status != 'COMPLETED':
                raise serializers.ValidationError("Can only rate completed reservations")

            if not reservation.can_be_rated():
                raise serializers.ValidationError("This reservation has already been rated")
        else:
            raise serializers.ValidationError("Reservation is required for rating.")
        return data

# -------------------- ActionLog --------------------
class ActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionLog
        fields = '__all__'