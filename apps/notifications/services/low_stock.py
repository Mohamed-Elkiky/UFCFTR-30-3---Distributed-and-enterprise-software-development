# apps/notifications/services/low_stock.py
"""
Low-stock notification helper (TC-023).
"""

from apps.notifications.models import Notification
from apps.notifications.services.dispatch import notify_user


def check_and_notify_low_stock(product):
    """
    If product.stock_qty <= product.low_stock_threshold, create a low-stock
    notification for the producer.  If stock has been replenished above the
    threshold, mark any existing unread low-stock notifications as read.
    """
    producer = product.producer
    if not producer:
        return

    user = getattr(producer, "user", None)
    if not user:
        return

    if product.stock_qty <= product.low_stock_threshold:
        # Avoid duplicate unread alerts for the same product
        already_notified = Notification.objects.filter(
            user=user,
            type=Notification.Type.LOW_STOCK,
            data__product_id=str(product.pk),
            is_read=False,
        ).exists()

        if not already_notified:
            notify_user(
                user=user,
                type=Notification.Type.LOW_STOCK,
                title=f"Low Stock: {product.name}",
                body=f"Only {product.stock_qty} {product.unit} remaining.",
                data={"product_id": str(product.pk)},
            )
    else:
        # Stock replenished above threshold — clear unread alerts
        Notification.objects.filter(
            user=user,
            type=Notification.Type.LOW_STOCK,
            data__product_id=str(product.pk),
            is_read=False,
        ).update(is_read=True)