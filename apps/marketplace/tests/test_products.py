# apps/marketplace/tests/test_products.py
"""
Tests for marketplace product functionality.
Covers: TC-003, TC-004, TC-005, TC-014, TC-015, TC-016
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brfn.settings")

from datetime import date, timedelta

import pytest

from tests.factories import (
    AllergenFactory,
    ProductAllergenFactory,
    ProductCategoryFactory,
    ProductFactory,
    ProducerProfileFactory,
    CustomerProfileFactory,
)
from apps.marketplace.models import Product, ProductAllergen, ProductCategory


# ======================================================================
# TC-003 — Producer creates product listing with seasonal availability
# ======================================================================

@pytest.mark.django_db
class TestTC003_ProductCreation:
    """Producer can create product listings with all required information."""

    def test_product_created_with_required_fields(self):
        product = ProductFactory(
            name="Organic Free Range Eggs",
            price_pence=350,
            unit="dozen",
            stock_qty=50,
        )
        assert product.pk is not None
        assert product.name == "Organic Free Range Eggs"
        assert product.price_pence == 350
        assert product.unit == "dozen"
        assert product.stock_qty == 50

    def test_product_linked_to_producer(self):
        producer = ProducerProfileFactory(business_name="Bristol Valley Farm")
        product = ProductFactory(producer=producer)
        assert product.producer == producer
        assert product.producer.business_name == "Bristol Valley Farm"

    def test_product_linked_to_category(self):
        category = ProductCategoryFactory(name="Dairy & Eggs")
        product = ProductFactory(category=category)
        assert product.category.name == "Dairy & Eggs"

    def test_allergens_can_be_attached(self):
        product = ProductFactory()
        allergen = AllergenFactory(name="Eggs")
        ProductAllergenFactory(product=product, allergen=allergen)
        assert product.allergen_links.count() == 1
        assert product.allergen_links.first().allergen.name == "Eggs"

    def test_seasonal_availability_fields(self):
        product = ProductFactory(
            availability=Product.AvailabilityStatus.IN_SEASON,
            seasonal_start_month=6,
            seasonal_end_month=8,
        )
        assert product.availability == "in_season"
        assert product.seasonal_start_month == 6
        assert product.seasonal_end_month == 8

    def test_price_display_format(self):
        product = ProductFactory(price_pence=350)
        assert product.price_display == "£3.50"

    def test_product_create_view_requires_producer(self, client):
        """Non-producer users get 403 when trying to create a product."""
        customer = CustomerProfileFactory()
        client.login(email=customer.user.email, password="password123")
        response = client.get("/products/new/")
        assert response.status_code == 403

    def test_product_create_view_accessible_by_producer(self, client):
        """Producer can access the product creation form."""
        producer = ProducerProfileFactory()
        client.login(email=producer.user.email, password="password123")
        response = client.get("/products/new/")
        assert response.status_code == 200

    def test_product_create_post_saves(self, client):
        """Producer can submit the product form and create a product."""
        producer = ProducerProfileFactory()
        category = ProductCategoryFactory(name="Vegetables")
        client.login(email=producer.user.email, password="password123")

        data = {
            "name": "Organic Carrots",
            "category": category.pk,
            "description": "Fresh organic carrots",
            "price_pence": 250,
            "unit": "kg",
            "availability": "available_year_round",
            "stock_qty": 30,
            "low_stock_threshold": 5,
        }
        response = client.post("/products/new/", data)
        assert response.status_code == 302  # redirect on success
        assert Product.objects.filter(name="Organic Carrots").exists()


# ======================================================================
# TC-004 — Customer browses products by category
# ======================================================================

@pytest.mark.django_db
class TestTC004_BrowseByCategory:
    """Customers can browse products filtered by category."""

    def _setup_categories(self):
        veg = ProductCategoryFactory(name="Vegetables")
        dairy = ProductCategoryFactory(name="Dairy")
        ProductFactory(category=veg, name="Carrots", availability="available_year_round")
        ProductFactory(category=veg, name="Potatoes", availability="available_year_round")
        ProductFactory(category=dairy, name="Milk", availability="available_year_round")
        return veg, dairy

    def test_category_page_returns_correct_products(self, client):
        veg, dairy = self._setup_categories()
        response = client.get(f"/category/{veg.pk}/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Carrots" in content
        assert "Potatoes" in content
        assert "Milk" not in content

    def test_dairy_category_shows_only_dairy(self, client):
        veg, dairy = self._setup_categories()
        response = client.get(f"/category/{dairy.pk}/")
        content = response.content.decode()
        assert "Milk" in content
        assert "Carrots" not in content

    def test_unavailable_products_excluded_from_category(self, client):
        veg = ProductCategoryFactory(name="Vegetables")
        ProductFactory(category=veg, name="Good Carrots", availability="available_year_round")
        ProductFactory(category=veg, name="Bad Carrots", availability="unavailable")
        response = client.get(f"/category/{veg.pk}/")
        content = response.content.decode()
        assert "Good Carrots" in content
        assert "Bad Carrots" not in content

    def test_category_list_page(self, client):
        veg, dairy = self._setup_categories()
        response = client.get("/categories/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Vegetables" in content
        assert "Dairy" in content


# ======================================================================
# TC-005 — Search products by name, description, or producer
# ======================================================================

@pytest.mark.django_db
class TestTC005_ProductSearch:
    """Search returns relevant results based on name/description/producer."""

    def test_search_by_name(self, client):
        ProductFactory(name="Organic Tomatoes", availability="available_year_round")
        ProductFactory(name="Fresh Milk", availability="available_year_round")
        response = client.get("/search/", {"q": "tomatoes"})
        assert response.status_code == 200
        content = response.content.decode()
        assert "Organic Tomatoes" in content
        assert "Fresh Milk" not in content

    def test_search_by_producer(self, client):
        producer = ProducerProfileFactory(business_name="Bristol Valley Farm")
        ProductFactory(producer=producer, name="Eggs", availability="available_year_round")
        ProductFactory(name="Other Eggs", availability="available_year_round")
        response = client.get("/search/", {"q": "Bristol Valley"})
        content = response.content.decode()
        assert "Eggs" in content

    def test_search_case_insensitive(self, client):
        ProductFactory(name="Organic Lettuce", availability="available_year_round")
        response = client.get("/search/", {"q": "ORGANIC"})
        content = response.content.decode()
        assert "Organic Lettuce" in content

    def test_search_no_results_handled(self, client):
        response = client.get("/search/", {"q": "nonexistentproduct12345"})
        assert response.status_code == 200

    def test_search_json_endpoint(self, client):
        ProductFactory(name="TestProduct42", availability="in_season")
        response = client.get("/search/json/", {"q": "TestProduct42"})
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["name"] == "TestProduct42"


# ======================================================================
# TC-014 — Filter products by organic certification
# ======================================================================

@pytest.mark.django_db
class TestTC014_OrganicFilter:
    """Customers can filter to only show organic-certified products."""

    def test_organic_filter_on_home(self, client):
        ProductFactory(name="Organic Veg", organic_certified=True, availability="available_year_round")
        ProductFactory(name="Normal Veg", organic_certified=False, availability="available_year_round")
        response = client.get("/", {"organic": "1"})
        content = response.content.decode()
        assert "Organic Veg" in content
        assert "Normal Veg" not in content

    def test_organic_filter_on_category(self, client):
        cat = ProductCategoryFactory(name="Veg")
        ProductFactory(category=cat, name="Organic Carrot", organic_certified=True, availability="available_year_round")
        ProductFactory(category=cat, name="Normal Carrot", organic_certified=False, availability="available_year_round")
        response = client.get(f"/category/{cat.pk}/", {"organic": "1"})
        content = response.content.decode()
        assert "Organic Carrot" in content
        assert "Normal Carrot" not in content

    def test_organic_filter_on_search(self, client):
        ProductFactory(name="Organic Apple", organic_certified=True, availability="in_season")
        ProductFactory(name="Normal Apple", organic_certified=False, availability="in_season")
        response = client.get("/search/", {"q": "Apple", "organic": "1"})
        content = response.content.decode()
        assert "Organic Apple" in content
        assert "Normal Apple" not in content


# ======================================================================
# TC-015 — Allergen warnings displayed (UK 14 major allergens)
# ======================================================================

@pytest.mark.django_db
class TestTC015_AllergenDisplay:
    """Allergen information is prominently displayed on product detail."""

    def test_allergens_shown_on_detail(self, client):
        product = ProductFactory(name="Cheddar Cheese")
        allergen = AllergenFactory(name="Milk")
        ProductAllergenFactory(product=product, allergen=allergen)
        response = client.get(f"/product/{product.pk}/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Milk" in content

    def test_multiple_allergens_shown(self, client):
        product = ProductFactory(name="Walnut Bread")
        for name in ["Wheat (Gluten)", "Nuts (Walnuts)"]:
            a = AllergenFactory(name=name)
            ProductAllergenFactory(product=product, allergen=a)
        response = client.get(f"/product/{product.pk}/")
        content = response.content.decode()
        assert "Wheat (Gluten)" in content
        assert "Nuts (Walnuts)" in content

    def test_no_allergens_product(self, client):
        product = ProductFactory(name="Fresh Apples")
        response = client.get(f"/product/{product.pk}/")
        assert response.status_code == 200
        # Page should still load fine with no allergens
        assert product.allergen_links.count() == 0

    def test_allergen_model_unique_constraint(self):
        product = ProductFactory()
        allergen = AllergenFactory(name="Soy")
        ProductAllergenFactory(product=product, allergen=allergen)
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            ProductAllergen.objects.create(product=product, allergen=allergen)


# ======================================================================
# TC-016 — Producer sets seasonal availability with date ranges
# ======================================================================

@pytest.mark.django_db
class TestTC016_SeasonalAvailability:
    """Producer can set seasonal availability; customers see correct indicators."""

    def test_in_season_product_visible(self, client):
        ProductFactory(name="Strawberries", availability="in_season")
        response = client.get("/")
        content = response.content.decode()
        assert "Strawberries" in content

    def test_out_of_season_product_hidden(self, client):
        ProductFactory(name="Winter Berries", availability="out_of_season")
        response = client.get("/")
        content = response.content.decode()
        assert "Winter Berries" not in content

    def test_seasonal_service_normal_range(self):
        from apps.marketplace.services.seasonal import is_in_season
        product = ProductFactory.build(
            availability="in_season",
            seasonal_start_month=6,
            seasonal_end_month=8,
        )
        today_month = date.today().month
        expected = 6 <= today_month <= 8
        assert is_in_season(product) == expected

    def test_seasonal_service_wraparound(self):
        from apps.marketplace.services.seasonal import is_in_season
        product = ProductFactory.build(
            availability="in_season",
            seasonal_start_month=11,
            seasonal_end_month=2,
        )
        today_month = date.today().month
        expected = today_month >= 11 or today_month <= 2
        assert is_in_season(product) == expected

    def test_year_round_not_seasonal(self):
        from apps.marketplace.services.seasonal import is_in_season
        product = ProductFactory.build(availability="available_year_round")
        assert is_in_season(product) is False

    def test_auto_update_seasonal(self):
        from apps.marketplace.services.seasonal import auto_update_seasonal_availability, is_in_season
        product = ProductFactory(
            availability="out_of_season",
            seasonal_start_month=1,
            seasonal_end_month=12,  # always in season
        )
        auto_update_seasonal_availability()
        product.refresh_from_db()
        assert product.availability == "in_season"