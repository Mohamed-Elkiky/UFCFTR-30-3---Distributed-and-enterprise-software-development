from datetime import date


def is_in_season(product) -> bool:
    """Return True if the product is currently in season."""
    if product.availability not in ('in_season', 'out_of_season'):
        return False

    start = product.seasonal_start_month
    end = product.seasonal_end_month

    if start is None or end is None:
        return False

    current_month = date.today().month

    if start <= end:
        return start <= current_month <= end
    else:
        # Wraps around year boundary (e.g. November → February)
        return current_month >= start or current_month <= end


def auto_update_seasonal_availability():
    """Update availability for all seasonal products based on the current month."""
    from apps.marketplace.models import Product

    seasonal_products = Product.objects.filter(
        availability__in=[
            Product.AvailabilityStatus.IN_SEASON,
            Product.AvailabilityStatus.OUT_OF_SEASON,
        ]
    )

    to_update = []
    for product in seasonal_products:
        new_status = (
            Product.AvailabilityStatus.IN_SEASON
            if is_in_season(product)
            else Product.AvailabilityStatus.OUT_OF_SEASON
        )
        if product.availability != new_status:
            product.availability = new_status
            to_update.append(product)

    if to_update:
        Product.objects.bulk_update(to_update, ['availability'])
