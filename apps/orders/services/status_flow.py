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


def transition_producer_order(
    producer_order: ProducerOrder,
    new_status: str,
    actor_user,
) -> ProducerOrder:
    """
    Validate and perform a ProducerOrder status transition.

    - Checks new_status is allowed based on VALID_TRANSITIONS[current_status]
    - Raises ValueError if invalid
    - Sets status and saves (updated_at auto-updates)
    - Creates an OrderStatusHistory audit record
    """
    old_status = producer_order.status
    allowed = VALID_TRANSITIONS.get(old_status, [])

    if new_status not in allowed:
        raise ValueError(f"Invalid transition: {old_status} -> {new_status}")

    producer_order.status = new_status
    # updated_at is auto_now=True in your model, so save updates timestamp
    producer_order.save(update_fields=["status", "updated_at"])

    OrderStatusHistory.objects.create(
        producer_order=producer_order,
        old_status=old_status,
        new_status=new_status,
        notes="",
        changed_by=actor_user,
        changed_at=timezone.now(),
    )

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

    # CustomerOrder has one delivery_date; ProducerOrder supports per-producer delivery_date
    chosen_dates = [d for d in delivery_dates_by_producer.values() if d]
    overall_delivery_date = min(chosen_dates) if chosen_dates else timezone.now().date()

    # Build delivery address string from CustomerProfile fields
    # street, city, state, country, postcode
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

    # Group items by producer
    items_by_producer: dict[Any, list[Any]] = defaultdict(list)
    for ci in cart_items:
        producer = ci.product.producer
        if producer is None:
            raise ValueError("Cart item product has no producer")
        items_by_producer[producer].append(ci)

    # Create one ProducerOrder per producer
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

    # Create OrderItems, compute producer totals, decrement stock
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
            # OrderItem.save() computes line_total_pence = price_pence * quantity
            producer_subtotal += order_item.line_total_pence

            # Decrement stock (Product.stock_qty exists in your model)
            type(product).objects.filter(pk=product.pk).update(stock_qty=F("stock_qty") - qty)

        # 5% commission on producer subtotal
        commission_pence = int(round(producer_subtotal * 0.05))
        payout_pence = producer_subtotal - commission_pence

        po = producer_orders[producer]
        po.subtotal_pence = producer_subtotal
        po.commission_pence = commission_pence
        po.producer_payment_pence = payout_pence
        po.save(update_fields=["subtotal_pence", "commission_pence", "producer_payment_pence", "updated_at"])

    # Customer totals
    customer_subtotal = sum(po.subtotal_pence for po in producer_orders.values())
    customer_commission = int(round(customer_subtotal * 0.05))

    customer_order.subtotal_pence = customer_subtotal
    customer_order.commission_pence = customer_commission
    # Your CustomerOrder.calculate_totals sets total_pence = subtotal_pence; keep same behaviour
    customer_order.total_pence = customer_subtotal
    customer_order.save(update_fields=["subtotal_pence", "commission_pence", "total_pence", "updated_at"])

    # Empty the cart
    cart.items.all().delete()

    return customer_order