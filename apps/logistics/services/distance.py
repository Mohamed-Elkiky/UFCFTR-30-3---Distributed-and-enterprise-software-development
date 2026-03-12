import math


def haversine_miles(lat1, lon1, lat2, lon2):
    """
    Calculate straight-line distance in miles between two points
    using the Haversine formula.
    """
    R = 3958.8  # Earth radius in miles

    lat1, lon1, lat2, lon2 = map(math.radians, [
        float(lat1), float(lon1), float(lat2), float(lon2)
    ])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return round(R * c, 1)


def get_food_miles(product, customer_profile):
    """
    Returns food miles (float) between a product's producer and the customer.
    Returns None if either side is missing coordinates.
    """
    try:
        producer = product.producer
        if not all([producer.latitude, producer.longitude,
                    customer_profile.latitude, customer_profile.longitude]):
            return None
        return haversine_miles(
            producer.latitude, producer.longitude,
            customer_profile.latitude, customer_profile.longitude
        )
    except Exception:
        return None


def get_order_total_food_miles(customer_order):
    """
    Sums food miles for all unique producers in a CustomerOrder.
    Returns None if no valid distances could be calculated.
    """
    try:
        customer_profile = customer_order.customer.customer_profile
    except Exception:
        return None

    seen_producers = set()
    total = 0.0
    any_valid = False

    for item in customer_order.items.select_related('product__producer'):
        producer = item.product.producer
        if producer.id in seen_producers:
            continue
        seen_producers.add(producer.id)
        miles = get_food_miles(item.product, customer_profile)
        if miles is not None:
            total += miles
            any_valid = True

    return round(total, 1) if any_valid else None