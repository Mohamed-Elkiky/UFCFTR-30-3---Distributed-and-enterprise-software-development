# apps/notifications/services/low_stock.py
"""
Low-stock notification helper (TC-023).

Behaviour:
- When stock_qty <= low_stock_threshold AND > 0, create a LOW_STOCK
  notification (avoids duplicates).
- When stock_qty == 0, create an urgent out-of-stock notification.
- When stock is replenished ABOVE the threshold, **delete** any unread
  low-stock alerts for that product so they don't linger in the
  notification list.

Note: products with stock_qty == 0 stay visible on the marketplace with
an "Out of Stock" badge — they are NOT hidden. The add-to-cart button
is disabled instead.
"""

from apps.notifications.models import Notification
from apps.notifications.services.dispatch import notify_user


def check_and_notify_low_stock(product):
    """
    Check the product's stock level and fire or clear alerts accordingly.
    """
    producer = product.producer
    if not producer:
        return

    user = getattr(producer, "user", None)
    if not user:
        return

    # ---- Zero stock ----
    if product.stock_qty == 0:
        _send_low_stock_alert(user, product, zero=True)
        return

    # ---- Below threshold ----
    if product.stock_qty <= product.low_stock_threshold:
        _send_low_stock_alert(user, product, zero=False)
    else:
        # Stock replenished above threshold — remove stale alerts entirely
        Notification.objects.filter(
            user=user,
            type=Notification.Type.LOW_STOCK,
            data__product_id=str(product.pk),
            is_read=False,
        ).delete()


def _send_low_stock_alert(user, product, zero=False):
    """Create a low-stock notification if one doesn't already exist (unread)."""
    already_notified = Notification.objects.filter(
        user=user,
        type=Notification.Type.LOW_STOCK,
        data__product_id=str(product.pk),
        is_read=False,
    ).exists()

    if already_notified:
        return

    if zero:
        title = f"Out of Stock: {product.name}"
        body = (
            f"{product.name} has reached 0 {product.unit}. "
            f"Customers can see the product but cannot order it. "
            f"Restock to re-enable purchasing."
        )
    else:
        title = f"Low Stock: {product.name}"
        body = (
            f"Only {product.stock_qty} {product.unit} remaining "
            f"(threshold: {product.low_stock_threshold})."
        )

    notify_user(
        user=user,
        type=Notification.Type.LOW_STOCK,
        title=title,
        body=body,
        data={"product_id": str(product.pk)},
    )