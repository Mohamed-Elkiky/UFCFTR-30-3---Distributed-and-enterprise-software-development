# apps/notifications/services/dispatch.py
"""
Notification dispatch helpers (TC-010, TC-023).
"""

from apps.notifications.models import Notification


def notify_user(user, type, title, body, data=None, channel="in_app"):
    """
    Create a Notification record for the given user.

    Args:
        user: User instance to notify.
        type: Notification.Type value (e.g. 'order_status', 'low_stock').
        title: Short summary shown in the notification list.
        body: Longer description text.
        data: Optional dict of extra context (stored as JSON).
        channel: 'in_app' (default) or 'email'.

    Returns:
        The created Notification instance.
    """
    return Notification.objects.create(
        user=user,
        type=type,
        channel=channel,
        title=title,
        body=body,
        data=data or {},
    )


def notify_order_status_change(producer_order):
    """
    Notify the *customer* that a producer order's status has changed (TC-010).
    """
    customer_user = producer_order.customer_order.customer.user
    producer_name = producer_order.producer.business_name
    status = producer_order.status

    notify_user(
        user=customer_user,
        type=Notification.Type.ORDER_STATUS,
        title=f"Order update from {producer_name}",
        body=f"Your order from {producer_name} is now '{status}'.",
        data={
            "producer_order_id": str(producer_order.pk),
            "customer_order_id": str(producer_order.customer_order_id),
            "status": status,
        },
    )


def notify_new_producer_order(producer_order):
    """
    Notify the *producer* that a new order has been placed for their products (TC-010).
    """
    producer_user = producer_order.producer.user
    customer_name = producer_order.customer_order.customer.full_name

    notify_user(
        user=producer_user,
        type=Notification.Type.ORDER_STATUS,
        title="New order received",
        body=(
            f"You have a new order from {customer_name} "
            f"for £{producer_order.subtotal_pence / 100:.2f}."
        ),
        data={
            "producer_order_id": str(producer_order.pk),
            "customer_order_id": str(producer_order.customer_order_id),
        },
    )