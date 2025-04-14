 # core/utils.py
import logging
import math
import requests

logger = logging.getLogger(__name__)

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
        - None if not found or an error occurs
        """
        if not building_name or not isinstance(building_name, str) or len(building_name.strip()) == 0:
            return None

        params = {
            'q': building_name,
            'n': 1  # Return only the first result
        }

        headers = {
            'Accept': 'application/json'
        }

        try:
            response = requests.get(AddressLookupService.BASE_URL, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
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
            else:
                logger.error(f"Lookup service returned status {response.status_code} for building {building_name}")
                return None
        except requests.RequestException as e:
            logger.exception(f"Request exception during address lookup for building {building_name}")
            return None

        return None

    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """
        Calculate the approximate distance between two points using
        equirectangular projection (unit: kilometers).
        """
        R = 6371  # Radius of the Earth in kilometers
        lat1_rad = math.radians(float(lat1))
        lon1_rad = math.radians(float(lon1))
        lat2_rad = math.radians(float(lat2))
        lon2_rad = math.radians(float(lon2))

        x = (lon2_rad - lon1_rad) * math.cos((lat1_rad + lat2_rad) / 2)
        y = lat2_rad - lat1_rad
        d = math.sqrt(x * x + y * y) * R
        return d

def validate_required_fields(data, fields):
    missing = [field for field in fields if field not in data or not data[field]]
    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(missing)}")
