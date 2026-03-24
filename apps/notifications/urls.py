from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_list, name="notification_list"),
    path("mark-all-read/", views.mark_all_read, name="mark_all_read"),
    path("<uuid:notification_id>/read/", views.mark_read, name="mark_read"),
    path("<uuid:notification_id>/dismiss/", views.dismiss, name="dismiss"),
]