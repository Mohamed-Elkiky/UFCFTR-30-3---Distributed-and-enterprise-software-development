# apps/notifications/tests/test_low_stock.py
"""
Tests for low stock notifications and alerts.
Covers: TC-023
"""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brfn.settings")

import pytest

from tests.factories import ProducerProfileFactory, ProductFactory
from apps.notifications.models import Notification
from apps.notifications.services.low_stock import check_and_notify_low_stock


@pytest.mark.django_db
class TestTC023_LowStockNotifications:

    def _make_product(self, stock_qty=50, threshold=10):
        producer = ProducerProfileFactory()
        return ProductFactory(
            producer=producer,
            stock_qty=stock_qty,
            low_stock_threshold=threshold,
        )

    def test_no_alert_above_threshold(self):
        product = self._make_product(stock_qty=50, threshold=10)
        check_and_notify_low_stock(product)
        assert Notification.objects.filter(
            type=Notification.Type.LOW_STOCK,
            data__product_id=str(product.pk),
        ).count() == 0

    def test_alert_when_below_threshold(self):
        product = self._make_product(stock_qty=9, threshold=10)
        check_and_notify_low_stock(product)
        notifs = Notification.objects.filter(
            type=Notification.Type.LOW_STOCK,
            data__product_id=str(product.pk),
        )
        assert notifs.count() == 1
        assert "Low Stock" in notifs.first().title

    def test_alert_at_exact_threshold(self):
        product = self._make_product(stock_qty=10, threshold=10)
        check_and_notify_low_stock(product)
        assert Notification.objects.filter(
            type=Notification.Type.LOW_STOCK,
            data__product_id=str(product.pk),
        ).count() == 1

    def test_out_of_stock_alert(self):
        product = self._make_product(stock_qty=0, threshold=10)
        check_and_notify_low_stock(product)
        notifs = Notification.objects.filter(
            type=Notification.Type.LOW_STOCK,
            data__product_id=str(product.pk),
        )
        assert notifs.count() == 1
        assert "Out of Stock" in notifs.first().title

    def test_no_duplicate_alert(self):
        product = self._make_product(stock_qty=5, threshold=10)
        check_and_notify_low_stock(product)
        check_and_notify_low_stock(product)  # second call
        assert Notification.objects.filter(
            type=Notification.Type.LOW_STOCK,
            data__product_id=str(product.pk),
        ).count() == 1

    def test_alert_cleared_when_restocked(self):
        product = self._make_product(stock_qty=5, threshold=10)
        check_and_notify_low_stock(product)
        assert Notification.objects.filter(
            type=Notification.Type.LOW_STOCK,
            data__product_id=str(product.pk),
        ).count() == 1

        # Restock above threshold
        product.stock_qty = 40
        product.save()
        check_and_notify_low_stock(product)

        # Alert should be deleted
        assert Notification.objects.filter(
            type=Notification.Type.LOW_STOCK,
            data__product_id=str(product.pk),
            is_read=False,
        ).count() == 0

    def test_alert_sent_to_producer_user(self):
        producer = ProducerProfileFactory()
        product = ProductFactory(producer=producer, stock_qty=3, low_stock_threshold=10)
        check_and_notify_low_stock(product)
        notif = Notification.objects.get(
            type=Notification.Type.LOW_STOCK,
            data__product_id=str(product.pk),
        )
        assert notif.user == producer.user

    def test_alert_includes_product_name(self):
        product = self._make_product(stock_qty=2, threshold=10)
        product.name = "Fresh Eggs"
        product.save()
        check_and_notify_low_stock(product)
        notif = Notification.objects.get(
            type=Notification.Type.LOW_STOCK,
            data__product_id=str(product.pk),
        )
        assert "Fresh Eggs" in notif.title

    def test_alert_includes_stock_qty_in_body(self):
        product = self._make_product(stock_qty=7, threshold=10)
        check_and_notify_low_stock(product)
        notif = Notification.objects.get(
            type=Notification.Type.LOW_STOCK,
            data__product_id=str(product.pk),
        )
        assert "7" in notif.body