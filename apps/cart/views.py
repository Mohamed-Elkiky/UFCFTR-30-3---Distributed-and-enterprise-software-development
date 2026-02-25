from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.cart.services.pricing import (
    add_to_cart,
    get_cart_total_pence,
    get_or_create_cart,
    group_cart_by_producer,
    remove_from_cart,
    update_quantity,
)
from apps.marketplace.models import Product


@login_required
def cart_detail(request):
    """GET — display the shopping-cart page."""
    if not hasattr(request.user, 'customer_profile'):
        return redirect('accounts:dashboard')

    cart = get_or_create_cart(request.user)
    grouped = group_cart_by_producer(cart)
    total_pence = get_cart_total_pence(cart)

    return render(request, "cart/cart_detail.html", {
        "cart": cart,
        "grouped": grouped,
        "total_pence": total_pence,
    })


@login_required
@require_POST
def add_to_cart_view(request, product_id):
    """POST — add a product to the cart, then redirect back."""
    if not hasattr(request.user, 'customer_profile'):
        return redirect('accounts:dashboard')

    cart = get_or_create_cart(request.user)
    product = get_object_or_404(Product, pk=product_id)
    quantity = int(request.POST.get("quantity", 1))
    add_to_cart(cart, product, quantity)
    return redirect(request.META.get("HTTP_REFERER", "cart:cart_detail"))


@login_required
@require_POST
def remove_from_cart_view(request, product_id):
    """POST — remove a product from the cart, then redirect to cart."""
    if not hasattr(request.user, 'customer_profile'):
        return redirect('accounts:dashboard')

    cart = get_or_create_cart(request.user)
    product = get_object_or_404(Product, pk=product_id)
    remove_from_cart(cart, product)
    return redirect("cart:cart_detail")


@login_required
@require_POST
def update_cart_view(request, product_id):
    """POST — update the quantity of a product in the cart."""
    if not hasattr(request.user, 'customer_profile'):
        return redirect('accounts:dashboard')

    cart = get_or_create_cart(request.user)
    product = get_object_or_404(Product, pk=product_id)
    quantity = int(request.POST.get("quantity", 1))
    update_quantity(cart, product, quantity)
    return redirect("cart:cart_detail")