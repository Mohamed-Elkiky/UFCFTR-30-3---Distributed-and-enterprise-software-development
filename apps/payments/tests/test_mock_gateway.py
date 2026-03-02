"""
Tests for TC-007: Mock payment gateway.
"""
import datetime

from django.test import TestCase

from apps.accounts.models import CustomerProfile, User
from apps.orders.models import CustomerOrder
from apps.payments.gateways.mock import MockGateway
from apps.payments.models import PaymentTransaction


def make_order():
    user = User.objects.create_user(email="buyer@example.com", password="pw")
    profile = CustomerProfile.objects.create(
        user=user,
        full_name="Test Buyer",
        street="1 Test St",
        city="Bristol",
        state="England",
        postcode="BS1 1AA",
        country="UK",
    )
    return CustomerOrder.objects.create(
        customer=profile,
        delivery_address="1 Test St, Bristol",
        delivery_postcode="BS1 1AA",
        delivery_date=datetime.date(2026, 4, 1),
        total_pence=1000,
    )


class MockGatewayInitiateTests(TestCase):
    def setUp(self):
        self.order = make_order()
        self.gw = MockGateway()

    def test_returns_authorised_status(self):
        result = self.gw.initiate(1000, self.order.id)
        self.assertEqual(result["status"], "authorised")

    def test_ref_has_mock_prefix(self):
        result = self.gw.initiate(1000, self.order.id)
        self.assertTrue(result["ref"].startswith("MOCK-"))

    def test_creates_pending_transaction(self):
        result = self.gw.initiate(1000, self.order.id)
        tx = PaymentTransaction.objects.get(external_reference=result["ref"])
        self.assertEqual(tx.status, PaymentTransaction.Status.PENDING)
        self.assertEqual(tx.amount_pence, 1000)
        self.assertEqual(tx.payment_method, PaymentTransaction.PaymentMethod.MOCK)


class MockGatewayCaptureTests(TestCase):
    def setUp(self):
        self.order = make_order()
        self.gw = MockGateway()
        self.ref = self.gw.initiate(1000, self.order.id)["ref"]

    def test_returns_captured_status(self):
        result = self.gw.capture(self.ref)
        self.assertEqual(result["status"], "captured")

    def test_updates_transaction_to_completed(self):
        self.gw.capture(self.ref)
        tx = PaymentTransaction.objects.get(external_reference=self.ref)
        self.assertEqual(tx.status, PaymentTransaction.Status.COMPLETED)
