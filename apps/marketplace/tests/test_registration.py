# apps/accounts/tests/test_registration.py
"""
Tests for user registration.
Covers: TC-001 (producer), TC-002 (customer), TC-017 (community group)
"""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brfn.settings")

import pytest
from apps.accounts.models import User, ProducerProfile, CustomerProfile, CommunityGroupProfile


# ======================================================================
# TC-001 — Producer registration
# ======================================================================

@pytest.mark.django_db
class TestTC001_ProducerRegistration:

    def _post_producer(self, client):
        return client.post("/accounts/register/producer/", {
            "producer-email": "jane@bristolvalley.com",
            "producer-phone": "01179 123456",
            "producer-password": "SecurePass99",
            "producer-password_confirm": "SecurePass99",
            "producer-business_name": "Bristol Valley Farm",
            "producer-contact_name": "Jane Smith",
            "producer-street": "1 Farm Lane",
            "producer-city": "Bristol",
            "producer-state": "Avon",
            "producer-postcode": "BS1 4DJ",
        })

    def test_producer_registration_redirects(self, client):
        response = self._post_producer(client)
        assert response.status_code == 302

    def test_producer_user_created_with_role(self, client):
        self._post_producer(client)
        user = User.objects.get(email="jane@bristolvalley.com")
        assert user.role == "producer"

    def test_producer_profile_created(self, client):
        self._post_producer(client)
        user = User.objects.get(email="jane@bristolvalley.com")
        assert ProducerProfile.objects.filter(user=user).exists()
        profile = user.producer_profile
        assert profile.business_name == "Bristol Valley Farm"
        assert profile.postcode == "BS1 4DJ"

    def test_producer_can_login_after_registration(self, client):
        self._post_producer(client)
        logged_in = client.login(email="jane@bristolvalley.com", password="SecurePass99")
        assert logged_in

    def test_producer_password_hashed(self, client):
        self._post_producer(client)
        user = User.objects.get(email="jane@bristolvalley.com")
        assert user.password != "SecurePass99"
        assert user.check_password("SecurePass99")

    def test_weak_password_rejected(self, client):
        response = client.post("/accounts/register/producer/", {
            "producer-email": "weak@test.com",
            "producer-phone": "0117",
            "producer-password": "short",
            "producer-password_confirm": "short",
            "producer-business_name": "Test",
            "producer-contact_name": "Test",
            "producer-street": "Test",
            "producer-city": "Test",
            "producer-postcode": "BS1",
        })
        assert not User.objects.filter(email="weak@test.com").exists()

    def test_duplicate_email_rejected(self, client):
        self._post_producer(client)
        client.logout()
        response = client.post("/accounts/register/producer/", {
            "producer-email": "jane@bristolvalley.com",
            "producer-phone": "0117",
            "producer-password": "AnotherPass99",
            "producer-password_confirm": "AnotherPass99",
            "producer-business_name": "Duplicate Farm",
            "producer-contact_name": "Dup",
            "producer-street": "Dup",
            "producer-city": "Dup",
            "producer-postcode": "BS2",
        })
        assert User.objects.filter(email="jane@bristolvalley.com").count() == 1


# ======================================================================
# TC-002 — Customer registration
# ======================================================================

@pytest.mark.django_db
class TestTC002_CustomerRegistration:

    def _post_customer(self, client):
        return client.post("/accounts/register/customer/", {
            "customer-email": "robert@email.com",
            "customer-phone": "07700 900123",
            "customer-password": "SecurePass99",
            "customer-password_confirm": "SecurePass99",
            "customer-full_name": "Robert Johnson",
            "customer-street": "45 Park Street",
            "customer-city": "Bristol",
            "customer-state": "England",
            "customer-postcode": "BS1 5JG",
            "customer-country": "United Kingdom",
            "customer-terms_accepted": "on",
        })

    def test_customer_registration_redirects(self, client):
        response = self._post_customer(client)
        assert response.status_code == 302

    def test_customer_user_created_with_role(self, client):
        self._post_customer(client)
        user = User.objects.get(email="robert@email.com")
        assert user.role == "customer"

    def test_customer_profile_has_delivery_address(self, client):
        self._post_customer(client)
        user = User.objects.get(email="robert@email.com")
        profile = user.customer_profile
        assert profile.street == "45 Park Street"
        assert profile.postcode == "BS1 5JG"

    def test_customer_can_login_after_registration(self, client):
        self._post_customer(client)
        logged_in = client.login(email="robert@email.com", password="SecurePass99")
        assert logged_in

    def test_customer_has_browsing_permissions(self, client):
        self._post_customer(client)
        user = User.objects.get(email="robert@email.com")
        assert user.is_customer

    def test_password_mismatch_rejected(self, client):
        response = client.post("/accounts/register/customer/", {
            "customer-email": "mismatch@test.com",
            "customer-phone": "0117",
            "customer-password": "Password123",
            "customer-password_confirm": "DifferentPass",
            "customer-full_name": "Test",
            "customer-street": "Test",
            "customer-city": "Test",
            "customer-state": "Test",
            "customer-postcode": "BS1",
            "customer-country": "UK",
            "customer-terms_accepted": "on",
        })
        assert not User.objects.filter(email="mismatch@test.com").exists()


# ======================================================================
# TC-017 — Community group registration
# ======================================================================

@pytest.mark.django_db
class TestTC017_CommunityGroupRegistration:

    def test_register_page_accessible(self, client):
        response = client.get("/accounts/register/")
        assert response.status_code == 200

    def test_community_group_url_exists(self, client):
        """GET redirects to register page (POST-only endpoint)."""
        response = client.get("/accounts/register/community/")
        assert response.status_code == 302

    def test_community_group_role_exists(self):
        assert "community_group" in [c[0] for c in User.Role.choices]

    def test_community_group_profile_model(self):
        """CommunityGroupProfile model has expected fields."""
        field_names = [f.name for f in CommunityGroupProfile._meta.get_fields()]
        assert "organisation_name" in field_names
        assert "organisation_type" in field_names
        assert "postcode" in field_names