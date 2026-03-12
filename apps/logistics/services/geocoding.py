import requests
from decimal import Decimal


def geocode_postcode(postcode):
    """
    Convert a UK postcode to (latitude, longitude) using postcodes.io.
    Returns (Decimal, Decimal) or (None, None) on failure.
    """
    try:
        url = f"https://api.postcodes.io/postcodes/{postcode.strip().replace(' ', '')}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            lat = Decimal(str(data["result"]["latitude"]))
            lng = Decimal(str(data["result"]["longitude"]))
            return lat, lng
    except Exception:
        pass
    return None, None


def update_producer_coordinates(producer_profile):
    lat, lng = geocode_postcode(producer_profile.postcode)
    if lat is not None:
        producer_profile.latitude = lat
        producer_profile.longitude = lng
        producer_profile.save(update_fields=["latitude", "longitude"])


def update_customer_coordinates(customer_profile):
    lat, lng = geocode_postcode(customer_profile.postcode)
    if lat is not None:
        customer_profile.latitude = lat
        customer_profile.longitude = lng
        customer_profile.save(update_fields=["latitude", "longitude"])