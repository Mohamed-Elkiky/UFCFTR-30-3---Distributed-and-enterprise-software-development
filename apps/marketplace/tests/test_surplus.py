# apps/marketplace/tests/test_surplus.py
"""
Tests for surplus produce discounts.
Covers: TC-019
"""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brfn.settings")

from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils.timezone import now

from tests.factories import ProductFactory, ProducerProfileFactory
from apps.marketplace.models import SurplusDeal
from apps.marketplace.services.surplus import (
    create_surplus_deal,
    get_active_surplus_deals,
    apply_surplus_discount,
    expire_old_deals,
)


@pytest.mark.django_db
class TestTC019_SurplusDeals:

    def test_create_surplus_deal(self):
        product = ProductFactory(price_pence=1000)
        deal = create_surplus_deal(product, discount_percent=20, hours_valid=24)
        assert deal.pk is not None
        assert deal.discount_bp == 2000
        assert deal.product == product

    def test_discount_below_10_rejected(self):
        product = ProductFactory()
        with pytest.raises(ValidationError):
            create_surplus_deal(product, discount_percent=5, hours_valid=24)

    def test_discount_above_50_rejected(self):
        product = ProductFactory()
        with pytest.raises(ValidationError):
            create_surplus_deal(product, discount_percent=60, hours_valid=24)

    def test_apply_surplus_discount_20_percent(self):
        product = ProductFactory(price_pence=1000)
        create_surplus_deal(product, discount_percent=20, hours_valid=24)
        discounted = apply_surplus_discount(product)
        assert discounted == 800  # 20% off 1000

    def test_apply_surplus_discount_30_percent(self):
        product = ProductFactory(price_pence=1000)
        create_surplus_deal(product, discount_percent=30, hours_valid=24)
        discounted = apply_surplus_discount(product)
        assert discounted == 700

    def test_no_deal_returns_original_price(self):
        product = ProductFactory(price_pence=500)
        assert apply_surplus_discount(product) == 500

    def test_get_active_surplus_deals(self):
        product = ProductFactory()
        create_surplus_deal(product, discount_percent=20, hours_valid=24)
        active = get_active_surplus_deals()
        assert active.count() >= 1

    def test_expired_deal_excluded_from_active(self):
        product = ProductFactory()
        deal = create_surplus_deal(product, discount_percent=20, hours_valid=24)
        SurplusDeal.objects.filter(pk=deal.pk).update(expires_at=now() - timedelta(hours=1))
        active = get_active_surplus_deals()
        assert not active.filter(pk=deal.pk).exists()

    def test_expired_deal_returns_original_price(self):
        product = ProductFactory(price_pence=1000)
        deal = create_surplus_deal(product, discount_percent=20, hours_valid=24)
        SurplusDeal.objects.filter(pk=deal.pk).update(expires_at=now() - timedelta(hours=1))
        product.refresh_from_db()
        assert apply_surplus_discount(product) == 1000

    def test_expire_old_deals_deletes(self):
        product = ProductFactory()
        deal = create_surplus_deal(product, discount_percent=20, hours_valid=24)
        SurplusDeal.objects.filter(pk=deal.pk).update(expires_at=now() - timedelta(hours=1))
        deleted = expire_old_deals()
        assert deleted >= 1
        assert not SurplusDeal.objects.filter(pk=deal.pk).exists()

    def test_surplus_deal_note_stored(self):
        product = ProductFactory()
        deal = create_surplus_deal(product, 20, 24, note="Must sell quickly")
        assert deal.note == "Must sell quickly"

    def test_surplus_deals_page_accessible(self, client):
        response = client.get("/surplus/")
        assert response.status_code == 200

    def test_producer_can_mark_surplus(self, client):
        producer = ProducerProfileFactory()
        product = ProductFactory(producer=producer, price_pence=1000)
        client.login(email=producer.user.email, password="password123")
        response = client.post(f"/products/{product.pk}/surplus/", {
            "discount_percent": 25,
            "hours_valid": 48,
            "note": "Surplus stock",
        })
        assert response.status_code == 302
        assert SurplusDeal.objects.filter(product=product).exists()