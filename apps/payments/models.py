# apps/payments/models.py
"""
Payment models for Bristol Regional Food Network.
Handles payment transactions, commission tracking, and weekly settlements.
Related test cases: TC-012, TC-025
"""

import uuid
from django.db import models
from django.utils import timezone


class PaymentTransaction(models.Model):
    """
    Records individual payment transactions for orders.
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        REFUNDED = 'refunded', 'Refunded'
    
    class PaymentMethod(models.TextChoices):
        CARD = 'card', 'Card'
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        MOCK = 'mock', 'Mock Payment (Testing)'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to the order
    order = models.OneToOneField(
        'orders.CustomerOrder',
        on_delete=models.CASCADE,
        related_name='payment'
    )
    
    amount_pence = models.IntegerField()  # Total amount paid
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.MOCK
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # External payment reference (e.g., Stripe payment intent ID)
    external_reference = models.CharField(max_length=255, blank=True, default='')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Payment {self.id} - £{self.amount_pence/100:.2f}"


class ProducerSettlement(models.Model):
    """
    Weekly payment settlement to a producer (TC-012).
    Aggregates all completed orders for a week and calculates the payout.
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSED = 'processed', 'Processed'
        PAID = 'paid', 'Paid'
        FAILED = 'failed', 'Failed'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    producer = models.ForeignKey(
        'accounts.ProducerProfile',
        on_delete=models.CASCADE,
        related_name='settlements'
    )
    
    # Settlement period (week)
    week_start = models.DateField()
    week_end = models.DateField()
    
    # Financial summary
    total_order_value_pence = models.IntegerField(default=0)  # Gross sales
    commission_pence = models.IntegerField(default=0)  # 5% to network
    settlement_amount_pence = models.IntegerField(default=0)  # 95% to producer
    
    order_count = models.IntegerField(default=0)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Bank transfer reference
    payment_reference = models.CharField(max_length=255, blank=True, default='')
    
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-week_start']
        unique_together = ['producer', 'week_start']
    
    def __str__(self):
        return f"Settlement {self.producer} - {self.week_start}"


class CommissionRecord(models.Model):
    """
    Individual commission record for audit trail (TC-025).
    One record per producer order.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    producer_order = models.OneToOneField(
        'orders.ProducerOrder',
        on_delete=models.CASCADE,
        related_name='commission_record'
    )
    
    order_value_pence = models.IntegerField()  # Value of producer's items
    commission_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=4, 
        default=0.05  # 5%
    )
    commission_pence = models.IntegerField()  # Calculated commission
    producer_payout_pence = models.IntegerField()  # Amount due to producer
    
    # Link to settlement (null until settled)
    settlement = models.ForeignKey(
        ProducerSettlement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commission_records'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Commission {self.id} - £{self.commission_pence/100:.2f}"