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
    
    def __str__(self):
        return f"Order {self.id} - {self.status}"
    
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
    
    def __str__(self):
        producer_name = self.producer.business_name if self.producer else 'Unknown'
        return f"ProducerOrder {self.id} - {producer_name}"
    
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