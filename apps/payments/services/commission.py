# apps/payments/services/commission.py

from __future__ import annotations

import datetime

from django.db import transaction

from apps.orders.models import CustomerOrder
from apps.payments.models import CommissionPolicy, OrderCommission


def get_active_policy(on_date: datetime.date | None = None) -> CommissionPolicy:
    """Return the CommissionPolicy active on *on_date* (defaults to today)."""
    if on_date is None:
        on_date = datetime.date.today()
    policy = (
        CommissionPolicy.objects.filter(valid_from__lte=on_date)
        .filter(valid_to__isnull=True) | CommissionPolicy.objects.filter(
            valid_from__lte=on_date, valid_to__gte=on_date
        )
    ).order_by("-valid_from").first()
    if policy is None:
        raise ValueError("No active CommissionPolicy found for date %s" % on_date)
    return policy


def calculate_commission(gross_pence: int, rate_bp: int) -> int:
    """Returns round(gross_pence * rate_bp / 10000) as int."""
    return int(round(gross_pence * rate_bp / 10000))


@transaction.atomic
def record_order_commission(customer_order: CustomerOrder) -> OrderCommission:
    """
    Create or update the OrderCommission for a CustomerOrder.

    Uses the active CommissionPolicy and the order's total_pence as gross.
    """
    policy = get_active_policy(customer_order.created_at.date() if customer_order.created_at else None)
    gross_pence = int(customer_order.total_pence or 0)
    commission_pence = calculate_commission(gross_pence, policy.rate_bp)
    net_pence = gross_pence - commission_pence

    record, _ = OrderCommission.objects.update_or_create(
        customer_order=customer_order,
        defaults={
            "commission_policy": policy,
            "gross_pence": gross_pence,
            "commission_pence": commission_pence,
            "net_pence": net_pence,
        },
    )
    return record
