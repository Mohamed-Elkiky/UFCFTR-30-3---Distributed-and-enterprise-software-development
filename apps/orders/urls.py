from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("producer/orders/", views.producer_orders, name="producer_orders"),
    path("producer/orders/<uuid:order_id>/", views.producer_order_detail, name="producer_order_detail"),
]