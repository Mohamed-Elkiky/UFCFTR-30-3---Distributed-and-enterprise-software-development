# apps/notifications/models.py
"""
Notification models for Bristol Regional Food Network.
Handles system notifications to users.
Related test cases: TC-010, TC-023
"""

import uuid
from django.db import models


class Notification(models.Model):
    """
    System notification to a user.
    Used for order updates, low stock alerts, etc.
    """
    
    class NotificationType(models.TextChoices):
        ORDER_PLACED = 'order_placed', 'New Order Placed'
        ORDER_STATUS = 'order_status', 'Order Status Update'
        LOW_STOCK = 'low_stock', 'Low Stock Alert'
        PAYMENT = 'payment', 'Payment Notification'
        REVIEW = 'review', 'New Review'
        SURPLUS = 'surplus', 'Surplus Deal Available'
        GENERAL = 'general', 'General Notification'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Recipient
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.GENERAL
    )
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Link to related object (optional)
    related_order_id = models.UUIDField(null=True, blank=True)
    related_product_id = models.UUIDField(null=True, blank=True)
    
    is_read = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification_type}: {self.title}"
    
    def mark_as_read(self):
        from django.utils import timezone
        self.is_read = True
        self.read_at = timezone.now()
        self.save()