from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("producer/", views.producer_orders, name="producer_orders"),
    path("producer/<uuid:order_id>/", views.producer_order_detail, name="producer_order_detail"),
    path(
        "producer/<uuid:order_id>/status/",
        views.update_producer_order_status,
        name="update_producer_order_status",
    ),

    path("customer/", views.customer_orders, name="customer_orders"),
    path("customer/<uuid:order_id>/", views.customer_order_detail, name="customer_order_detail"),
    path("customer/<uuid:order_id>/reorder/", views.reorder, name="reorder"),
]
