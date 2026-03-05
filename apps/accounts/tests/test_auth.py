import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brfn.settings")

import pytest
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from tests.factories import (
    CustomerProfileFactory,
    ProducerOrderFactory,
    ProducerProfileFactory,
    UserFactory,
)


@pytest.mark.django_db
def test_weak_password_rejected():
    with pytest.raises(ValidationError):
        validate_password("short")


@pytest.mark.django_db
def test_login_wrong_password_no_user_reveal(client):
    user = UserFactory()
    response = client.post(
        "/accounts/login/",
        {"username": user.email, "password": "wrongpassword"},
    )
    content = response.content.decode()
    assert "No account found" not in content
    assert "does not exist" not in content
    assert "no user" not in content.lower()


@pytest.mark.django_db
def test_customer_cannot_access_producer_route(client):
    customer = UserFactory(role="customer")
    client.login(email=customer.email, password="password123")
    response = client.get("/products/new/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_producer_cannot_access_other_producers_order(client):
    profile_a = ProducerProfileFactory()
    profile_b = ProducerProfileFactory()
    order = ProducerOrderFactory(producer=profile_a)

    client.login(email=profile_b.user.email, password="password123")
    response = client.get(f"/orders/producer/{order.id}/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_session_destroyed_on_logout(client):
    user = UserFactory(role="producer")
    ProducerProfileFactory(user=user)
    client.login(email=user.email, password="password123")

    response = client.get("/orders/producer/")
    assert response.status_code == 200

    client.post("/accounts/logout/")

    response = client.get("/orders/producer/")
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]
