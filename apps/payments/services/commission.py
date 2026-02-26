# apps/payments/services/commission.py

from __future__ import annotations

from decimal import Decimal
from typing import Union, Iterable

from django.db import transaction

from apps.orders.models import CustomerOrder, ProducerOrder
from apps.payments.models import CommissionRecord

# 5% = 500 basis points
COMMISSION_RATE_BP = 500
COMMISSION_RATE_DECIMAL = Decimal("0.05")


def calculate_commission(gross_pence: int) -> int:
    """
    Returns round(gross_pence * 500 / 10000) as int.
    """
    return int(round(gross_pence * COMMISSION_RATE_BP / 10000))


def calculate_producer_payout(gross_pence: int) -> int:
    """
    Returns gross_pence - calculate_commission(gross_pence).
    """
    return gross_pence - calculate_commission(gross_pence)


@transaction.atomic
def record_order_commission(customer_order: CustomerOrder) -> list[CommissionRecord]:
    """
    Create/update CommissionRecord rows for ALL ProducerOrders belonging to this CustomerOrder.

    - Uses ProducerOrder.subtotal_pence as the gross amount for that producer
    - Stores commission + payout in CommissionRecord
    - Also updates ProducerOrder.commission_pence and ProducerOrder.producer_payment_pence
      to keep the order tables consistent.
    """
    records: list[CommissionRecord] = []

    producer_orders: Iterable[ProducerOrder] = customer_order.producer_orders.all()

    for po in producer_orders:
        gross_pence = int(po.subtotal_pence or 0)
        commission_pence = calculate_commission(gross_pence)
        payout_pence = gross_pence - commission_pence

        # Keep ProducerOrder totals consistent with service calculation
        if po.commission_pence != commission_pence or po.producer_payment_pence != payout_pence:
            po.commission_pence = commission_pence
            po.producer_payment_pence = payout_pence
            po.save(update_fields=["commission_pence", "producer_payment_pence"])

        record, _created = CommissionRecord.objects.update_or_create(
            producer_order=po,
            defaults={
                "order_value_pence": gross_pence,
                "commission_rate": COMMISSION_RATE_DECIMAL,
                "commission_pence": commission_pence,
                "producer_payout_pence": payout_pence,
            },
        )
        records.append(record)

    # Optional: you could also sync CustomerOrder.commission_pence here if you want:
    # customer_order.commission_pence = sum(r.commission_pence for r in records)
    # customer_order.save(update_fields=["commission_pence"])

    return records