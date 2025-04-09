from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import math

class Owner(models.Model):
    """Property owner who offers accommodations for rent"""
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    
    # Authentication information could be added here if owners need login access
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class HKUCampus(models.Model):
    """Campus or premises of HKU for distance calculation"""
    name = models.CharField(max_length=200)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return self.name

class Accommodation(models.Model):
    """Accommodation that can be rented by HKU members"""
    # Basic info
    name = models.CharField(max_length=200)
    building_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Type and size
    TYPE_CHOICES = [
        ('APARTMENT', 'Apartment'),
        ('HOUSE', 'House'),
        ('SHARED', 'Shared Room'),
        ('STUDIO', 'Studio'),
    ]
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    num_bedrooms = models.PositiveIntegerField()
    num_beds = models.PositiveIntegerField()

    # Location data
    address = models.TextField()
    geo_address = models.CharField(max_length=19)  # The 19-character standardized identifier
    latitude = models.FloatField()
    longitude = models.FloatField()

    # Availability and cost
    available_from = models.DateField()
    available_to = models.DateField()
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2)

    # Owner relation (replace owner_name, owner_email, owner_phone fields)
    owner = models.ForeignKey(Owner, related_name='accommodations', on_delete=models.CASCADE)

    # Status tracking
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Photos can be added as a separate model with ForeignKey

    def calculate_distance(self, campus):
        """Calculate distance to campus in kilometers using equirectangular projection"""
        # Earth radius in kilometers
        R = 6371.0

        # Convert latitude and longitude from degrees to radians
        lat1 = math.radians(self.latitude)
        lon1 = math.radians(self.longitude)
        lat2 = math.radians(campus.latitude)
        lon2 = math.radians(campus.longitude)

        # Equirectangular approximation
        x = (lon2 - lon1) * math.cos((lat1 + lat2) / 2)
        y = (lat2 - lat1)
        d = R * math.sqrt(x*x + y*y)

        return d
    
    def average_rating(self):
        """Calculate the average rating for this accommodation"""
        ratings = self.ratings.all()
        if not ratings:
            return None
        return sum(rating.score for rating in ratings) / len(ratings)
        
    def rating_count(self):
        """Get the number of ratings for this accommodation"""
        return self.ratings.count()

    def __str__(self):
        return self.name
"""
Do we need this?
"""
class AccommodationPhoto(models.Model):
    """Photos of accommodations"""
    accommodation = models.ForeignKey(Accommodation, related_name='photos', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='accommodation_photos/')
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo of {self.accommodation.name}"
        
    class Meta:
        ordering = ['order', 'created_at']
        
    def save(self, *args, **kwargs):
        # Ensure only one primary photo per accommodation
        if self.is_primary:
            self.__class__.objects.filter(
                accommodation=self.accommodation, 
                is_primary=True
            ).exclude(id=self.id).update(is_primary=False)
        super().save(*args, **kwargs)

class HKUMember(models.Model):
    """Member of HKU who can search and reserve accommodations"""
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.name

class CEDARSSpecialist(models.Model):
    """CEDARS accommodation specialist who manages the system"""
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)

    def __str__(self):
        return self.name

class Reservation(models.Model):
    """Reservation of accommodation by an HKU member"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
    ]

    accommodation = models.ForeignKey(Accommodation, on_delete=models.CASCADE)
    member = models.ForeignKey(HKUMember, on_delete=models.CASCADE)
    reserved_from = models.DateField()
    reserved_to = models.DateField()
    
    # New contact fields
    contact_name = models.CharField(max_length=200)
    contact_phone = models.CharField(max_length=20)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def can_be_rated(self):
        """Check if this reservation can be rated"""
        return self.status == 'COMPLETED' and not hasattr(self, 'rating')
        
    def can_be_cancelled(self):
        """Check if this reservation can be cancelled"""
        return self.status == 'PENDING'
        
    def cancel(self):
        """Cancel this reservation and handle side effects"""
        if self.can_be_cancelled():
            self.status = 'CANCELLED'
            self.save()
            
            # Make accommodation available again
            self.accommodation.is_available = True
            self.accommodation.save()
            
            # Create notifications
            from .models import CEDARSSpecialist, Notification
            for specialist in CEDARSSpecialist.objects.all():
                Notification.objects.create(
                    specialist=specialist,
                    reservation=self,
                    type='CANCELLATION'
                )
            return True
        return False

    def __str__(self):
        return f"{self.member.name}'s reservation of {self.accommodation.name}"
    
class Rating(models.Model):
    """Rating given by an HKU member for an accommodation after stay"""
    accommodation = models.ForeignKey(Accommodation, related_name='ratings', on_delete=models.CASCADE)
    member = models.ForeignKey(HKUMember, on_delete=models.CASCADE)
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE)
    score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Moderation fields
    is_approved = models.BooleanField(default=True)  # Auto-approve by default
    moderated_by = models.ForeignKey(CEDARSSpecialist, null=True, blank=True, on_delete=models.SET_NULL)
    moderation_date = models.DateTimeField(null=True, blank=True)
    moderation_note = models.TextField(blank=True)

    class Meta:
        unique_together = ('accommodation', 'member', 'reservation')

    def __str__(self):
        return f"{self.member.name}'s {self.score}-star rating for {self.accommodation.name}"

class Notification(models.Model):
    """Notifications for CEDARS specialists"""
    TYPE_CHOICES = [
        ('RESERVATION', 'New Reservation'),
        ('CANCELLATION', 'Reservation Cancelled'),
    ]

    specialist = models.ForeignKey(CEDARSSpecialist, on_delete=models.CASCADE)
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} notification for {self.specialist.name}"

class ActionLog(models.Model):
    """Log of actions performed in the system for audit purposes"""
    ACTION_TYPES = [
        ('CREATE_ACCOMMODATION', 'Create Accommodation'),
        ('UPDATE_ACCOMMODATION', 'Update Accommodation'),
        ('DELETE_ACCOMMODATION', 'Delete Accommodation'),
        ('MARK_UNAVAILABLE', 'Mark Unavailable'),
        ('CREATE_RESERVATION', 'Create Reservation'),
        ('UPDATE_RESERVATION', 'Update Reservation'),
        ('CANCEL_RESERVATION', 'Cancel Reservation'),
        ('CREATE_RATING', 'Create Rating'),
        ('MODERATE_RATING', 'Moderate Rating'),
        ('UPLOAD_PHOTO', 'Upload Photo'),
        ('DELETE_PHOTO', 'Delete Photo'),
    ]
    
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    user_type = models.CharField(max_length=20, default='SPECIALIST')  # SPECIALIST, MEMBER, SYSTEM
    user_id = models.PositiveIntegerField(null=True, blank=True)  # ID of the user who performed the action
    accommodation_id = models.PositiveIntegerField(null=True, blank=True)  # ID of relevant accommodation
    reservation_id = models.PositiveIntegerField(null=True, blank=True)  # ID of relevant reservation
    rating_id = models.PositiveIntegerField(null=True, blank=True)  # ID of relevant rating
    details = models.TextField(blank=True)  # Additional details about the action
    ip_address = models.GenericIPAddressField(null=True, blank=True)  # IP address of the user
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.action_type} at {self.created_at}"
