# apps/payments/services/settlement.py
from __future__ import annotations

import datetime
from collections import defaultdict

from django.db import transaction

from apps.orders.models import ProducerOrder
from apps.payments.models import (
    ProducerOrderSettlementLink,
    ProducerSettlement,
    SettlementWeek,
)
from apps.payments.services.commission import calculate_commission, get_active_policy


def get_or_create_settlement_week(week_start_date: datetime.date) -> SettlementWeek:
    """
    Get or create a SettlementWeek for the given Monday.
    week_end is always week_start + 6 days (Sunday).
    """
    week_end_date = week_start_date + datetime.timedelta(days=6)
    week, _ = SettlementWeek.objects.get_or_create(
        week_start=week_start_date,
        defaults={'week_end': week_end_date},
    )
    return week


@transaction.atomic
def run_weekly_settlement(week_start_date: datetime.date) -> list[ProducerSettlement]:
    """
    Run settlement for all delivered ProducerOrders within the given week.

    Steps:
    1. Get/create the SettlementWeek.
    2. Find all delivered ProducerOrders with delivery_date in [week_start, week_end]
       that have not already been linked to a settlement.
    3. Group by producer.
    4. For each producer: sum subtotal_pence, calculate commission and payout,
       create ProducerSettlement, create ProducerOrderSettlementLink per order.

    Returns list of ProducerSettlement objects created in this run.
    """
    week = get_or_create_settlement_week(week_start_date)
    week_end_date = week.week_end

    # Fetch delivered orders in the week not yet settled
    unsettled_orders = (
        ProducerOrder.objects
        .filter(
            status=ProducerOrder.Status.DELIVERED,
            delivery_date__gte=week_start_date,
            delivery_date__lte=week_end_date,
        )
        .exclude(settlement_link__isnull=False)
        .select_related('producer')
    )

    if not unsettled_orders.exists():
        return []

    # Get commission policy active at week_start
    policy = get_active_policy(week_start_date)

    # Group orders by producer
    orders_by_producer: dict = defaultdict(list)
    for order in unsettled_orders:
        orders_by_producer[order.producer].append(order)

    settlements_created = []

    for producer, orders in orders_by_producer.items():
        gross_pence = sum(o.subtotal_pence for o in orders)
        commission_pence = calculate_commission(gross_pence, policy.rate_bp)
        payout_pence = gross_pence - commission_pence

        settlement, created = ProducerSettlement.objects.get_or_create(
            settlement_week=week,
            producer=producer,
            defaults={
                'commission_pence': commission_pence,
                'payout_pence': payout_pence,
                'status': ProducerSettlement.Status.PENDING,
            },
        )

        # If settlement already existed, add to its totals
        if not created:
            settlement.commission_pence += commission_pence
            settlement.payout_pence += payout_pence
            settlement.save(update_fields=['commission_pence', 'payout_pence'])

        # Link each order to this settlement
        for order in orders:
            ProducerOrderSettlementLink.objects.get_or_create(
                producer_order=order,
                defaults={'producer_settlement': settlement},
            )

        settlements_created.append(settlement)

    return settlements_created