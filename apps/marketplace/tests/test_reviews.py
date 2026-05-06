# apps/reviews/tests/test_reviews.py
"""
Tests for product ratings and reviews (verified purchases).
Covers: TC-024
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brfn.settings")

import pytest

from tests.factories import (
    CustomerOrderFactory,
    CustomerProfileFactory,
    OrderItemFactory,
    ProducerProfileFactory,
    ProductFactory,
)
from apps.orders.models import CustomerOrder
from apps.reviews.models import ProductReview


@pytest.mark.django_db
class TestTC024_ProductReviews:
    """Customers can rate/review products they've purchased and received."""

    def _setup_delivered_order(self, customer, product):
        """Create a delivered order containing the given product."""
        order = CustomerOrderFactory(
            customer=customer,
            status=CustomerOrder.Status.DELIVERED,
        )
        OrderItemFactory(order=order, product=product, product_name=product.name)
        return order

    def test_submit_review_for_delivered_product(self, client):
        customer = CustomerProfileFactory()
        product = ProductFactory(name="Organic Tomatoes")
        self._setup_delivered_order(customer, product)

        client.login(email=customer.user.email, password="password123")
        response = client.post(
            f"/reviews/reviews/{product.pk}/submit/",
            {"stars": 5, "title": "Excellent quality", "body": "Very fresh!"},
        )
        assert response.status_code == 302  # redirect to product detail
        assert ProductReview.objects.filter(
            product=product, customer=customer
        ).exists()
        review = ProductReview.objects.get(product=product, customer=customer)
        assert review.stars == 5
        assert review.title == "Excellent quality"

    def test_cannot_review_undelivered_order(self, client):
        customer = CustomerProfileFactory()
        product = ProductFactory()
        # Order is still pending, not delivered
        order = CustomerOrderFactory(
            customer=customer,
            status=CustomerOrder.Status.PENDING,
        )
        OrderItemFactory(order=order, product=product, product_name=product.name)

        client.login(email=customer.user.email, password="password123")
        response = client.post(
            f"/reviews/reviews/{product.pk}/submit/",
            {"stars": 4, "title": "Good", "body": "Nice"},
        )
        assert response.status_code == 403

    def test_cannot_review_product_not_purchased(self, client):
        customer = CustomerProfileFactory()
        product = ProductFactory()
        # No order at all

        client.login(email=customer.user.email, password="password123")
        response = client.post(
            f"/reviews/reviews/{product.pk}/submit/",
            {"stars": 3, "title": "OK", "body": "Average"},
        )
        assert response.status_code == 403

    def test_duplicate_review_blocked(self, client):
        customer = CustomerProfileFactory()
        product = ProductFactory()
        self._setup_delivered_order(customer, product)

        client.login(email=customer.user.email, password="password123")
        # First review
        client.post(
            f"/reviews/reviews/{product.pk}/submit/",
            {"stars": 5, "title": "Great", "body": "Loved it"},
        )
        # Second review should be blocked
        response = client.post(
            f"/reviews/reviews/{product.pk}/submit/",
            {"stars": 1, "title": "Bad", "body": "Changed my mind"},
        )
        assert response.status_code == 403
        assert ProductReview.objects.filter(
            product=product, customer=customer
        ).count() == 1

    def test_review_appears_on_product_page(self, client):
        customer = CustomerProfileFactory()
        product = ProductFactory()
        self._setup_delivered_order(customer, product)
        ProductReview.objects.create(
            product=product,
            customer=customer,
            stars=5,
            title="Fantastic",
            body="Best tomatoes ever",
        )
        response = client.get(f"/product/{product.pk}/")
        content = response.content.decode()
        assert "Fantastic" in content
        assert "Best tomatoes ever" in content

    def test_reviews_list_view(self, client):
        customer = CustomerProfileFactory()
        product = ProductFactory()
        self._setup_delivered_order(customer, product)
        ProductReview.objects.create(
            product=product,
            customer=customer,
            stars=4,
            title="Good stuff",
            body="Tasty!",
        )
        response = client.get(f"/reviews/reviews/{product.pk}/")
        assert response.status_code == 200
        assert "Good stuff" in response.content.decode()

    def test_producer_cannot_submit_review(self, client):
        producer = ProducerProfileFactory()
        product = ProductFactory()
        client.login(email=producer.user.email, password="password123")
        response = client.post(
            f"/reviews/reviews/{product.pk}/submit/",
            {"stars": 5, "title": "Great", "body": "Self-promotion"},
        )
        assert response.status_code == 403

    def test_review_unique_constraint_at_model_level(self):
        customer = CustomerProfileFactory()
        product = ProductFactory()
        ProductReview.objects.create(
            product=product, customer=customer,
            stars=5, title="First", body="Good",
        )
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            ProductReview.objects.create(
                product=product, customer=customer,
                stars=1, title="Second", body="Bad",
            )

    def test_stars_range_validation(self):
        """Stars field accepts values 1-5."""
        customer = CustomerProfileFactory()
        product = ProductFactory()
        review = ProductReview(
            product=product, customer=customer,
            stars=5, title="Max", body="Perfect",
        )
        review.full_clean()  # should not raise

    def test_review_requires_post(self, client):
        customer = CustomerProfileFactory()
        product = ProductFactory()
        client.login(email=customer.user.email, password="password123")
        response = client.get(f"/reviews/reviews/{product.pk}/submit/")
        assert response.status_code == 405  # GET not allowed