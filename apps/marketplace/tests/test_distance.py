# apps/logistics/tests/test_distance.py
"""
Tests for food miles calculation.
Covers: TC-013
"""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brfn.settings")

import pytest
from decimal import Decimal

from apps.logistics.services.distance import haversine_miles, get_food_miles, get_order_total_food_miles
from tests.factories import (
    CustomerOrderFactory,
    CustomerProfileFactory,
    OrderItemFactory,
    ProducerProfileFactory,
    ProductFactory,
)


@pytest.mark.django_db
class TestTC013_FoodMiles:

    def test_haversine_same_point_is_zero(self):
        assert haversine_miles(51.45, -2.59, 51.45, -2.59) == 0.0

    def test_haversine_known_distance(self):
        """Bristol (51.45, -2.59) to Bath (51.38, -2.36) ≈ 11 miles."""
        miles = haversine_miles(51.45, -2.59, 51.38, -2.36)
        assert 9 < miles < 15

    def test_haversine_accepts_decimals(self):
        miles = haversine_miles(
            Decimal("51.45"), Decimal("-2.59"),
            Decimal("51.38"), Decimal("-2.36"),
        )
        assert miles > 0

    def test_get_food_miles_with_coordinates(self):
        producer = ProducerProfileFactory(
            latitude=Decimal("51.4500"),
            longitude=Decimal("-2.5900"),
        )
        customer = CustomerProfileFactory()
        customer.latitude = Decimal("51.3800")
        customer.longitude = Decimal("-2.3600")
        customer.save()
        product = ProductFactory(producer=producer)
        miles = get_food_miles(product, customer)
        assert miles is not None
        assert miles > 0

    def test_get_food_miles_missing_producer_coords(self):
        producer = ProducerProfileFactory(latitude=None, longitude=None)
        customer = CustomerProfileFactory(
            latitude=Decimal("51.38"), longitude=Decimal("-2.36"),
        )
        product = ProductFactory(producer=producer)
        assert get_food_miles(product, customer) is None

    def test_get_food_miles_missing_customer_coords(self):
        producer = ProducerProfileFactory(
            latitude=Decimal("51.45"), longitude=Decimal("-2.59"),
        )
        customer = CustomerProfileFactory(latitude=None, longitude=None)
        product = ProductFactory(producer=producer)
        assert get_food_miles(product, customer) is None


    def test_order_food_miles_deduplicates_producers(self):
        """Two items from same producer should count distance once."""
        producer = ProducerProfileFactory(
            latitude=Decimal("51.4500"), longitude=Decimal("-2.5900"),
        )
        customer = CustomerProfileFactory(
            latitude=Decimal("51.3800"), longitude=Decimal("-2.3600"),
        )
        order = CustomerOrderFactory(customer=customer)
        p1 = ProductFactory(producer=producer, name="Carrots")
        p2 = ProductFactory(producer=producer, name="Potatoes")
        OrderItemFactory(order=order, product=p1)
        OrderItemFactory(order=order, product=p2)

        single_product_miles = get_food_miles(p1, customer)
        total = get_order_total_food_miles(order)
        assert total == single_product_miles  # counted only once