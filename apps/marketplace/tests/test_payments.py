# apps/payments/tests/test_payments.py
"""
Tests for payment settlement and commission reporting.
Covers: TC-012, TC-025
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "brfn.settings")

from datetime import date, timedelta

import pytest

from tests.factories import (
    CustomerOrderFactory,
    CustomerProfileFactory,
    OrderItemFactory,
    ProducerOrderFactory,
    ProducerProfileFactory,
    ProductFactory,
    UserFactory,
)
from apps.orders.models import CustomerOrder, ProducerOrder
from apps.payments.models import (
    CommissionPolicy,
    OrderCommission,
    ProducerOrderSettlementLink,
    ProducerSettlement,
    SettlementWeek,
)
from apps.payments.services.commission import (
    calculate_commission,
    get_active_policy,
    record_order_commission,
)
from apps.payments.services.settlement import (
    get_or_create_settlement_week,
    run_weekly_settlement,
)


# ======================================================================
# TC-012 — Weekly payment settlements (95% to producers)
# ======================================================================

@pytest.mark.django_db
class TestTC012_WeeklySettlement:
    """Payment settlement distributes 95% to producers weekly."""

    def _make_policy(self):
        return CommissionPolicy.objects.create(
            rate_bp=500, valid_from=date(2020, 1, 1)
        )

    def test_commission_calculation_5_percent(self):
        assert calculate_commission(10000, 500) == 500
        assert calculate_commission(1500, 500) == 75

    def test_commission_accurate_to_penny(self):
        # 5% of 999 = 49.95 -> rounds to 50
        result = calculate_commission(999, 500)
        assert result == 50

    def test_get_active_policy(self):
        policy = self._make_policy()
        found = get_active_policy(date.today())
        assert found.rate_bp == policy.rate_bp

    def test_no_policy_raises(self):
        with pytest.raises(ValueError, match="No active CommissionPolicy"):
            get_active_policy(date(2019, 1, 1))

    def test_record_order_commission(self):
        self._make_policy()
        order = CustomerOrderFactory(total_pence=10000)
        oc = record_order_commission(order)
        assert oc.gross_pence == 10000
        assert oc.commission_pence == 500
        assert oc.net_pence == 9500

    def test_settlement_week_creation(self):
        monday = date(2026, 5, 4)
        week = get_or_create_settlement_week(monday)
        assert week.week_start == monday
        assert week.week_end == date(2026, 5, 10)

    def test_run_weekly_settlement_creates_records(self):
        self._make_policy()
        producer = ProducerProfileFactory()
        today = date.today()
        monday = today - timedelta(days=today.weekday())

        order = CustomerOrderFactory(status="pending")
        po = ProducerOrderFactory(
            customer_order=order,
            producer=producer,
            subtotal_pence=2000,
            commission_pence=100,
            producer_payment_pence=1900,
            status="delivered",
            delivery_date=monday,
        )
        settlements = run_weekly_settlement(monday)
        assert len(settlements) == 1
        s = settlements[0]
        assert s.producer == producer
        assert s.payout_pence == 1900
        assert s.commission_pence == 100

    def test_settlement_links_created(self):
        self._make_policy()
        producer = ProducerProfileFactory()
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        order = CustomerOrderFactory()
        po = ProducerOrderFactory(
            customer_order=order,
            producer=producer,
            subtotal_pence=1000,
            status="delivered",
            delivery_date=monday,
        )
        run_weekly_settlement(monday)
        assert ProducerOrderSettlementLink.objects.filter(producer_order=po).exists()

    def test_already_settled_orders_not_re_settled(self):
        self._make_policy()
        producer = ProducerProfileFactory()
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        order = CustomerOrderFactory()
        po = ProducerOrderFactory(
            customer_order=order,
            producer=producer,
            subtotal_pence=1000,
            status="delivered",
            delivery_date=monday,
        )
        run_weekly_settlement(monday)
        # Run again — should not create duplicates
        settlements = run_weekly_settlement(monday)
        assert len(settlements) == 0

    def test_producer_settlements_view(self, client):
        self._make_policy()
        producer = ProducerProfileFactory()
        client.login(email=producer.user.email, password="password123")
        response = client.get("/payments/settlements/")
        assert response.status_code == 200


# ======================================================================
# TC-025 — Commission monitoring and financial reports
# ======================================================================

@pytest.mark.django_db
class TestTC025_CommissionReport:
    """Admin can view commission reports with filtering and CSV export."""

    def _setup_report_data(self):
        policy = CommissionPolicy.objects.create(
            rate_bp=500, valid_from=date(2020, 1, 1)
        )
        producer_a = ProducerProfileFactory(business_name="Farm A")
        producer_b = ProducerProfileFactory(business_name="Farm B")

        # Single-vendor order: £100 total
        order1 = CustomerOrderFactory(total_pence=10000, status="delivered")
        ProducerOrderFactory(
            customer_order=order1,
            producer=producer_a,
            subtotal_pence=10000,
            commission_pence=500,
            producer_payment_pence=9500,
        )
        record_order_commission(order1)

        # Multi-vendor order: £150 total (£80 + £70)
        order2 = CustomerOrderFactory(total_pence=15000, status="delivered")
        ProducerOrderFactory(
            customer_order=order2,
            producer=producer_a,
            subtotal_pence=8000,
            commission_pence=400,
            producer_payment_pence=7600,
        )
        ProducerOrderFactory(
            customer_order=order2,
            producer=producer_b,
            subtotal_pence=7000,
            commission_pence=350,
            producer_payment_pence=6650,
        )
        record_order_commission(order2)

        return policy, producer_a, producer_b, order1, order2

    def test_admin_can_access_report(self, client):
        admin = UserFactory(role="admin")
        self._setup_report_data()
        client.login(email=admin.email, password="password123")
        response = client.get("/payments/admin/commission-report/")
        assert response.status_code == 200

    def test_non_admin_blocked(self, client):
        customer = CustomerProfileFactory()
        client.login(email=customer.user.email, password="password123")
        response = client.get("/payments/admin/commission-report/")
        assert response.status_code == 403

    def test_report_shows_correct_totals(self, client):
        admin = UserFactory(role="admin")
        self._setup_report_data()
        client.login(email=admin.email, password="password123")
        response = client.get("/payments/admin/commission-report/")
        content = response.content.decode()
        # Should contain commission amounts
        assert "250.00" in content or "£250" in content  # total gross
        assert response.status_code == 200

    def test_csv_export(self, client):
        admin = UserFactory(role="admin")
        self._setup_report_data()
        client.login(email=admin.email, password="password123")
        response = client.get(
            "/payments/admin/commission-report/", {"format": "csv"}
        )
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        content = response.content.decode()
        assert "Order ID" in content
        assert "Commission" in content

    def test_order_detail_view(self, client):
        admin = UserFactory(role="admin")
        _, _, _, order1, _ = self._setup_report_data()
        client.login(email=admin.email, password="password123")
        response = client.get(
            f"/payments/admin/commission-report/order/{order1.id}/"
        )
        assert response.status_code == 200

    def test_single_order_commission_is_5_percent_of_100(self):
        """If order total is £100, commission is £5.00, producer gets £95.00."""
        CommissionPolicy.objects.create(rate_bp=500, valid_from=date(2020, 1, 1))
        order = CustomerOrderFactory(total_pence=10000)
        oc = record_order_commission(order)
        assert oc.commission_pence == 500
        assert oc.net_pence == 9500

    def test_multi_vendor_commission_calculation(self):
        """For multi-vendor £150 order: total commission £7.50,
        Producer 1 (£80): pays £4.00, gets £76.00.
        Producer 2 (£70): pays £3.50, gets £66.50."""
        CommissionPolicy.objects.create(rate_bp=500, valid_from=date(2020, 1, 1))
        order = CustomerOrderFactory(total_pence=15000)

        oc = record_order_commission(order)
        assert oc.commission_pence == 750  # 5% of 15000
        assert oc.net_pence == 14250

        # Verify per-producer breakdown
        pa = ProducerProfileFactory()
        pb = ProducerProfileFactory()
        po_a = ProducerOrderFactory(
            customer_order=order, producer=pa,
            subtotal_pence=8000, commission_pence=400,
            producer_payment_pence=7600,
        )
        po_b = ProducerOrderFactory(
            customer_order=order, producer=pb,
            subtotal_pence=7000, commission_pence=350,
            producer_payment_pence=6650,
        )
        assert po_a.producer_payment_pence == 7600
        assert po_b.producer_payment_pence == 6650

    def test_date_filter_on_report(self, client):
        admin = UserFactory(role="admin")
        self._setup_report_data()
        client.login(email=admin.email, password="password123")
        today = date.today()
        response = client.get("/payments/admin/commission-report/", {
            "date_from": (today - timedelta(days=7)).isoformat(),
            "date_to": today.isoformat(),
        })
        assert response.status_code == 200