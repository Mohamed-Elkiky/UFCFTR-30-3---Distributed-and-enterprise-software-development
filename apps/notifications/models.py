# apps/notifications/models.py

import uuid

from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        ORDER_STATUS = "order_status", "Order status"
        LOW_STOCK = "low_stock", "Low stock"
        SURPLUS_DEAL = "surplus_deal", "Surplus deal"
        RECURRING_ORDER = "recurring_order", "Recurring order"
        SYSTEM = "system", "System"

    class Channel(models.TextChoices):
        IN_APP = "in_app", "In-app"
        EMAIL = "email", "Email"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="app_notifications",
        related_query_name="app_notification",
    )

    type = models.CharField(max_length=30, choices=Type.choices)
    channel = models.CharField(max_length=20, choices=Channel.choices)

    title = models.CharField(max_length=255)
    body = models.TextField()

    data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.type} ({self.channel}) -> {self.user}"