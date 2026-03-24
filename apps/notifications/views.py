# apps/notifications/views.py

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.notifications.models import Notification


@login_required
def notification_list(request):
    """Show all notifications for the logged-in user."""
    all_notifications = Notification.objects.filter(user=request.user)
    unread_count = all_notifications.filter(is_read=False).count()
    notifications = all_notifications.order_by("-created_at")[:50]

    return render(request, "notifications/notification_list.html", {
        "notifications": notifications,
        "unread_count": unread_count,
    })


@require_POST
@login_required
def mark_all_read(request):
    """Mark all notifications as read for the logged-in user."""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect("notifications:notification_list")


@require_POST
@login_required
def mark_read(request, notification_id):
    """Mark a single notification as read."""
    notification = get_object_or_404(Notification, pk=notification_id, user=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    return redirect("notifications:notification_list")


@require_POST
@login_required
def dismiss(request, notification_id):
    """Delete a single notification entirely."""
    notification = get_object_or_404(Notification, pk=notification_id, user=request.user)
    notification.delete()
    return redirect("notifications:notification_list")