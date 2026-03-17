# apps/notifications/views.py

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

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


@login_required
def mark_all_read(request):
    """Mark all notifications as read for the logged-in user."""
    if request.method == "POST":
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect("notifications:notification_list")