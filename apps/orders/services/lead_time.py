# apps/orders/services/lead_time.py
"""
Lead time and delivery date utilities (TC-007, TC-008).
Producers require a minimum 48-hour lead time for order preparation.
"""

from datetime import date, timedelta
from django.utils import timezone


LEAD_TIME_HOURS = 48


def get_earliest_delivery_date() -> date:
    """
    Return the earliest date a customer can select for delivery.
    Always at least 48 hours from now.
    """
    earliest = timezone.now() + timedelta(hours=LEAD_TIME_HOURS)
    return earliest.date()


def validate_delivery_date(delivery_date: date) -> bool:
    """
    Return True if delivery_date respects the 48-hour minimum lead time.
    """
    return delivery_date >= get_earliest_delivery_date()