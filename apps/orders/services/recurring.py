# apps/orders/services/recurring.py
"""
Service functions for recurring orders (TC-018).

Allows business customers to set up an order template with an iCal RRULE
schedule. A management command (or admin trigger) periodically calls
generate_upcoming_instances() to create RecurringOrderInstance rows for
upcoming dates, and place_recurring_instance() converts a scheduled
instance into a real CustomerOrder.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Iterable

from dateutil.rrule import rrulestr
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.marketplace.models import Product
from apps.marketplace.services.surplus import apply_surplus_discount
from apps.orders.models import (
    CustomerOrder,
    OrderItem,
    ProducerOrder,
    RecurringOrderInstance,
    RecurringOrderItem,
    RecurringOrderTemplate,
)


# ---------------------------------------------------------------------------
# Template creation
# ---------------------------------------------------------------------------

@transaction.atomic
def create_recurring_template(customer_profile, name, rrule_str, items):
    """
    Create a RecurringOrderTemplate and its associated RecurringOrderItem rows.

    Args:
        customer_profile: CustomerProfile that owns the template.
        name: Human-readable name for the template (e.g. "Weekly produce").
        rrule_str: iCal RRULE string, e.g. "FREQ=WEEKLY;BYDAY=MO".
        items: Iterable of (product, quantity) tuples or dicts with
               keys 'product' and 'quantity'.

    Returns:
        The created RecurringOrderTemplate.

    Raises:
        ValueError: if rrule_str is invalid or items is empty.
    """
    if not items:
        raise ValueError("Cannot create a recurring template with no items.")

    # Validate rrule eagerly so we fail before creating any rows.
    try:
        rrulestr(rrule_str, dtstart=datetime.now())
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid RRULE string: {exc}") from exc

    template = RecurringOrderTemplate.objects.create(
        customer=customer_profile,
        name=name,
        rrule=rrule_str,
        active=True,
    )

    for entry in items:
        # Accept either (product, qty) tuples or {'product': p, 'quantity': q} dicts.
        if isinstance(entry, dict):
            product = entry['product']
            quantity = int(entry.get('quantity', 1))
        else:
            product, quantity = entry
            quantity = int(quantity)

        if quantity < 1:
            raise ValueError("Recurring item quantity must be >= 1.")

        RecurringOrderItem.objects.create(
            template=template,
            product=product,
            quantity=quantity,
        )

    return template


# ---------------------------------------------------------------------------
# Schedule expansion
# ---------------------------------------------------------------------------

def generate_upcoming_instances(template, days_ahead=7):
    """
    Materialise RecurringOrderInstance rows for any RRULE-derived dates
    falling within the next `days_ahead` days that don't already have an
    instance for this template.

    Idempotent: safe to run repeatedly. Skips dates that already have an
    instance regardless of that instance's status (placed/skipped/scheduled).

    Args:
        template: RecurringOrderTemplate to expand.
        days_ahead: Window size in days (default 7).

    Returns:
        List of newly created RecurringOrderInstance rows.
    """
    if not template.active:
        return []

    today = timezone.localdate()
    window_end = today + timedelta(days=days_ahead)

    # rrulestr requires a datetime as dtstart; we only care about the date
    # part downstream.
    dtstart = datetime.combine(today, time.min)

    rule = rrulestr(template.rrule, dtstart=dtstart)

    # rrule.between expects datetimes; inc=True includes endpoints.
    upcoming_datetimes = rule.between(
        dtstart,
        datetime.combine(window_end, time.max),
        inc=True,
    )

    upcoming_dates = {dt.date() for dt in upcoming_datetimes}

    # Find which dates already have an instance to avoid duplicates.
    existing_dates = set(
        template.instances
        .filter(scheduled_for__in=upcoming_dates)
        .values_list('scheduled_for', flat=True)
    )

    new_dates = sorted(upcoming_dates - existing_dates)

    created = []
    for scheduled_for in new_dates:
        instance = RecurringOrderInstance.objects.create(
            template=template,
            scheduled_for=scheduled_for,
            status=RecurringOrderInstance.Status.SCHEDULED,
        )
        created.append(instance)

    return created


# ---------------------------------------------------------------------------
# Instance placement
# ---------------------------------------------------------------------------

@transaction.atomic
def place_recurring_instance(instance):
    """
    Convert a SCHEDULED RecurringOrderInstance into a real CustomerOrder.

    Mirrors create_orders_from_cart() but sources items from the template
    rather than a Cart. Groups items by producer, creates one ProducerOrder
    per producer, calculates 5% commission, and decrements stock.

    Args:
        instance: RecurringOrderInstance to place.

    Returns:
        The created CustomerOrder.

    Raises:
        ValueError: if the instance is not in SCHEDULED status, the template
                    is inactive, or it has no items.
    """
    if instance.status != RecurringOrderInstance.Status.SCHEDULED:
        raise ValueError(
            f"Cannot place instance with status '{instance.status}'."
        )

    template = instance.template

    if not template.active:
        raise ValueError("Cannot place an instance for an inactive template.")

    template_items = list(
        template.items.select_related('product', 'product__producer')
    )

    if not template_items:
        raise ValueError("Template has no items.")

    customer_profile = template.customer

    # Build the delivery address snapshot from the customer's saved profile.
    address_parts = [
        customer_profile.street,
        customer_profile.city,
        customer_profile.state,
        customer_profile.country,
    ]
    delivery_address = ", ".join(p for p in address_parts if p).strip()

    # Create the parent CustomerOrder.
    customer_order = CustomerOrder.objects.create(
        customer=customer_profile,
        delivery_address=delivery_address,
        delivery_postcode=customer_profile.postcode,
        delivery_date=instance.scheduled_for,
        special_instructions=f"Recurring order: {template.name}",
        status=CustomerOrder.Status.PENDING,
    )

    # Group template items by producer so we can create one ProducerOrder each.
    items_by_producer: dict = {}
    for item in template_items:
        producer = item.product.producer
        if producer is None:
            raise ValueError(
                f"Product '{item.product.name}' has no producer."
            )
        items_by_producer.setdefault(producer, []).append(item)

    # Create OrderItems and one ProducerOrder per producer.
    for producer, producer_items in items_by_producer.items():
        producer_subtotal = 0

        for tmpl_item in producer_items:
            product = tmpl_item.product
            # Check if this product has a quantity override for this instance
            qty = instance.quantity_overrides.get(
                str(product.id),
                tmpl_item.quantity  # Fall back to template default
            )
            unit_price = apply_surplus_discount(product)
            line_total = unit_price * qty
            producer_subtotal += line_total

            OrderItem.objects.create(
                order=customer_order,
                product=product,
                product_name=product.name,
                product_unit=product.unit,
                price_pence=unit_price,
                quantity=qty,
            )

            # Decrement stock atomically.
            Product.objects.filter(pk=product.pk).update(
                stock_qty=F('stock_qty') - qty
            )

        commission = int(round(producer_subtotal * 0.05))
        producer_payment = producer_subtotal - commission

        ProducerOrder.objects.create(
            customer_order=customer_order,
            producer=producer,
            subtotal_pence=producer_subtotal,
            commission_pence=commission,
            producer_payment_pence=producer_payment,
            delivery_date=instance.scheduled_for,
            status=ProducerOrder.Status.PENDING,
        )

    # Roll up totals onto the CustomerOrder.
    subtotal = sum(oi.line_total_pence for oi in customer_order.items.all())
    customer_order.subtotal_pence = subtotal
    customer_order.commission_pence = int(round(subtotal * 0.05))
    customer_order.total_pence = subtotal
    customer_order.save(
        update_fields=[
            'subtotal_pence',
            'commission_pence',
            'total_pence',
            'updated_at',
        ]
    )

    # Mark the instance as placed and link it to the order.
    instance.customer_order = customer_order
    instance.status = RecurringOrderInstance.Status.PLACED
    instance.save(update_fields=['customer_order', 'status'])

    return customer_order


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def skip_recurring_instance(instance):
    """
    Mark a SCHEDULED instance as SKIPPED so it isn't placed.
    Useful when the customer wants to pause a single occurrence.
    """
    if instance.status != RecurringOrderInstance.Status.SCHEDULED:
        raise ValueError(
            f"Cannot skip instance with status '{instance.status}'."
        )

    instance.status = RecurringOrderInstance.Status.SKIPPED
    instance.save(update_fields=['status'])
    return instance