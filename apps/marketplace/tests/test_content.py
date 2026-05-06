# apps/content/tests/test_content.py
"""
Tests for producer content: recipes, farm stories, storage guides.
Covers: TC-020
"""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brfn.settings")

import pytest

from tests.factories import ProducerProfileFactory, ProductFactory, CustomerProfileFactory
from apps.content.models import ContentPost, ContentProductLink


@pytest.mark.django_db
class TestTC020_ProducerContent:

    def test_create_recipe(self):
        producer = ProducerProfileFactory()
        post = ContentPost.objects.create(
            producer=producer,
            kind=ContentPost.Kind.RECIPE,
            title="Roasted Root Vegetable Medley",
            body="Preheat oven to 200C. Chop vegetables...",
            seasonal_tag=ContentPost.SeasonalTag.AUTUMN,
        )
        assert post.pk is not None
        assert post.kind == "recipe"
        assert post.title == "Roasted Root Vegetable Medley"

    def test_create_farm_story(self):
        producer = ProducerProfileFactory()
        post = ContentPost.objects.create(
            producer=producer,
            kind=ContentPost.Kind.FARM_STORY,
            title="Harvest Season Update",
            body="This year's harvest has been excellent...",
        )
        assert post.kind == "farm_story"

    def test_create_storage_guide(self):
        producer = ProducerProfileFactory()
        post = ContentPost.objects.create(
            producer=producer,
            kind=ContentPost.Kind.STORAGE_GUIDE,
            title="How to Store Root Vegetables",
            body="Keep in a cool dark place...",
        )
        assert post.kind == "storage_guide"

    def test_link_recipe_to_product(self):
        producer = ProducerProfileFactory()
        product = ProductFactory(producer=producer, name="Carrots")
        post = ContentPost.objects.create(
            producer=producer,
            kind=ContentPost.Kind.RECIPE,
            title="Carrot Soup",
            body="Blend carrots...",
        )
        link = ContentProductLink.objects.create(content=post, product=product)
        assert link.pk is not None
        assert post.product_links.count() == 1
        assert product.content_links.count() == 1

    def test_multiple_products_linked(self):
        producer = ProducerProfileFactory()
        p1 = ProductFactory(producer=producer, name="Carrots")
        p2 = ProductFactory(producer=producer, name="Parsnips")
        post = ContentPost.objects.create(
            producer=producer, kind="recipe",
            title="Root Medley", body="Instructions...",
        )
        ContentProductLink.objects.create(content=post, product=p1)
        ContentProductLink.objects.create(content=post, product=p2)
        assert post.product_links.count() == 2

    def test_duplicate_link_prevented(self):
        producer = ProducerProfileFactory()
        product = ProductFactory(producer=producer)
        post = ContentPost.objects.create(
            producer=producer, kind="recipe",
            title="Test", body="Test",
        )
        ContentProductLink.objects.create(content=post, product=product)
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            ContentProductLink.objects.create(content=post, product=product)

    def test_content_list_view_requires_producer(self, client):
        customer = CustomerProfileFactory()
        client.login(email=customer.user.email, password="password123")
        response = client.get("/content/")
        assert response.status_code == 403

    def test_content_list_view_accessible_by_producer(self, client):
        producer = ProducerProfileFactory()
        client.login(email=producer.user.email, password="password123")
        response = client.get("/content/")
        assert response.status_code == 200

    def test_content_create_view_accessible(self, client):
        producer = ProducerProfileFactory()
        client.login(email=producer.user.email, password="password123")
        response = client.get("/content/new/")
        assert response.status_code == 200

    def test_seasonal_tag_choices(self):
        choices = [c[0] for c in ContentPost.SeasonalTag.choices]
        assert "spring" in choices
        assert "summer" in choices
        assert "autumn" in choices
        assert "winter" in choices
        assert "all_year" in choices

