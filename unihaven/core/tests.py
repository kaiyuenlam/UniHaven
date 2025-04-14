from django.test import TestCase
import datetime
import math
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from unittest.mock import patch
from faker import Faker

from .models import (
    Owner, HKUCampus, Accommodation, AccommodationPhoto, HKUMember,
    CEDARSSpecialist, Reservation, Rating, ActionLog
)
from .serializers import AccommodationSerializer, ReservationSerializer, RatingSerializer

# Helper for generating dates
def days_from_today(n):
    return timezone.now().date() + datetime.timedelta(days=n)

class BaseTest(APITestCase):
    """
    BaseTest creates some common objects used across multiple test cases.
    """
    def setUp(self):
        # Create an Owner
        self.owner = Owner.objects.create(
            name="Test Owner", email="owner@example.com",
            phone="1234567890", address="123 Test Lane"
        )
        # Create an HKUCampus
        self.campus = HKUCampus.objects.create(
            name="Main Campus", latitude=22.3964, longitude=114.1095
        )
        # Create an Accommodation available from today+5 to today+30
        self.accommodation = Accommodation.objects.create(
            name="Test Apt",
            building_name="Test Building",
            description="A test apartment",
            type="APARTMENT",
            num_bedrooms=2,
            num_beds=3,
            address="123 Test Lane",
            geo_address="TEST-GEO-ADDR-123456789",  # Ensure length <=19
            latitude=22.3964,
            longitude=114.1095,
            available_from=days_from_today(5),
            available_to=days_from_today(30),
            monthly_rent=1500.00,
            owner=self.owner,
            is_available=True
        )
        # Create a HKUMember
        self.member = HKUMember.objects.create(
            name="Test Member", email="member@example.com", phone="0987654321"
        )
        # Create a CEDARSSpecialist
        self.specialist = CEDARSSpecialist.objects.create(
            name="Test Specialist", email="specialist@example.com", phone="1122334455"
        )
        # Set up the APIClient
        self.client = APIClient()

### --- Tests for Accommodation Endpoints ---
class AccommodationAPITest(BaseTest):
    def test_create_accommodation_with_address_lookup(self):
        """
        Test that creating an accommodation without geographical location data causes
        the view to use the AddressLookupService (which we will mock) and return a valid response.
        Note: owner data is provided as nested 'owner_details'.
        """
        url = reverse('accommodation-list')
        payload = {
            "name": "Lookup Apt",
            "building_name": "Lookup Building",
            "description": "Testing location lookup",
            "type": "APARTMENT",
            "num_bedrooms": 1,
            "num_beds": 2,
            "address": "456 Lookup Street",
            # No latitude, longitude, or geo_address provided so that lookup is triggered
            "available_from": str(days_from_today(7)),
            "available_to": str(days_from_today(40)),
            "monthly_rent": "1200.00",
            "owner_details": {   # Nested owner data
                "name": "Test Owner",
                "email": "owner@example.com",
                "phone": "1234567890",
                "address": "123 Test Lane"
            },
            "is_available": True
        }
        # Patch the lookup_address method to simulate a valid lookup.
        # Use a geo_address value that is less than or equal to 19 characters.
        with patch('core.utils.AddressLookupService.lookup_address') as mock_lookup:
            mock_lookup.return_value = {
                "latitude": 22.3000,
                "longitude": 114.1000,
                "geo_address": "MOCK-ADDR-12345"  # 15 characters
            }
            response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(float(response.data.get('latitude')), 22.3000)
        self.assertEqual(response.data.get('geo_address'), "MOCK-ADDR-12345")

    def test_search_accommodations_by_type(self):
        """
        Test the search action filtering by accommodation type.
        """
        url = reverse('accommodation-search')
        # Create another accommodation of type 'HOUSE'
        Accommodation.objects.create(
            name="House Apt",
            building_name="House Building",
            description="A test house",
            type="HOUSE",
            num_bedrooms=3,
            num_beds=4,
            address="789 House Rd",
            geo_address="HOUSE-GEO-ADDR",  # Ensure within length
            latitude=22.4000,
            longitude=114.2000,
            available_from=days_from_today(1),
            available_to=days_from_today(90),
            monthly_rent=2000.00,
            owner=self.owner,
            is_available=True
        )
        response = self.client.get(url, {'type': 'HOUSE'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check that only one accommodation of type HOUSE is returned
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['type'], 'HOUSE')

    def test_reserve_accommodation(self):
        """
        Test the reserve custom action on an accommodation.
        It should create a reservation and mark the accommodation as unavailable.
        """
        url = reverse('accommodation-reserve', kwargs={'pk': self.accommodation.id})
        payload = {
            "member_id": self.member.id,
            "reserved_from": str(days_from_today(6)),
            "reserved_to": str(days_from_today(10)),
            "contact_name": "John Doe",
            "contact_phone": "1231231234"
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Refresh accommodation from DB and check availability
        self.accommodation.refresh_from_db()
        self.assertFalse(self.accommodation.is_available)
        # Verify that a reservation is created with status 'PENDING'
        self.assertEqual(response.data['status'], 'PENDING')


### --- Tests for Reservation Endpoints ---
class ReservationAPITest(BaseTest):
    def setUp(self):
        super().setUp()
        # Create a reservation in PENDING state for testing cancellation and update
        self.reservation = Reservation.objects.create(
            accommodation=self.accommodation,
            member=self.member,
            reserved_from=days_from_today(6),
            reserved_to=days_from_today(10),
            contact_name="John Doe",
            contact_phone="1231231234",
            status="PENDING"
        )
        # Mark the accommodation unavailable to reflect reservation state
        self.accommodation.is_available = False
        self.accommodation.save()

    def test_cancel_reservation(self):
        """
        Test that canceling a reservation changes its status to CANCELLED and makes the accommodation available.
        """
        url = reverse('reservation-cancel', kwargs={'pk': self.reservation.id})
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, 'CANCELLED')
        self.accommodation.refresh_from_db()
        self.assertTrue(self.accommodation.is_available)

    def test_update_reservation_status(self):
        """
        Test updating reservation status.
        """
        url = reverse('reservation-update-status', kwargs={'pk': self.reservation.id})
        payload = {"status": "CONFIRMED"}
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, "CONFIRMED")


### --- Tests for Rating Endpoints ---
class RatingAPITest(BaseTest):
    def setUp(self):
        super().setUp()
        # Create a reservation that is completed so that rating is allowed.
        self.reservation = Reservation.objects.create(
            accommodation=self.accommodation,
            member=self.member,
            reserved_from=days_from_today(6),
            reserved_to=days_from_today(10),
            contact_name="John Doe",
            contact_phone="1231231234",
            status="COMPLETED"
        )
        # Create an initial rating (later we will test moderation)
        self.rating = Rating.objects.create(
            accommodation=self.accommodation,
            member=self.member,
            reservation=self.reservation,
            score=4,
            comment="Good stay."
        )

    def test_moderate_rating(self):
        """
        Test moderating a rating via the custom action.
        """
        url = reverse('rating-moderate', kwargs={'pk': self.rating.id})
        payload = {
            "specialist_id": self.specialist.id,
            "is_approved": False,
            "moderation_note": "Inappropriate language."
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.rating.refresh_from_db()
        self.assertFalse(self.rating.is_approved)
        self.assertEqual(self.rating.moderated_by.id, self.specialist.id)
        self.assertIsNotNone(self.rating.moderation_date)

    def test_pending_ratings(self):
        """
        Test retrieving pending ratings (those not yet moderated).
        """
        # Create a new completed reservation and a new rating that hasn't been moderated.
        new_reservation = Reservation.objects.create(
            accommodation=self.accommodation,
            member=self.member,
            reserved_from=days_from_today(11),
            reserved_to=days_from_today(15),
            contact_name="Jane Doe",
            contact_phone="5555555555",
            status="COMPLETED"
        )
        Rating.objects.create(
            accommodation=self.accommodation,
            member=self.member,
            reservation=new_reservation,
            score=5,
            comment="Excellent!"
        )
        url = reverse('rating-pending')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The response may be paginated or a plain list. Check accordingly:
        data = response.data.get('results') if isinstance(response.data, dict) else response.data
        self.assertGreaterEqual(len(data), 1)


### --- Tests for HKUMember Custom Reservations Action ---
class MemberReservationsAPITest(BaseTest):
    def test_get_member_reservations(self):
        """
        Test that the custom 'reservations' action on HKUMemberViewSet returns all reservations for a member.
        """
        # Create two reservations for this member.
        Reservation.objects.create(
            accommodation=self.accommodation,
            member=self.member,
            reserved_from=days_from_today(6),
            reserved_to=days_from_today(10),
            contact_name="John Doe",
            contact_phone="1231231234",
            status="PENDING"
        )
        Reservation.objects.create(
            accommodation=self.accommodation,
            member=self.member,
            reserved_from=days_from_today(11),
            reserved_to=days_from_today(15),
            contact_name="Jane Doe",
            contact_phone="5555555555",
            status="CONFIRMED"
        )
        # The custom action on HKUMemberViewSet should be registered under the router name 'members-reservations'
        url = reverse('members-reservations', kwargs={'pk': self.member.id})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for res in response.data:
            self.assertEqual(res['member'], self.member.id)


### --- Tests for Action Logs Endpoint ---
class ActionLogsAPITest(BaseTest):
    def setUp(self):
        super().setUp()
        # Create a sample ActionLog entry.
        ActionLog.objects.create(
            action_type="TEST_ACTION",
            user_type="MEMBER",
            user_id=self.member.id,
            accommodation_id=self.accommodation.id,
            details="Test log entry"
        )

    def test_get_action_logs(self):
        """
        Test the get_action_logs view returns paginated logs.
        """
        url = reverse('get_action_logs')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify that logs are returned, handling both paginated and unpaginated responses.
        if isinstance(response.data, dict) and 'results' in response.data:
            results = response.data['results']
        else:
            results = response.data
        self.assertGreaterEqual(len(results), 1)
