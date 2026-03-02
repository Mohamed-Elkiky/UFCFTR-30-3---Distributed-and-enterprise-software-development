# apps/payments/models.py
"""
Payment models for Bristol Regional Food Network.
TC-007: PaymentTransaction, CommissionPolicy, OrderCommission
TC-012: SettlementWeek, ProducerSettlement, ProducerOrderSettlementLink
"""

import uuid
from django.db import models


class PaymentTransaction(models.Model):
    """Records a single payment attempt against a customer order (TC-007)."""

    class Status(models.TextChoices):
        INITIATED = 'initiated', 'Initiated'
        AUTHORISED = 'authorised', 'Authorised'
        CAPTURED = 'captured', 'Captured'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_order = models.OneToOneField(
        'orders.CustomerOrder',
        on_delete=models.CASCADE,
        related_name='payment',
    )
    provider = models.CharField(max_length=50)          # e.g. 'mock', 'stripe'
    provider_ref = models.CharField(max_length=255)     # gateway's transaction ref
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.INITIATED,
    )
    amount_pence = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PaymentTransaction {self.provider_ref} ({self.status})"


class CommissionPolicy(models.Model):
    """Defines the commission rate in basis points for a date range (TC-007)."""

    rate_bp = models.IntegerField(help_text="Rate in basis points; 500 = 5%")
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-valid_from']
        verbose_name_plural = 'Commission policies'

    def __str__(self):
        return f"{self.rate_bp}bp from {self.valid_from}"


class OrderCommission(models.Model):
    """Commission record for a single customer order (TC-007)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_order = models.OneToOneField(
        'orders.CustomerOrder',
        on_delete=models.CASCADE,
        related_name='commission',
    )
    commission_policy = models.ForeignKey(
        CommissionPolicy,
        on_delete=models.PROTECT,
        related_name='order_commissions',
    )
    gross_pence = models.IntegerField()
    commission_pence = models.IntegerField()
    net_pence = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Commission on order {self.customer_order_id}: {self.commission_pence}p"


class SettlementWeek(models.Model):
    """Represents a weekly settlement period (TC-012)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    week_start = models.DateField(unique=True)
    week_end = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-week_start']

    def __str__(self):
        return f"Week {self.week_start} – {self.week_end}"


class ProducerSettlement(models.Model):
    """Payout record for one producer within a settlement week (TC-012)."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSED = 'processed', 'Processed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    settlement_week = models.ForeignKey(
        SettlementWeek,
        on_delete=models.CASCADE,
        related_name='producer_settlements',
    )
    producer = models.ForeignKey(
        'accounts.ProducerProfile',
        on_delete=models.CASCADE,
        related_name='settlements',
    )
    commission_pence = models.IntegerField(default=0)
    payout_pence = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    processed_ref = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [('settlement_week', 'producer')]

    def __str__(self):
        return f"Settlement {self.producer} / {self.settlement_week}"


class ProducerOrderSettlementLink(models.Model):
    """Links a ProducerOrder to the ProducerSettlement it was included in (TC-012)."""

    producer_order = models.OneToOneField(
        'orders.ProducerOrder',
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='settlement_link',
    )
    producer_settlement = models.ForeignKey(
        ProducerSettlement,
        on_delete=models.CASCADE,
        related_name='order_links',
    )

    def __str__(self):
        return f"ProducerOrder {self.producer_order_id} → Settlement {self.producer_settlement_id}"
