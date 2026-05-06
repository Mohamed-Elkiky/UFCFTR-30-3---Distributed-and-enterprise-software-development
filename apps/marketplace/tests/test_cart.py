# apps/cart/tests/test_cart.py
"""
Tests for cart and checkout functionality.
Covers: TC-006, TC-007, TC-008
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brfn.settings")

from datetime import date, timedelta

import pytest

from tests.factories import (
    CartFactory,
    CartItemFactory,
    CustomerProfileFactory,
    ProductCategoryFactory,
    ProductFactory,
    ProducerProfileFactory,
)
from apps.cart.models import Cart, CartItem
from apps.cart.services.pricing import (
    add_to_cart,
    get_cart_total_pence,
    get_or_create_cart,
    group_cart_by_producer,
    remove_from_cart,
    update_quantity,
)
from apps.orders.models import CustomerOrder, ProducerOrder, OrderItem
from apps.payments.models import CommissionPolicy


# ======================================================================
# TC-006 — Shopping cart functionality with quantity management
# ======================================================================

@pytest.mark.django_db
class TestTC006_ShoppingCart:
    """Customers can add products, modify quantities, and view cart."""

    def test_add_product_to_cart(self):
        cart = CartFactory()
        product = ProductFactory(price_pence=200)
        item = add_to_cart(cart, product, quantity=2)
        assert item.quantity == 2
        assert cart.items.count() == 1

    def test_add_same_product_increments(self):
        cart = CartFactory()
        product = ProductFactory(price_pence=200)
        add_to_cart(cart, product, quantity=2)
        add_to_cart(cart, product, quantity=3)
        item = cart.items.get(product=product)
        assert item.quantity == 5

    def test_add_multiple_products(self):
        cart = CartFactory()
        p1 = ProductFactory(name="Carrots", price_pence=200)
        p2 = ProductFactory(name="Milk", price_pence=150)
        add_to_cart(cart, p1, quantity=2)
        add_to_cart(cart, p2, quantity=3)
        assert cart.items.count() == 2

    def test_cart_total_calculation(self):
        cart = CartFactory()
        p1 = ProductFactory(price_pence=200)
        p2 = ProductFactory(price_pence=300)
        add_to_cart(cart, p1, quantity=2)  # 400
        add_to_cart(cart, p2, quantity=1)  # 300
        assert get_cart_total_pence(cart) == 700

    def test_update_quantity(self):
        cart = CartFactory()
        product = ProductFactory(price_pence=200)
        add_to_cart(cart, product, quantity=2)
        update_quantity(cart, product, 5)
        item = cart.items.get(product=product)
        assert item.quantity == 5

    def test_remove_from_cart(self):
        cart = CartFactory()
        product = ProductFactory()
        add_to_cart(cart, product, quantity=1)
        assert cart.items.count() == 1
        remove_from_cart(cart, product)
        assert cart.items.count() == 0

    def test_update_quantity_to_zero_removes(self):
        cart = CartFactory()
        product = ProductFactory()
        add_to_cart(cart, product, quantity=3)
        update_quantity(cart, product, 0)
        assert cart.items.count() == 0

    def test_get_or_create_cart(self):
        profile = CustomerProfileFactory()
        cart = get_or_create_cart(profile.user)
        assert cart.customer == profile
        # Calling again returns the same cart
        cart2 = get_or_create_cart(profile.user)
        assert cart.pk == cart2.pk

    def test_group_by_producer(self):
        producer_a = ProducerProfileFactory(business_name="Farm A")
        producer_b = ProducerProfileFactory(business_name="Farm B")
        cart = CartFactory()
        p1 = ProductFactory(producer=producer_a)
        p2 = ProductFactory(producer=producer_b)
        add_to_cart(cart, p1)
        add_to_cart(cart, p2)
        grouped = group_cart_by_producer(cart)
        assert len(grouped) == 2
        assert producer_a in grouped
        assert producer_b in grouped

    def test_cart_view_accessible_by_customer(self, client):
        profile = CustomerProfileFactory()
        client.login(email=profile.user.email, password="password123")
        response = client.get("/cart/")
        assert response.status_code == 200

    def test_line_total_display(self):
        cart = CartFactory()
        product = ProductFactory(price_pence=350)
        item = CartItemFactory(cart=cart, product=product, quantity=2)
        assert item.line_total_display == "7.00"


# ======================================================================
# TC-007 — Single-producer checkout
# ======================================================================

@pytest.mark.django_db
class TestTC007_SingleProducerCheckout:
    """Complete checkout for orders from a single producer."""

    def _setup_checkout(self):
        """Create a commission policy, customer, producer, cart with items."""
        CommissionPolicy.objects.create(
            rate_bp=500,
            valid_from=date(2020, 1, 1),
        )
        profile = CustomerProfileFactory()
        producer = ProducerProfileFactory()
        product = ProductFactory(
            producer=producer,
            price_pence=500,
            stock_qty=100,
            availability="available_year_round",
            best_before_date=date.today() + timedelta(days=14),
        )
        cart = get_or_create_cart(profile.user)
        add_to_cart(cart, product, quantity=2)
        return profile, producer, product, cart

    def test_order_creation_from_cart(self):
        from apps.orders.services.create_order import create_orders_from_cart
        profile, producer, product, cart = self._setup_checkout()
        delivery_date = date.today() + timedelta(days=3)
        order = create_orders_from_cart(
            cart=cart, customer_profile=profile, delivery_date=delivery_date,
        )
        assert order.pk is not None
        assert order.status == "pending"
        assert order.items.count() == 1
        assert order.subtotal_pence == 1000  # 500 * 2

    def test_commission_calculated_at_5_percent(self):
        from apps.orders.services.create_order import create_orders_from_cart
        profile, producer, product, cart = self._setup_checkout()
        order = create_orders_from_cart(
            cart=cart, customer_profile=profile,
            delivery_date=date.today() + timedelta(days=3),
        )
        assert order.commission_pence == 50  # 5% of 1000

    def test_producer_payment_is_95_percent(self):
        from apps.orders.services.create_order import create_orders_from_cart
        profile, producer, product, cart = self._setup_checkout()
        order = create_orders_from_cart(
            cart=cart, customer_profile=profile,
            delivery_date=date.today() + timedelta(days=3),
        )
        po = ProducerOrder.objects.get(customer_order=order, producer=producer)
        assert po.producer_payment_pence == 950  # 95% of 1000

    def test_stock_decremented_after_order(self):
        from apps.orders.services.create_order import create_orders_from_cart
        profile, producer, product, cart = self._setup_checkout()
        create_orders_from_cart(
            cart=cart, customer_profile=profile,
            delivery_date=date.today() + timedelta(days=3),
        )
        product.refresh_from_db()
        assert product.stock_qty == 98  # 100 - 2

    def test_cart_emptied_after_order(self):
        from apps.orders.services.create_order import create_orders_from_cart
        profile, producer, product, cart = self._setup_checkout()
        create_orders_from_cart(
            cart=cart, customer_profile=profile,
            delivery_date=date.today() + timedelta(days=3),
        )
        assert cart.items.count() == 0


# ======================================================================
# TC-008 — Multi-vendor checkout with payment distribution
# ======================================================================

@pytest.mark.django_db
class TestTC008_MultiVendorCheckout:
    """Multi-vendor orders create separate ProducerOrders with correct splits."""

    def _setup_multi(self):
        CommissionPolicy.objects.create(rate_bp=500, valid_from=date(2020, 1, 1))
        profile = CustomerProfileFactory()
        producer_a = ProducerProfileFactory(business_name="Farm A")
        producer_b = ProducerProfileFactory(business_name="Farm B")
        pa = ProductFactory(producer=producer_a, price_pence=800, stock_qty=50, availability="available_year_round")
        pb = ProductFactory(producer=producer_b, price_pence=700, stock_qty=50, availability="available_year_round")
        cart = get_or_create_cart(profile.user)
        add_to_cart(cart, pa, quantity=1)
        add_to_cart(cart, pb, quantity=1)
        delivery = date.today() + timedelta(days=3)
        return profile, producer_a, producer_b, pa, pb, cart, delivery

    def test_creates_two_producer_orders(self):
        from apps.orders.services.create_order import create_orders_from_cart
        profile, pa_prof, pb_prof, pa, pb, cart, delivery = self._setup_multi()
        order = create_orders_from_cart(cart=cart, customer_profile=profile, delivery_date=delivery)
        assert order.producer_orders.count() == 2

    def test_total_is_sum_of_both(self):
        from apps.orders.services.create_order import create_orders_from_cart
        profile, pa_prof, pb_prof, pa, pb, cart, delivery = self._setup_multi()
        order = create_orders_from_cart(cart=cart, customer_profile=profile, delivery_date=delivery)
        assert order.subtotal_pence == 1500  # 800 + 700

    def test_commission_on_total(self):
        from apps.orders.services.create_order import create_orders_from_cart
        profile, pa_prof, pb_prof, pa, pb, cart, delivery = self._setup_multi()
        order = create_orders_from_cart(cart=cart, customer_profile=profile, delivery_date=delivery)
        assert order.commission_pence == 75  # 5% of 1500

    def test_producer_a_gets_correct_split(self):
        from apps.orders.services.create_order import create_orders_from_cart
        profile, pa_prof, pb_prof, pa, pb, cart, delivery = self._setup_multi()
        order = create_orders_from_cart(cart=cart, customer_profile=profile, delivery_date=delivery)
        po_a = ProducerOrder.objects.get(customer_order=order, producer=pa_prof)
        assert po_a.subtotal_pence == 800
        assert po_a.commission_pence == 40  # 5% of 800
        assert po_a.producer_payment_pence == 760  # 95% of 800

    def test_producer_b_gets_correct_split(self):
        from apps.orders.services.create_order import create_orders_from_cart
        profile, pa_prof, pb_prof, pa, pb, cart, delivery = self._setup_multi()
        order = create_orders_from_cart(cart=cart, customer_profile=profile, delivery_date=delivery)
        po_b = ProducerOrder.objects.get(customer_order=order, producer=pb_prof)
        assert po_b.subtotal_pence == 700
        assert po_b.commission_pence == 35  # 5% of 700
        assert po_b.producer_payment_pence == 665  # 95% of 700

    def test_empty_cart_raises(self):
        from apps.orders.services.create_order import create_orders_from_cart
        profile = CustomerProfileFactory()
        cart = get_or_create_cart(profile.user)
        with pytest.raises(ValueError, match="Cannot create order from empty cart"):
            create_orders_from_cart(cart=cart, customer_profile=profile, delivery_date=date.today())