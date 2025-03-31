from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import math

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
    """
    #### TODO: rating
    """
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

    # Owner contact
    owner_name = models.CharField(max_length=200)
    owner_email = models.EmailField()
    owner_phone = models.CharField(max_length=20)

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

    def __str__(self):
        return f"Photo of {self.accommodation.name}"

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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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