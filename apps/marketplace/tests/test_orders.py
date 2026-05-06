# apps/orders/tests/test_orders.py
"""
Tests for order management functionality.
Covers: TC-009, TC-010, TC-021
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brfn.settings")

from datetime import date, timedelta

import pytest

from tests.factories import (
    CustomerOrderFactory,
    CustomerProfileFactory,
    OrderItemFactory,
    ProducerOrderFactory,
    ProducerProfileFactory,
    ProductFactory,
)
from apps.orders.models import CustomerOrder, OrderStatusHistory, ProducerOrder
from apps.orders.services.status_flow import transition_producer_order, VALID_TRANSITIONS


# ======================================================================
# TC-009 — Producer views incoming orders
# ======================================================================

@pytest.mark.django_db
class TestTC009_ProducerViewOrders:
    """Producers can see their incoming orders with customer details."""

    def test_producer_sees_own_orders(self, client):
        producer = ProducerProfileFactory()
        order = CustomerOrderFactory()
        ProducerOrderFactory(customer_order=order, producer=producer)
        client.login(email=producer.user.email, password="password123")
        response = client.get("/orders/producer/")
        assert response.status_code == 200

    def test_producer_cannot_see_other_producers_orders(self, client):
        producer_a = ProducerProfileFactory()
        producer_b = ProducerProfileFactory()
        order = CustomerOrderFactory()
        po = ProducerOrderFactory(customer_order=order, producer=producer_a)
        client.login(email=producer_b.user.email, password="password123")
        response = client.get(f"/orders/producer/{po.id}/")
        assert response.status_code == 404

    def test_producer_order_detail_accessible(self, client):
        producer = ProducerProfileFactory()
        order = CustomerOrderFactory()
        po = ProducerOrderFactory(customer_order=order, producer=producer)
        client.login(email=producer.user.email, password="password123")
        response = client.get(f"/orders/producer/{po.id}/")
        assert response.status_code == 200

    def test_customer_cannot_access_producer_orders(self, client):
        customer = CustomerProfileFactory()
        client.login(email=customer.user.email, password="password123")
        response = client.get("/orders/producer/")
        assert response.status_code == 403


# ======================================================================
# TC-010 — Producer updates order status with notifications
# ======================================================================

@pytest.mark.django_db
class TestTC010_OrderStatusUpdate:
    """Producer can transition order status through the lifecycle."""

    def _make_producer_order(self, status="pending"):
        producer = ProducerProfileFactory()
        order = CustomerOrderFactory()
        po = ProducerOrderFactory(
            customer_order=order,
            producer=producer,
            status=status,
        )
        return producer, po

    def test_pending_to_confirmed(self):
        producer, po = self._make_producer_order("pending")
        result = transition_producer_order(po, "confirmed", producer.user)
        assert result.status == "confirmed"

    def test_confirmed_to_ready(self):
        producer, po = self._make_producer_order("confirmed")
        result = transition_producer_order(po, "ready", producer.user)
        assert result.status == "ready"

    def test_ready_to_delivered(self):
        producer, po = self._make_producer_order("ready")
        # Need a commission policy for the settlement trigger
        from apps.payments.models import CommissionPolicy
        CommissionPolicy.objects.create(rate_bp=500, valid_from=date(2020, 1, 1))
        result = transition_producer_order(po, "delivered", producer.user)
        assert result.status == "delivered"

    def test_invalid_transition_raises(self):
        producer, po = self._make_producer_order("pending")
        with pytest.raises(ValueError, match="Invalid transition"):
            transition_producer_order(po, "delivered", producer.user)

    def test_cannot_skip_stages(self):
        producer, po = self._make_producer_order("pending")
        with pytest.raises(ValueError):
            transition_producer_order(po, "ready", producer.user)

    def test_status_history_created(self):
        producer, po = self._make_producer_order("pending")
        transition_producer_order(po, "confirmed", producer.user)
        history = OrderStatusHistory.objects.filter(producer_order=po)
        assert history.count() == 1
        entry = history.first()
        assert entry.old_status == "pending"
        assert entry.new_status == "confirmed"

    def test_customer_order_syncs_when_all_delivered(self):
        from apps.payments.models import CommissionPolicy
        CommissionPolicy.objects.create(rate_bp=500, valid_from=date(2020, 1, 1))
        customer_order = CustomerOrderFactory(status="pending")
        producer = ProducerProfileFactory()
        po = ProducerOrderFactory(
            customer_order=customer_order,
            producer=producer,
            status="ready",
        )
        transition_producer_order(po, "delivered", producer.user)
        customer_order.refresh_from_db()
        assert customer_order.status == "delivered"

    def test_status_update_via_view(self, client):
        producer, po = self._make_producer_order("pending")
        client.login(email=producer.user.email, password="password123")
        response = client.post(
            f"/orders/producer/{po.id}/status/",
            {"new_status": "confirmed"},
        )
        assert response.status_code == 302
        po.refresh_from_db()
        assert po.status == "confirmed"

    def test_valid_transitions_map(self):
        assert "confirmed" in VALID_TRANSITIONS["pending"]
        assert "cancelled" in VALID_TRANSITIONS["pending"]
        assert "ready" in VALID_TRANSITIONS["confirmed"]
        assert "delivered" in VALID_TRANSITIONS["ready"]
        assert VALID_TRANSITIONS["delivered"] == []
        assert VALID_TRANSITIONS["cancelled"] == []


# ======================================================================
# TC-021 — Order history with reorder functionality
# ======================================================================

@pytest.mark.django_db
class TestTC021_OrderHistoryReorder:
    """Customer can view order history and reorder previous purchases."""

    def test_customer_sees_own_orders(self, client):
        customer = CustomerProfileFactory()
        CustomerOrderFactory(customer=customer)
        CustomerOrderFactory(customer=customer)
        client.login(email=customer.user.email, password="password123")
        response = client.get("/orders/customer/")
        assert response.status_code == 200

    def test_customer_cannot_see_other_orders(self, client):
        customer_a = CustomerProfileFactory()
        customer_b = CustomerProfileFactory()
        order = CustomerOrderFactory(customer=customer_a)
        client.login(email=customer_b.user.email, password="password123")
        response = client.get(f"/orders/customer/{order.id}/")
        assert response.status_code == 404

    def test_order_detail_shows_items(self, client):
        customer = CustomerProfileFactory()
        order = CustomerOrderFactory(customer=customer)
        producer = ProducerProfileFactory()
        product = ProductFactory(name="Test Carrots", producer=producer)
        OrderItemFactory(order=order, product=product, product_name="Test Carrots")
        ProducerOrderFactory(customer_order=order, producer=producer)
        client.login(email=customer.user.email, password="password123")
        response = client.get(f"/orders/customer/{order.id}/")
        assert response.status_code == 200
        assert "Test Carrots" in response.content.decode()

    def test_reorder_adds_items_to_cart(self, client):
        customer = CustomerProfileFactory()
        order = CustomerOrderFactory(customer=customer)
        product = ProductFactory(
            name="Reorder Product",
            availability="available_year_round",
            stock_qty=50,
        )
        OrderItemFactory(
            order=order,
            product=product,
            product_name="Reorder Product",
            quantity=3,
        )
        client.login(email=customer.user.email, password="password123")
        response = client.post(f"/orders/customer/{order.id}/reorder/")
        assert response.status_code == 302  # redirect to cart
        from apps.cart.models import Cart
        cart = Cart.objects.get(customer=customer)
        assert cart.items.count() == 1
        assert cart.items.first().quantity == 3

    def test_reorder_skips_unavailable_products(self, client):
        customer = CustomerProfileFactory()
        order = CustomerOrderFactory(customer=customer)
        available = ProductFactory(name="Available", availability="available_year_round", stock_qty=50)
        unavailable = ProductFactory(name="Unavailable", availability="unavailable", stock_qty=50)
        OrderItemFactory(order=order, product=available, product_name="Available", quantity=1)
        OrderItemFactory(order=order, product=unavailable, product_name="Unavailable", quantity=1)
        client.login(email=customer.user.email, password="password123")
        response = client.post(f"/orders/customer/{order.id}/reorder/")
        assert response.status_code == 302
        from apps.cart.models import Cart
        cart = Cart.objects.get(customer=customer)
        assert cart.items.count() == 1
        assert cart.items.first().product == available

    def test_reorder_requires_post(self, client):
        customer = CustomerProfileFactory()
        order = CustomerOrderFactory(customer=customer)
        client.login(email=customer.user.email, password="password123")
        response = client.get(f"/orders/customer/{order.id}/reorder/")
        assert response.status_code == 405  # Method Not Allowed