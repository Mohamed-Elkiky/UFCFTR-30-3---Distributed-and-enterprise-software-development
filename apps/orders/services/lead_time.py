# apps/orders/services/lead_time.py

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional, Union

from django.utils import timezone

MIN_LEAD_HOURS = 48


def get_earliest_delivery_date(from_dt: Optional[datetime] = None) -> date:
    """
    Returns the earliest allowed delivery DATE, which is 48 hours from `from_dt` (default: now).
    """
    base = from_dt or timezone.now()
    return (base + timedelta(hours=MIN_LEAD_HOURS)).date()


def validate_delivery_date(
    delivery_date: Union[date, datetime],
    placed_at: Optional[datetime] = None,
) -> None:
    """
    Raises ValueError if `delivery_date` is less than 48 hours from `placed_at` (default: now).

    - If `delivery_date` is a date, we compare it against the earliest allowed delivery *date*
      (i.e., (placed_at + 48h).date()).
    - If `delivery_date` is a datetime, we compare it directly against placed_at + 48 hours.
    """
    placed = placed_at or timezone.now()

    # Ensure placed is timezone-aware (Django best practice)
    if timezone.is_naive(placed):
        placed = timezone.make_aware(placed, timezone.get_current_timezone())

    earliest_dt = placed + timedelta(hours=MIN_LEAD_HOURS)

    if isinstance(delivery_date, datetime):
        ddt = delivery_date
        if timezone.is_naive(ddt):
            ddt = timezone.make_aware(ddt, timezone.get_current_timezone())

        if ddt < earliest_dt:
            raise ValueError(f"Delivery must be at least {MIN_LEAD_HOURS} hours after order placement.")
        return

    # delivery_date is a date
    earliest_date = earliest_dt.date()
    if delivery_date < earliest_date:
        raise ValueError(f"Delivery must be at least {MIN_LEAD_HOURS} hours after order placement.")