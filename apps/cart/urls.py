from django.urls import path

from apps.cart import views

app_name = "cart"

urlpatterns = [
    path("", views.cart_detail, name="cart_detail"),
    path("add/<uuid:product_id>/", views.add_to_cart_view, name="cart_add"),
    path("remove/<uuid:product_id>/", views.remove_from_cart_view, name="cart_remove"),
    path("update/<uuid:product_id>/", views.update_cart_view, name="cart_update"),
]