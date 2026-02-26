# apps/orders/services/create_order.py
"""
Service to convert a cart into CustomerOrder + ProducerOrders + OrderItems.
Handles both single-vendor (TC-007) and multi-vendor (TC-008) orders.
"""

from django.db import transaction

from apps.cart.services.pricing import group_cart_by_producer
from apps.orders.models import CustomerOrder, OrderItem, ProducerOrder


@transaction.atomic
def create_orders_from_cart(
    cart,
    customer_profile,
    delivery_date,
    delivery_dates_by_producer=None,
    special_instructions="",
):
    """
    Convert cart contents into a CustomerOrder with ProducerOrder sub-orders.

    Args:
        cart: Cart instance
        customer_profile: CustomerProfile of the buyer
        delivery_date: Default delivery date (date object)
        delivery_dates_by_producer: Optional dict {producer_id: date} for multi-vendor
        special_instructions: Optional delivery note

    Returns:
        CustomerOrder instance
    """
    grouped = group_cart_by_producer(cart)

    if not grouped:
        raise ValueError("Cannot create order from empty cart.")

    delivery_address = f"{customer_profile.street}, {customer_profile.city}"
    delivery_postcode = customer_profile.postcode

    customer_order = CustomerOrder.objects.create(
        customer=customer_profile,
        delivery_address=delivery_address,
        delivery_postcode=delivery_postcode,
        delivery_date=delivery_date,
        special_instructions=special_instructions,
        status=CustomerOrder.Status.PENDING,
    )

    for producer, items in grouped.items():
        if (
            delivery_dates_by_producer
            and producer
            and str(producer.pk) in delivery_dates_by_producer
        ):
            producer_delivery_date = delivery_dates_by_producer[
                str(producer.pk)
            ]
        else:
            producer_delivery_date = delivery_date

        producer_subtotal = 0

        for cart_item in items:
            product = cart_item.product
            line_total = product.price_pence * cart_item.quantity
            producer_subtotal += line_total

            OrderItem.objects.create(
                order=customer_order,
                product=product,
                product_name=product.name,
                product_unit=product.unit,
                price_pence=product.price_pence,
                quantity=cart_item.quantity,
                line_total_pence=line_total,
            )

        commission = int(producer_subtotal * 0.05)
        producer_payment = producer_subtotal - commission

        ProducerOrder.objects.create(
            customer_order=customer_order,
            producer=producer,
            subtotal_pence=producer_subtotal,
            commission_pence=commission,
            producer_payment_pence=producer_payment,
            delivery_date=producer_delivery_date,
            status=ProducerOrder.Status.PENDING,
        )

    subtotal = sum(item.line_total_pence for item in customer_order.items.all())
    commission = int(subtotal * 0.05)

    customer_order.subtotal_pence = subtotal
    customer_order.commission_pence = commission
    customer_order.total_pence = subtotal
    customer_order.save()

    cart.items.all().delete()

    return customer_order