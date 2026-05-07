# apps/orders/models.py
"""
Order models for Bristol Regional Food Network.
Handles customer orders, order items, and order status tracking.
Related test cases: TC-007, TC-008, TC-009, TC-010, TC-021
"""

import uuid
from django.db import models
from django.utils import timezone


class CustomerOrder(models.Model):
    """
    Main order placed by a customer.
    A single order can contain items from multiple producers (TC-008).
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        READY = 'ready', 'Ready for Collection/Delivery'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to the customer who placed the order
    customer = models.ForeignKey(
        'accounts.CustomerProfile',
        on_delete=models.SET_NULL,
        null=True,
        related_name='orders'
    )
    
    # Delivery details (snapshot at time of order)
    delivery_address = models.TextField()
    delivery_postcode = models.CharField(max_length=10)
    delivery_date = models.DateField()
    special_instructions = models.TextField(blank=True, default='')
    
    # Order totals (in pence to avoid floating point issues)
    subtotal_pence = models.IntegerField(default=0)
    commission_pence = models.IntegerField(default=0)  # 5% network commission
    total_pence = models.IntegerField(default=0)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    @property
    def short_ref(self):
        """Human-readable order reference, e.g. BRF-1A2B3C."""
        return f"BRF-{str(self.id)[:6].upper()}"

    def __str__(self):
        return f"Order {self.short_ref} - {self.status}"
    
    def calculate_totals(self):
        """Calculate order totals from items."""
        self.subtotal_pence = sum(item.line_total_pence for item in self.items.all())
        self.commission_pence = int(self.subtotal_pence * 0.05)
        self.total_pence = self.subtotal_pence
        self.save()


class ProducerOrder(models.Model):
    """
    Sub-order for a specific producer within a customer order.
    For multi-vendor orders, each producer gets their own ProducerOrder (TC-008).
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        READY = 'ready', 'Ready'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    customer_order = models.ForeignKey(
        CustomerOrder,
        on_delete=models.CASCADE,
        related_name='producer_orders'
    )
    
    producer = models.ForeignKey(
        'accounts.ProducerProfile',
        on_delete=models.SET_NULL,
        null=True,
        related_name='orders'
    )
    
    subtotal_pence = models.IntegerField(default=0)
    commission_pence = models.IntegerField(default=0)
    producer_payment_pence = models.IntegerField(default=0)
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    status_notes = models.TextField(blank=True, default='')
    delivery_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = [('customer_order', 'producer')]
    
    @property
    def short_ref(self):
        """Human-readable sub-order reference, e.g. PO-1A2B3C."""
        return f"PO-{str(self.id)[:6].upper()}"

    def __str__(self):
        producer_name = self.producer.business_name if self.producer else 'Unknown'
        return f"ProducerOrder {self.short_ref} - {producer_name}"
    
    def calculate_totals(self):
        """Calculate totals for this producer's portion."""
        self.subtotal_pence = sum(
            item.line_total_pence 
            for item in self.customer_order.items.filter(product__producer=self.producer)
        )
        self.commission_pence = int(self.subtotal_pence * 0.05)
        self.producer_payment_pence = self.subtotal_pence - self.commission_pence
        self.save()


class OrderItem(models.Model):
    """Individual item within an order."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    order = models.ForeignKey(
        CustomerOrder,
        on_delete=models.CASCADE,
        related_name='items'
    )
    
    product = models.ForeignKey(
        'marketplace.Product',
        on_delete=models.SET_NULL,
        null=True,
        related_name='order_items'
    )
    
    # Snapshot of product details at time of order
    product_name = models.CharField(max_length=255)
    product_unit = models.CharField(max_length=50)
    price_pence = models.IntegerField()
    quantity = models.PositiveIntegerField(default=1)
    line_total_pence = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        self.line_total_pence = self.price_pence * self.quantity
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.quantity}x {self.product_name}"


class OrderStatusHistory(models.Model):
    """Tracks status changes for audit trail (TC-010)."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    producer_order = models.ForeignKey(
        ProducerOrder,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    notes = models.TextField(blank=True, default='')
    changed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-changed_at']
    
    def __str__(self):
        return f"{self.old_status} → {self.new_status}"
    
# ---------------------------------------------------------------------------
# Recurring Orders (TC-018)
# ---------------------------------------------------------------------------
# Allows business customers (e.g. restaurants) to set up a repeating order
# schedule defined by an iCal RRULE string. A scheduler periodically calls
# generate_upcoming_instances() to materialise RecurringOrderInstance rows
# for upcoming dates, and place_recurring_instance() converts a scheduled
# instance into a real CustomerOrder using the template's items.


class RecurringOrderTemplate(models.Model):
    """
    A reusable order template owned by a customer.
    Defines what items to order and on what schedule (via RRULE).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    customer = models.ForeignKey(
        'accounts.CustomerProfile',
        on_delete=models.CASCADE,
        related_name='recurring_templates',
    )

    name = models.CharField(max_length=200)

    # iCal RRULE string, e.g. "FREQ=WEEKLY;BYDAY=MO"
    # Parsed at runtime with dateutil.rrule.rrulestr().
    rrule = models.TextField(
        help_text="iCal RRULE string defining the recurrence schedule"
    )

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.customer})"


class RecurringOrderItem(models.Model):
    """
    A line item within a RecurringOrderTemplate.
    Stores the product and the quantity to be ordered each occurrence.
    Composite uniqueness on (template, product) prevents duplicate lines.
    """

    template = models.ForeignKey(
        RecurringOrderTemplate,
        on_delete=models.CASCADE,
        related_name='items',
    )

    product = models.ForeignKey(
        'marketplace.Product',
        on_delete=models.CASCADE,
        related_name='recurring_order_items',
    )

    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['template', 'product'],
                name='recurring_order_item_pk',
            )
        ]

    def __str__(self):
        return f"{self.quantity}x {self.product.name} ({self.template.name})"


class RecurringOrderInstance(models.Model):
    """
    A scheduled occurrence of a RecurringOrderTemplate.
    Created by generate_upcoming_instances() ahead of time so the customer
    can preview, modify, or skip an upcoming run before it's placed.
    """

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        PLACED = 'placed', 'Placed'
        SKIPPED = 'skipped', 'Skipped'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    template = models.ForeignKey(
        RecurringOrderTemplate,
        on_delete=models.CASCADE,
        related_name='instances',
    )

    scheduled_for = models.DateField()

    # Set once the instance is converted into a real order.
    customer_order = models.ForeignKey(
        'orders.CustomerOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recurring_instance',
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
    )

    # Persistent storage for quantity overrides (replaces session-based approach)
    quantity_overrides = models.JSONField(
        default=dict,
        blank=True,
        help_text="Override quantities for this specific instance. Format: {product_id: quantity}"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['scheduled_for']
        constraints = [
            models.UniqueConstraint(
                fields=['template', 'scheduled_for'],
                name='recurring_instance_unique_per_date',
            )
        ]

    def __str__(self):
        return f"{self.template.name} on {self.scheduled_for} ({self.status})"