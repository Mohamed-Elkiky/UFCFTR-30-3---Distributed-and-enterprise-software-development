# apps/notifications/services/low_stock.py

from apps.notifications.models import Notification


def check_and_notify_low_stock(product):
    if product.stock_qty > product.low_stock_threshold:
        return

    producer = product.producer
    if not producer:
        return

    user = getattr(producer, 'user', None)
    if not user:
        return

    Notification.objects.create(
        user=user,
        type=Notification.Type.LOW_STOCK,
        channel=Notification.Channel.IN_APP,
        title=f'Low stock: {product.name}',
        body=(
            f'Your product "{product.name}" has only {product.stock_qty} '
            f'{product.unit} remaining (threshold: {product.low_stock_threshold}).'
        ),
        data={'product_id': str(product.pk)},
    )