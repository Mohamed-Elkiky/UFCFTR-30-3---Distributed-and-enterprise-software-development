from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils.timezone import now


def create_surplus_deal(product, discount_percent, hours_valid, note=""):
    """Create a SurplusDeal for the given product.

    discount_percent must be between 10 and 50 (inclusive).
    expires_at is set to now() + timedelta(hours=hours_valid).
    """
    from apps.marketplace.models import SurplusDeal

    if not (10 <= discount_percent <= 50):
        raise ValidationError(
            f"discount_percent must be between 10 and 50, got {discount_percent}."
        )

    discount_bp = int(discount_percent * 100)

    deal = SurplusDeal.objects.create(
        product=product,
        discount_bp=discount_bp,
        expires_at=now() + timedelta(hours=hours_valid),
        note=note,
    )
    return deal


def get_active_surplus_deals():
    """Return all SurplusDeals that have not yet expired."""
    from apps.marketplace.models import SurplusDeal

    return SurplusDeal.objects.filter(expires_at__gt=now())


def apply_surplus_discount(product):
    """Return the discounted price in pence if an active surplus deal exists.

    Returns the original price_pence if no active deal exists.
    """
    try:
        deal = product.surplus_deal
    except product.__class__.surplus_deal.RelatedObjectDoesNotExist:
        return product.price_pence

    if deal.expires_at <= now():
        return product.price_pence

    discount_factor = 1 - (deal.discount_bp / 10000)
    return int(product.price_pence * discount_factor)


def expire_old_deals():
    """Delete all SurplusDeals whose expires_at is in the past.

    Intended to be run as a management command or scheduled task.
    """
    from apps.marketplace.models import SurplusDeal

    deleted_count, _ = SurplusDeal.objects.filter(expires_at__lt=now()).delete()
    return deleted_count
