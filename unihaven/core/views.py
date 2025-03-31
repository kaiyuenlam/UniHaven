# views.py
import math
import requests
from django.db.models import Q
from rest_framework import viewsets, status, filters
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import (
    Accommodation, AccommodationPhoto, HKUMember, CEDARSSpecialist,
    Reservation, Rating, Notification, HKUCampus
)
from .serializers import (
    AccommodationSerializer, AccommodationPhotoSerializer, HKUMemberSerializer,
    CEDARSSpecialistSerializer, ReservationSerializer, RatingSerializer,
    NotificationSerializer, HKUCampusSerializer
)

# Using ViewSets to handle basic CRUD operations
class HKUCampusViewSet(viewsets.ModelViewSet):
    queryset = HKUCampus.objects.all()
    serializer_class = HKUCampusSerializer
class AccommodationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Accommodation model, providing CRUD operations.
    """
    queryset = Accommodation.objects.all()
    serializer_class = AccommodationSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'building_name', 'description', 'type', 'address']
    ordering_fields = ['monthly_rent', 'num_bedrooms', 'num_beds', 'available_from']

    def create(self, request, *args, **kwargs):
        # Check if building_name is provided but geographical location data is missing
        if (request.data.get('building_name') and
                not all([
                    request.data.get('latitude'),
                    request.data.get('longitude'),
                    request.data.get('geo_address')
                ])):

            try:
                # Use the new address lookup service
                building_name = request.data.get('building_name')
                location_data = AddressLookupService.lookup_address(building_name)

                if location_data:
                    # Copy request data for modification
                    request_data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)

                    # Add geographical location data
                    request_data['latitude'] = location_data.get('latitude')
                    request_data['longitude'] = location_data.get('longitude')
                    request_data['geo_address'] = location_data.get('geo_address')

                    # Create serializer and validate data
                    serializer = self.get_serializer(data=request_data)
                    serializer.is_valid(raise_exception=True)
                    self.perform_create(serializer)
                    headers = self.get_success_headers(serializer.data)
                    return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
                else:
                    # If no address is found, return an error message
                    return Response(
                        {"error": "No address found for this building name. Please enter location data manually."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except Exception as e:
                # If an exception occurs, return an error message
                return Response(
                    {"error": f"Failed to get location data: {str(e)}. Please enter location data manually."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # If all necessary data is provided or in other cases, call the default create method
        return super().create(request, *args, **kwargs)

class ReservationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Reservation model, providing CRUD operations.
    """
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer

class RatingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Rating model, providing read-only operations.
    """
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer

    def get_queryset(self):
        queryset = Rating.objects.all()
        accommodation_id = self.request.query_params.get('accommodation')
        if accommodation_id:
            queryset = queryset.filter(accommodation__id=accommodation_id)
        return queryset

class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Notification model, providing CRUD operations.
    """
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    def get_queryset(self):
        queryset = Notification.objects.all()
        specialist_id = self.request.query_params.get('specialist')
        if specialist_id:
            queryset = queryset.filter(specialist__id=specialist_id)
        return queryset

class HKUMemberViewSet(viewsets.ModelViewSet):
    """
    ViewSet for HKUMember model, providing CRUD operations.
    """
    queryset = HKUMember.objects.all()
    serializer_class = HKUMemberSerializer

class CEDARSSpecialistViewSet(viewsets.ModelViewSet):
    """
    ViewSet for CEDARSSpecialist model, providing CRUD operations.
    """
    queryset = CEDARSSpecialist.objects.all()
    serializer_class = CEDARSSpecialistSerializer

class AddressLookupService:
    BASE_URL = "https://www.als.ogcio.gov.hk/lookup"

    @staticmethod
    def lookup_address(building_name):
        """
        Query geographical coordinates based on building name (using JSON format).
        """
        params = {
            'q': building_name,
            'n': 1  # Return only the first result
        }

        # Add Accept header to request JSON format
        headers = {
            'Accept': 'application/json'
        }

        try:
            response = requests.get(AddressLookupService.BASE_URL, params=params, headers=headers)

            if response.status_code == 200:
                data = response.json()

                # Parse JSON response to get geographical location data
                if data.get('SuggestedAddress') and len(data['SuggestedAddress']) > 0:
                    address = data['SuggestedAddress'][0]
                    geo_info = address.get('Address', {}).get('PremisesAddress', {}).get('GeospatialInformation', {})
                    geo_address = address.get('Address', {}).get('PremisesAddress', {}).get('GeoAddress', '')

                    if geo_info.get('Latitude') and geo_info.get('Longitude'):
                        return {
                            'latitude': geo_info.get('Latitude'),
                            'longitude': geo_info.get('Longitude'),
                            'geo_address': geo_address
                        }

                return Response({
                    "error": "No suggested address found for the provided building name."
                }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "error": f"An error occurred while fetching address details: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return None

    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """
        Calculate the approximate distance between two points using equirectangular projection (unit: kilometers).
        """
        import math

        R = 6371  # Earth's radius in kilometers
        lat1_rad = math.radians(float(lat1))
        lon1_rad = math.radians(float(lon1))
        lat2_rad = math.radians(float(lat2))
        lon2_rad = math.radians(float(lon2))

        x = (lon2_rad - lon1_rad) * math.cos((lat1_rad + lat2_rad) / 2)
        y = lat2_rad - lat1_rad
        d = math.sqrt(x * x + y * y) * R
        return d

# Using api_view decorator instead of @action method
@api_view(['GET'])
def search_accommodations(request):
    """
    Search for accommodations with filtering and sorting by distance to campus.
    """
    # Get filter parameters
    accommodation_type = request.query_params.get('type')
    available_from = request.query_params.get('available_from')
    available_to = request.query_params.get('available_to')
    num_beds = request.query_params.get('num_beds')
    num_bedrooms = request.query_params.get('num_bedrooms')
    min_price = request.query_params.get('min_price')
    max_price = request.query_params.get('max_price')
    campus_id = request.query_params.get('campus_id')

    # Start querying all available accommodations
    queryset = Accommodation.objects.filter(is_available=True)

    # Apply filters
    if accommodation_type:
        queryset = queryset.filter(type=accommodation_type)
    if available_from:
        queryset = queryset.filter(available_from__lte=available_from)
    if available_to:
        queryset = queryset.filter(available_to__gte=available_to)
    if num_beds:
        queryset = queryset.filter(num_beds__gte=num_beds)
    if num_bedrooms:
        queryset = queryset.filter(num_bedrooms__gte=num_bedrooms)
    if min_price:
        queryset = queryset.filter(monthly_rent__gte=min_price)
    if max_price:
        queryset = queryset.filter(monthly_rent__lte=max_price)

    # If a campus is provided, calculate distances and sort

    """
    TODO: sort by price
    """
    if campus_id:
        try:
            campus = HKUCampus.objects.get(id=campus_id)
            # Get all accommodations with distances
            accommodations_with_distances = [
                (accommodation, accommodation.calculate_distance(campus))
                for accommodation in queryset
            ]
            # Sort by distance
            accommodations_with_distances.sort(key=lambda x: x[1])
            # Get sorted accommodations
            data = []
            for acc, distance in accommodations_with_distances:
                serializer = AccommodationSerializer(acc)
                acc_data = serializer.data
                acc_data['distance'] = round(distance, 2)
                data.append(acc_data)
            return Response(data)
        except HKUCampus.DoesNotExist:
            return Response(
                {"error": "Campus not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    # If no campus is provided, return unsorted results
    serializer= AccommodationSerializer(queryset, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def reserve_accommodation(request, pk):
    """
    Reserve an accommodation.
    """
    try:
        accommodation = Accommodation.objects.get(pk=pk)
    except Accommodation.DoesNotExist:
        return Response(
            {"error": "Accommodation not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    if not accommodation.is_available:
        return Response(
            {"error": "This accommodation is not available for reservation"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Create a reservation
    serializer = ReservationSerializer(data={
        'accommodation': accommodation.id,
        'member': request.data.get('member_id'),
        'reserved_from': request.data.get('reserved_from'),
        'reserved_to': request.data.get('reserved_to'),
        'status': 'PENDING'
    })

    if serializer.is_valid():
        reservation = serializer.save()

        # Mark the accommodation as unavailable
        accommodation.is_available = False
        accommodation.save()

        # Create notifications for CEDARS specialists
        for specialist in CEDARSSpecialist.objects.all():
            Notification.objects.create(
                specialist=specialist,
                reservation=reservation,
                type='RESERVATION'
            )

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def get_location_data(request):
    """
    Query DATA.GOV.HK address lookup service to get latitude, longitude, and geo address.
    """
    building_name = request.data.get('building_name')
    if not building_name:
        return Response(
            {"error": "Building name is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    result = AddressLookupService.lookup_address(building_name)

    if result:
        return Response(result)
    else:
        return Response(
            {"error": "No address found for this building name or service unavailable"},
            status=status.HTTP_404_NOT_FOUND
        )

# @api_view(['POST'])
# def cancel_reservation(request, pk):
#     """
#     Cancel a reservation.
#     """
#     try:
#         reservation = Reservation.objects.get(pk=pk)
#     except Reservation.DoesNotExist:
#         return Response(
#             {"error": "Reservation not found"},
#             status=status.HTTP_404_NOT_FOUND
#         )
#
#     # Check if the reservation can be canceled (not in contract stage)
#     if reservation.status == 'CONFIRMED':
#         return Response(
#             {"error": "Cannot cancel a confirmed reservation"},
#             status(status.HTTP_400_BAD_REQUEST))
#
#         # Update reservation status
#         reservation.status = 'CANCELLED'
#         reservation.save()
#
#         # Make the accommodation available again
#         accommodation = reservation.accommodation
#         accommodation.is_available = True
#         accommodation.save()
#
#         # Create notifications for CEDARS specialists
#         for specialist in CEDARSSpecialist.objects.all():
#             Notification.objects.create(
#                 specialist=specialist,
#                 reservation=reservation,
#                 type='CANCELLATION'
#             )
#
#     return Response({"status": "Reservation cancelled successfully"})
@api_view(['POST'])
def cancel_reservation(request, pk):
    """取消预订"""
    try:
        reservation = Reservation.objects.get(pk=pk)
    except Reservation.DoesNotExist:
        return Response(
            {"error": "Reservation not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # 检查预订是否可以取消（未处于合同阶段）
    if reservation.status == 'CONFIRMED':
        return Response(
            {"error": "Cannot cancel a confirmed reservation"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 更新预订状态
    old_status = reservation.status
    reservation.status = 'CANCELLED'
    reservation.save()

    # 使住宿再次可用
    accommodation = reservation.accommodation
    old_availability = accommodation.is_available
    accommodation.is_available = True
    accommodation.save()

    # # 添加这行代码确认更改已保存到数据库
    # updated_reservation = Reservation.objects.get(pk=pk)
    # updated_accommodation = Accommodation.objects.get(pk=accommodation.id)
    # print(f"检查更新: 预订状态={updated_reservation.status}, 住宿可用性={updated_accommodation.is_available}")

    # 为CEDARS专家创建通知
    notification_count = 0
    for specialist in CEDARSSpecialist.objects.all():
        notification = Notification.objects.create(
            specialist=specialist,
            reservation=reservation,
            type='CANCELLATION'
        )
        notification_count += 1
    # print(f"已创建 {notification_count} 条取消通知")

    return Response({"status": "Reservation cancelled successfully"})
@api_view(['POST'])
def rate_accommodation(request, pk):
    """
    Rate an accommodation.
    """
    try:
        reservation = Reservation.objects.get(pk=pk)
    except Reservation.DoesNotExist:
        return Response(
            {"error": "Reservation not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # Check if the reservation is completed
    if reservation.status != 'COMPLETED':
        return Response(
            {"error": "Can only rate completed reservations"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if it has already been rated
    if Rating.objects.filter(reservation=reservation).exists():
        return Response(
            {"error": "This reservation has already been rated"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Create a rating
    serializer = RatingSerializer(data={
        'accommodation': reservation.accommodation.id,
        'member': reservation.member.id,
        'reservation': reservation.id,
        'score': request.data.get('score'),
        'comment': request.data.get('comment', '')
    })

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def mark_notification_read(request, pk):
    """
    Mark a notification as read.
    """
    try:
        notification = Notification.objects.get(pk=pk)
    except Notification.DoesNotExist:
        return Response(
            {"error": "Notification not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    notification.is_read = True
    notification.save()
    return Response({"status": "Notification marked as read"})

@api_view(['GET'])
def get_member_reservations(request, pk):
    """
    Get all reservations of a member.
    """
    try:
        member = HKUMember.objects.get(pk=pk)
    except HKUMember.DoesNotExist:
        return Response(
            {"error": "Member not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    reservations = Reservation.objects.filter(member=member)
    serializer = ReservationSerializer(reservations, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_specialist_notifications(request, pk):
    """
    Get all notifications of a specialist.
    """
    try:
        specialist = CEDARSSpecialist.objects.get(pk=pk)
    except CEDARSSpecialist.DoesNotExist:
        return Response(
            {"error": "Specialist not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    notifications = Notification.objects.filter(specialist=specialist)
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)