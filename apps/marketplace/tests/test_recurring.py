# apps/orders/tests/test_recurring.py
"""
Tests for recurring weekly orders.
Covers: TC-018
"""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brfn.settings")

from datetime import date, timedelta

import pytest

from tests.factories import CustomerProfileFactory, ProducerProfileFactory, ProductFactory
from apps.orders.models import (
    RecurringOrderTemplate,
    RecurringOrderItem,
    RecurringOrderInstance,
)
from apps.orders.services.recurring import (
    create_recurring_template,
    generate_upcoming_instances,
    place_recurring_instance,
    skip_recurring_instance,
)


@pytest.mark.django_db
class TestTC018_RecurringOrders:

    def _make_template(self, customer=None):
        customer = customer or CustomerProfileFactory()
        producer = ProducerProfileFactory()
        product = ProductFactory(producer=producer, price_pence=500, stock_qty=100)
        template = create_recurring_template(
            customer_profile=customer,
            name="Weekly Produce",
            rrule_str="FREQ=DAILY",
            items=[(product, 3)],
        )
        return template, customer, product

    def test_create_template(self):
        template, _, _ = self._make_template()
        assert template.pk is not None
        assert template.name == "Weekly Produce"
        assert template.active is True
        assert template.items.count() == 1

    def test_template_stores_rrule(self):
        template, _, _ = self._make_template()
        assert "FREQ=DAILY" in template.rrule

    def test_template_items_linked(self):
        template, _, product = self._make_template()
        item = template.items.first()
        assert item.product == product
        assert item.quantity == 3

    def test_empty_items_raises(self):
        customer = CustomerProfileFactory()
        with pytest.raises(ValueError, match="no items"):
            create_recurring_template(customer, "Empty", "FREQ=DAILY", items=[])

    def test_invalid_rrule_raises(self):
        customer = CustomerProfileFactory()
        product = ProductFactory()
        with pytest.raises(ValueError, match="Invalid RRULE"):
            create_recurring_template(customer, "Bad", "NOT_A_RULE", items=[(product, 1)])

    def test_generate_upcoming_instances(self):
        template, _, _ = self._make_template()
        instances = generate_upcoming_instances(template, days_ahead=3)
        assert len(instances) > 0
        for inst in instances:
            assert inst.status == "scheduled"

    def test_generate_is_idempotent(self):
        template, _, _ = self._make_template()
        first_run = generate_upcoming_instances(template, days_ahead=3)
        second_run = generate_upcoming_instances(template, days_ahead=3)
        assert len(second_run) == 0  # no duplicates

    def test_inactive_template_generates_nothing(self):
        template, _, _ = self._make_template()
        template.active = False
        template.save()
        instances = generate_upcoming_instances(template, days_ahead=7)
        assert len(instances) == 0

    def test_place_recurring_instance(self):
        template, customer, product = self._make_template()
        instances = generate_upcoming_instances(template, days_ahead=3)
        instance = instances[0]
        order = place_recurring_instance(instance)
        assert order.pk is not None
        assert order.customer == customer
        assert order.items.count() == 1
        assert order.items.first().quantity == 3
        instance.refresh_from_db()
        assert instance.status == "placed"
        assert instance.customer_order == order

    def test_place_calculates_commission(self):
        template, _, _ = self._make_template()
        instances = generate_upcoming_instances(template, days_ahead=3)
        order = place_recurring_instance(instances[0])
        assert order.subtotal_pence == 1500  # 500 * 3
        assert order.commission_pence == 75  # 5% of 1500

    def test_place_decrements_stock(self):
        template, _, product = self._make_template()
        instances = generate_upcoming_instances(template, days_ahead=3)
        place_recurring_instance(instances[0])
        product.refresh_from_db()
        assert product.stock_qty == 97  # 100 - 3

    def test_cannot_place_already_placed(self):
        template, _, _ = self._make_template()
        instances = generate_upcoming_instances(template, days_ahead=3)
        place_recurring_instance(instances[0])
        with pytest.raises(ValueError, match="Cannot place"):
            place_recurring_instance(instances[0])

    def test_skip_instance(self):
        template, _, _ = self._make_template()
        instances = generate_upcoming_instances(template, days_ahead=3)
        skipped = skip_recurring_instance(instances[0])
        assert skipped.status == "skipped"

    def test_cannot_skip_already_placed(self):
        template, _, _ = self._make_template()
        instances = generate_upcoming_instances(template, days_ahead=3)
        place_recurring_instance(instances[0])
        with pytest.raises(ValueError):
            skip_recurring_instance(instances[0])

    def test_quantity_overrides_applied(self):
        """Instance-level quantity overrides replace template defaults."""
        template, _, product = self._make_template()
        instances = generate_upcoming_instances(template, days_ahead=3)
        instance = instances[0]
        instance.quantity_overrides = {str(product.id): 10}
        instance.save()
        order = place_recurring_instance(instance)
        assert order.items.first().quantity == 10  # overridden from 3

    def test_recurring_orders_view_accessible(self, client):
        customer = CustomerProfileFactory()
        client.login(email=customer.user.email, password="password123")
        response = client.get("/orders/recurring/")
        assert response.status_code == 200