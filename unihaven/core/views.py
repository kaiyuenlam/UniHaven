# views.py
import math
import requests
from django.db.models import Q
from rest_framework import viewsets, status, filters
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination

from .models import (
    Accommodation, AccommodationPhoto, HKUMember, CEDARSSpecialist,
    Reservation, Rating, Notification, HKUCampus, Owner, ActionLog
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
    
class AccommodationPhotoViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AccommodationPhoto model, providing CRUD operations.
    """
    queryset = AccommodationPhoto.objects.all()
    serializer_class = AccommodationPhotoSerializer
    
    def get_queryset(self):
        queryset = AccommodationPhoto.objects.all()
        accommodation_id = self.request.query_params.get('accommodation')
        if accommodation_id:
            queryset = queryset.filter(accommodation__id=accommodation_id)
        return queryset

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
        
        Parameters:
        - building_name: Name of the building to look up
        
        Returns:
        - Dictionary with latitude, longitude, and geo_address if found
        - None if not found or error occurs
        """
        if not building_name or not isinstance(building_name, str) or len(building_name.strip()) == 0:
            return None
            
        params = {
            'q': building_name,
            'n': 1  # Return only the first result
        }

        # Add Accept header to request JSON format
        headers = {
            'Accept': 'application/json'
        }

        try:
            response = requests.get(AddressLookupService.BASE_URL, params=params, headers=headers, timeout=10)

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
            
            # Handle non-200 responses with appropriate error message
            error_message = "No address found" if response.status_code == 404 else f"Service error: {response.status_code}"
            return None
        except requests.RequestException as e:
            # Handle timeouts, connection errors, etc.
            return None

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
    Search for accommodations with filtering and sorting by distance to campus or price.
    
    Parameters:
    - type: Filter by accommodation type
    - available_from: Filter by availability start date
    - available_to: Filter by availability end date
    - num_beds: Filter by minimum number of beds
    - num_bedrooms: Filter by minimum number of bedrooms
    - min_price: Filter by minimum monthly rent
    - max_price: Filter by maximum monthly rent
    - campus_id: Sort by distance to this campus
    - sort_by: Sort by 'price_asc', 'price_desc', or 'distance' (default)
    
    Returns:
    - List of accommodations matching criteria, optionally with distance to campus
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
    sort_by = request.query_params.get('sort_by', 'distance')  # Default to distance if campus_id is provided

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

    # Sorting based on price if requested
    if sort_by == 'price_asc':
        queryset = queryset.order_by('monthly_rent')
        serializer = AccommodationSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    elif sort_by == 'price_desc':
        queryset = queryset.order_by('-monthly_rent')
        serializer = AccommodationSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    # If a campus is provided, calculate distances and sort by distance
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
                serializer = AccommodationSerializer(acc, context={'request': request})
                acc_data = serializer.data
                acc_data['distance'] = round(distance, 2)
                data.append(acc_data)
            return Response(data)
        except HKUCampus.DoesNotExist:
            return Response(
                {"error": "Campus not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    # If no sorting specified, return unsorted results
    serializer = AccommodationSerializer(queryset, many=True, context={'request': request})
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
        
    # Check for required fields
    required_fields = ['member_id', 'reserved_from', 'reserved_to', 'contact_name', 'contact_phone']
    for field in required_fields:
        if field not in request.data:
            return Response(
                {"error": f"Missing required field: {field}"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Validate dates
    from datetime import datetime
    try:
        reserved_from = datetime.strptime(request.data.get('reserved_from'), '%Y-%m-%d').date()
        reserved_to = datetime.strptime(request.data.get('reserved_to'), '%Y-%m-%d').date()
        
        # Check date logic
        today = timezone.now().date()
        if reserved_from < today:
            return Response(
                {"error": "Reservation cannot start in the past"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if reserved_from > reserved_to:
            return Response(
                {"error": "End date must be after start date"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if reserved_from < accommodation.available_from or reserved_to > accommodation.available_to:
            return Response(
                {"error": "Requested dates are outside the accommodation's availability period"},
                status=status.HTTP_400_BAD_REQUEST
            )
    except ValueError:
        return Response(
            {"error": "Invalid date format. Use YYYY-MM-DD"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Create a reservation
    serializer = ReservationSerializer(data={
        'accommodation': accommodation.id,
        'member': request.data.get('member_id'),
        'reserved_from': request.data.get('reserved_from'),
        'reserved_to': request.data.get('reserved_to'),
        'contact_name': request.data.get('contact_name'),
        'contact_phone': request.data.get('contact_phone'),
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
            
        # Log the action
        ActionLog.objects.create(
            action_type="CREATE_RESERVATION",
            user_type="MEMBER",
            user_id=reservation.member.id,
            accommodation_id=accommodation.id,
            reservation_id=reservation.id,
            details=f"Created reservation for '{accommodation.name}'"
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

@api_view(['POST'])
def update_reservation_status(request, pk):
    """
    Update the status of a reservation.
    
    Parameters:
    - pk: ID of the reservation to update
    - status: New status ('PENDING', 'CONFIRMED', 'CANCELLED', 'COMPLETED')
    
    Returns:
    - Updated reservation data
    """
    try:
        reservation = Reservation.objects.get(pk=pk)
    except Reservation.DoesNotExist:
        return Response(
            {"error": "Reservation not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    new_status = request.data.get('status')
    if not new_status or new_status not in [s[0] for s in Reservation.STATUS_CHOICES]:
        return Response(
            {"error": "Invalid status value"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    old_status = reservation.status
    reservation.status = new_status
    reservation.save()
    
    # Additional actions based on status change
    if new_status == 'CONFIRMED' and old_status == 'PENDING':
        # Notify the member that their reservation is confirmed
        pass
    elif new_status == 'COMPLETED' and old_status != 'COMPLETED':
        # Enable rating for the completed reservation
        pass
    elif new_status == 'CANCELLED' and old_status != 'CANCELLED':
        # Make the accommodation available again
        accommodation = reservation.accommodation
        accommodation.is_available = True
        accommodation.save()
        
        # Create notifications for CEDARS specialists
        for specialist in CEDARSSpecialist.objects.all():
            Notification.objects.create(
                specialist=specialist,
                reservation=reservation,
                type='CANCELLATION'
            )
    
    # Return the updated reservation
    serializer = ReservationSerializer(reservation)
    return Response(serializer.data)
    
@api_view(['POST'])
def upload_accommodation_photo(request, pk):
    """
    Upload a photo for an accommodation.
    """
    try:
        accommodation = Accommodation.objects.get(pk=pk)
    except Accommodation.DoesNotExist:
        return Response(
            {"error": "Accommodation not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if an image file is provided
    if 'image' not in request.FILES:
        return Response(
            {"error": "No image file provided"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create a photo
    serializer = AccommodationPhotoSerializer(data={
        'accommodation': accommodation.id,
        'image': request.FILES['image'],
        'caption': request.data.get('caption', ''),
        'is_primary': request.data.get('is_primary', False),
        'order': request.data.get('order', 0)
    })
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_accommodation_photos(request, pk):
    """
    Get all photos of an accommodation.
    """
    try:
        accommodation = Accommodation.objects.get(pk=pk)
    except Accommodation.DoesNotExist:
        return Response(
            {"error": "Accommodation not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    photos = AccommodationPhoto.objects.filter(accommodation=accommodation)
    serializer = AccommodationPhotoSerializer(photos, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['POST'])
def mark_accommodation_unavailable(request, pk):
    """
    Mark an accommodation as unavailable without deleting it.
    """
    try:
        accommodation = Accommodation.objects.get(pk=pk)
    except Accommodation.DoesNotExist:
        return Response(
            {"error": "Accommodation not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    accommodation.is_available = False
    accommodation.save()
    
    # Log the action - use specialist_id from request if provided
    specialist_id = request.data.get('specialist_id')
    if specialist_id:
        try:
            specialist = CEDARSSpecialist.objects.get(pk=specialist_id)
            ActionLog.objects.create(
                action_type="MARK_UNAVAILABLE",
                user_type="SPECIALIST",
                user_id=specialist.id,
                accommodation_id=accommodation.id,
                details=f"Marked accommodation '{accommodation.name}' as unavailable"
            )
        except CEDARSSpecialist.DoesNotExist:
            # Log without specialist information
            ActionLog.objects.create(
                action_type="MARK_UNAVAILABLE",
                accommodation_id=accommodation.id,
                details=f"Marked accommodation '{accommodation.name}' as unavailable"
            )
    else:
        # Log without specialist information
        ActionLog.objects.create(
            action_type="MARK_UNAVAILABLE",
            accommodation_id=accommodation.id,
            details=f"Marked accommodation '{accommodation.name}' as unavailable"
        )
    
    return Response({"status": "Accommodation marked as unavailable"})

@api_view(['DELETE'])
def delete_accommodation(request, pk):
    """
    Permanently delete an accommodation and all related data.
    Only CEDARS specialists should have permission to do this.
    """
    try:
        accommodation = Accommodation.objects.get(pk=pk)
    except Accommodation.DoesNotExist:
        return Response(
            {"error": "Accommodation not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if there are active reservations
    active_reservations = Reservation.objects.filter(
        accommodation=accommodation,
        status__in=['PENDING', 'CONFIRMED']
    ).exists()
    
    if active_reservations:
        return Response(
            {"error": "Cannot delete accommodation with active reservations"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Store the name for logging
    name = accommodation.name
    
    # Delete all photos first to clean up media files
    AccommodationPhoto.objects.filter(accommodation=accommodation).delete()
    
    # Delete the accommodation
    accommodation.delete()
    
    # Log the action - use specialist_id from request if provided
    specialist_id = request.data.get('specialist_id')
    if specialist_id:
        try:
            specialist = CEDARSSpecialist.objects.get(pk=specialist_id)
            ActionLog.objects.create(
                action_type="DELETE_ACCOMMODATION",
                user_type="SPECIALIST",
                user_id=specialist.id,
                details=f"Deleted accommodation '{name}'"
            )
        except CEDARSSpecialist.DoesNotExist:
            # Log without specialist information
            ActionLog.objects.create(
                action_type="DELETE_ACCOMMODATION",
                details=f"Deleted accommodation '{name}'"
            )
    else:
        # Log without specialist information
        ActionLog.objects.create(
            action_type="DELETE_ACCOMMODATION",
            details=f"Deleted accommodation '{name}'"
        )
    
    return Response(
        {"status": f"Accommodation '{name}' successfully deleted"},
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
def list_unavailable_accommodations(request):
    """
    List all unavailable accommodations for administrative purposes.
    """
    accommodations = Accommodation.objects.filter(is_available=False)
    serializer = AccommodationSerializer(accommodations, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['POST'])
def moderate_rating(request, pk):
    """
    Moderate a rating (approve or reject).
    """
    try:
        rating = Rating.objects.get(pk=pk)
    except Rating.DoesNotExist:
        return Response(
            {"error": "Rating not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Only CEDARS specialists can moderate ratings
    specialist_id = request.data.get('specialist_id')
    if not specialist_id:
        return Response(
            {"error": "Specialist ID is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        specialist = CEDARSSpecialist.objects.get(pk=specialist_id)
    except CEDARSSpecialist.DoesNotExist:
        return Response(
            {"error": "Specialist not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Update rating moderation status
    is_approved = request.data.get('is_approved', True)
    moderation_note = request.data.get('moderation_note', '')
    
    rating.is_approved = is_approved
    rating.moderated_by = specialist
    rating.moderation_date = timezone.now()
    rating.moderation_note = moderation_note
    rating.save()
    
    # Log the action
    ActionLog.objects.create(
        action_type="MODERATE_RATING",
        user_type="SPECIALIST",
        user_id=specialist.id,
        accommodation_id=rating.accommodation.id,
        rating_id=rating.id,
        details=f"Rating {'approved' if is_approved else 'rejected'}: {moderation_note}"
    )
    
    return Response({
        "status": f"Rating {'approved' if is_approved else 'rejected'}",
        "rating_id": rating.id
    })

@api_view(['GET'])
def get_pending_ratings(request):
    """
    Get ratings that need moderation (currently auto-approved but not explicitly moderated).
    """
    ratings = Rating.objects.filter(
        moderated_by__isnull=True
    ).order_by('created_at')
    
    serializer = RatingSerializer(ratings, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_action_logs(request):
    """
    Get a list of action logs for audit purposes.
    """
    # Parse filtering parameters
    action_type = request.query_params.get('action_type')
    user_type = request.query_params.get('user_type')
    user_id = request.query_params.get('user_id')
    accommodation_id = request.query_params.get('accommodation_id')
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    
    # Start with all logs
    logs = ActionLog.objects.all()
    
    # Apply filters
    if action_type:
        logs = logs.filter(action_type=action_type)
    if user_type:
        logs = logs.filter(user_type=user_type)
    if user_id:
        logs = logs.filter(user_id=user_id)
    if accommodation_id:
        logs = logs.filter(accommodation_id=accommodation_id)
    if start_date:
        logs = logs.filter(created_at__gte=start_date)
    if end_date:
        logs = logs.filter(created_at__lte=end_date)
    
    # Pagination
    paginator = PageNumberPagination()
    paginator.page_size = 20
    result_page = paginator.paginate_queryset(logs, request)

    class ActionLogSerializer(serializers.ModelSerializer):
        class Meta:
            model = ActionLog
            fields = '__all__'
    
    serializer = ActionLogSerializer(result_page, many=True)
    return paginator.get_paginated_response(serializer.data)