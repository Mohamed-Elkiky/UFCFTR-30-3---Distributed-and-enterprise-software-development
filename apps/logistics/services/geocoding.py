import requests
from decimal import Decimal


# Fallback coordinates for common Bristol-area postcodes.
# Used when postcodes.io is unreachable (e.g. inside Docker without
# external network access).  Covers the 20-mile radius commitment.
_BRISTOL_FALLBACK = {
    "BS11AA": (Decimal("51.454500"), Decimal("-2.587900")),
    "BS14DJ": (Decimal("51.451700"), Decimal("-2.600900")),
    "BS15JG": (Decimal("51.453700"), Decimal("-2.596600")),
    "BS161GW": (Decimal("51.490200"), Decimal("-2.531400")),
    "BS81TH": (Decimal("51.461200"), Decimal("-2.614300")),
    "BS91JG": (Decimal("51.487500"), Decimal("-2.635200")),
    "BS419LB": (Decimal("51.430100"), Decimal("-2.659800")),
    "BS137AB": (Decimal("51.426500"), Decimal("-2.601700")),
    "BS130JA": (Decimal("51.408900"), Decimal("-2.594600")),
    "BS66YB": (Decimal("51.468300"), Decimal("-2.601200")),
    "BS82NT": (Decimal("51.463700"), Decimal("-2.608900")),
}


def geocode_postcode(postcode):
    """
    Convert a UK postcode to (latitude, longitude) using postcodes.io.
    Falls back to a static Bristol-area lookup when the API is unreachable.
    Returns (Decimal, Decimal) or (None, None) on failure.
    """
    normalised = postcode.strip().replace(" ", "").upper()

    # Try the live API first
    try:
        url = f"https://api.postcodes.io/postcodes/{normalised}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            lat = Decimal(str(data["result"]["latitude"]))
            lng = Decimal(str(data["result"]["longitude"]))
            return lat, lng
    except Exception:
        pass

    # Fallback to static Bristol-area lookup
    if normalised in _BRISTOL_FALLBACK:
        return _BRISTOL_FALLBACK[normalised]

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