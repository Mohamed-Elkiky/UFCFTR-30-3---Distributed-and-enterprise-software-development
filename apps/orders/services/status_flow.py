# apps/orders/services/status_flow.py

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Dict

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.orders.models import CustomerOrder, ProducerOrder, OrderItem, OrderStatusHistory


VALID_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["confirmed", "cancelled"],
    "confirmed": ["ready", "cancelled"],
    "ready": ["delivered"],
    "delivered": [],
    "cancelled": [],
}


def _sync_customer_order_status(customer_order: CustomerOrder) -> CustomerOrder:
    """
    Update the parent CustomerOrder status based on its ProducerOrders.

    Rules:
    - If all producer orders are delivered -> customer order delivered
    - If all producer orders are cancelled -> customer order cancelled
    - If all producer orders are ready or delivered -> customer order ready
    - If all producer orders are confirmed/ready/delivered -> customer order confirmed
    - Otherwise -> customer order pending
    """
    statuses = list(
        customer_order.producer_orders.values_list("status", flat=True)
    )

    if not statuses:
        return customer_order

    if all(status == ProducerOrder.Status.DELIVERED for status in statuses):
        new_status = CustomerOrder.Status.DELIVERED
    elif all(status == ProducerOrder.Status.CANCELLED for status in statuses):
        new_status = CustomerOrder.Status.CANCELLED
    elif all(
        status in [ProducerOrder.Status.READY, ProducerOrder.Status.DELIVERED]
        for status in statuses
    ):
        new_status = CustomerOrder.Status.READY
    elif all(
        status in [
            ProducerOrder.Status.CONFIRMED,
            ProducerOrder.Status.READY,
            ProducerOrder.Status.DELIVERED,
        ]
        for status in statuses
    ):
        new_status = CustomerOrder.Status.CONFIRMED
    else:
        new_status = CustomerOrder.Status.PENDING

    if customer_order.status != new_status:
        customer_order.status = new_status
        customer_order.save(update_fields=["status", "updated_at"])

    return customer_order


def transition_producer_order(
    producer_order: ProducerOrder,
    new_status: str,
    actor_user,
) -> ProducerOrder:
    """
    Validate and perform a ProducerOrder status transition.

    - Checks new_status is allowed based on VALID_TRANSITIONS[current_status]
    - Raises ValueError if invalid
    - Sets status and saves
    - Creates an OrderStatusHistory audit record
    - Syncs the parent CustomerOrder status
    - Triggers weekly settlement if status is delivered
    """
    old_status = producer_order.status
    allowed = VALID_TRANSITIONS.get(old_status, [])

    if new_status not in allowed:
        raise ValueError(f"Invalid transition: {old_status} -> {new_status}")

    producer_order.status = new_status
    producer_order.save(update_fields=["status", "updated_at"])

    OrderStatusHistory.objects.create(
        producer_order=producer_order,
        old_status=old_status,
        new_status=new_status,
        notes="",
        changed_by=actor_user,
        changed_at=timezone.now(),
    )

    _sync_customer_order_status(producer_order.customer_order)

    if new_status == "delivered":
        import datetime
        from apps.payments.services.settlement import run_weekly_settlement
        today = datetime.date.today()
        week_start = today - datetime.timedelta(days=today.weekday())
        run_weekly_settlement(week_start)

    return producer_order


@transaction.atomic
def create_orders_from_cart(
    cart,
    delivery_dates_by_producer: Dict[Any, date],
    notes: str = "",
) -> CustomerOrder:
    """
    Creates:
      - 1 CustomerOrder
      - 1 ProducerOrder per producer in the cart
      - OrderItem rows with product snapshots

    Calculates:
      - ProducerOrder.subtotal_pence, commission_pence (5%), producer_payment_pence
      - CustomerOrder.subtotal_pence, commission_pence, total_pence

    Decrements:
      - Product.stock_qty for each item

    Empties:
      - deletes CartItem rows for the cart

    Returns:
      - the created CustomerOrder
    """
    cart_items = list(cart.items.select_related("product", "product__producer"))
    if not cart_items:
        raise ValueError("Cart is empty")

    customer_profile = cart.customer

    chosen_dates = [d for d in delivery_dates_by_producer.values() if d]
    overall_delivery_date = min(chosen_dates) if chosen_dates else timezone.now().date()

    address_parts = [
        customer_profile.street,
        customer_profile.city,
        customer_profile.state,
        customer_profile.country,
    ]
    delivery_address = ", ".join([p for p in address_parts if p]).strip()
    delivery_postcode = customer_profile.postcode

    customer_order = CustomerOrder.objects.create(
        customer=customer_profile,
        delivery_address=delivery_address,
        delivery_postcode=delivery_postcode,
        delivery_date=overall_delivery_date,
        special_instructions=notes or "",
        subtotal_pence=0,
        commission_pence=0,
        total_pence=0,
        status=CustomerOrder.Status.PENDING,
    )

    items_by_producer: dict[Any, list[Any]] = defaultdict(list)
    for ci in cart_items:
        producer = ci.product.producer
        if producer is None:
            raise ValueError("Cart item product has no producer")
        items_by_producer[producer].append(ci)

    producer_orders: dict[Any, ProducerOrder] = {}
    for producer in items_by_producer.keys():
        producer_orders[producer] = ProducerOrder.objects.create(
            customer_order=customer_order,
            producer=producer,
            subtotal_pence=0,
            commission_pence=0,
            producer_payment_pence=0,
            status=ProducerOrder.Status.PENDING,
            status_notes=notes or "",
            delivery_date=delivery_dates_by_producer.get(producer),
        )

    for producer, producer_items in items_by_producer.items():
        producer_subtotal = 0

        for ci in producer_items:
            product = ci.product
            qty = int(ci.quantity)

            order_item = OrderItem.objects.create(
                order=customer_order,
                product=product,
                product_name=product.name,
                product_unit=product.unit,
                price_pence=int(product.price_pence),
                quantity=qty,
            )
            producer_subtotal += order_item.line_total_pence

            type(product).objects.filter(pk=product.pk).update(
                stock_qty=F("stock_qty") - qty
            )

        commission_pence = int(round(producer_subtotal * 0.05))
        payout_pence = producer_subtotal - commission_pence

        po = producer_orders[producer]
        po.subtotal_pence = producer_subtotal
        po.commission_pence = commission_pence
        po.producer_payment_pence = payout_pence
        po.save(
            update_fields=[
                "subtotal_pence",
                "commission_pence",
                "producer_payment_pence",
                "updated_at",
            ]
        )

    customer_subtotal = sum(po.subtotal_pence for po in producer_orders.values())
    customer_commission = int(round(customer_subtotal * 0.05))

    customer_order.subtotal_pence = customer_subtotal
    customer_order.commission_pence = customer_commission
    customer_order.total_pence = customer_subtotal
    customer_order.save(
        update_fields=["subtotal_pence", "commission_pence", "total_pence", "updated_at"]
    )

    cart.items.all().delete()

    return customer_order