# apps/cart/views.py

from datetime import date

from django.contrib import messages
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
from apps.orders.models import CustomerOrder
from apps.orders.services.lead_time import (
    get_earliest_delivery_date,
    validate_delivery_date,
)
from apps.orders.services.create_order import create_orders_from_cart


def _customer_required(request):
    """Return True if user has a customer profile, else False."""
    return hasattr(request.user, "customer_profile")


@login_required
def cart_detail(request):
    """GET — display the shopping-cart page."""
    if not _customer_required(request):
        return redirect("accounts:dashboard")

    cart = get_or_create_cart(request.user)
    grouped = group_cart_by_producer(cart)
    total_pence = get_cart_total_pence(cart)

    return render(
        request,
        "cart/cart_detail.html",
        {
            "cart": cart,
            "grouped": grouped,
            "total_pence": total_pence,
        },
    )


@login_required
@require_POST
def add_to_cart_view(request, product_id):
    """POST — add a product to the cart, then redirect back."""
    if not _customer_required(request):
        return redirect("accounts:dashboard")

    cart = get_or_create_cart(request.user)
    product = get_object_or_404(Product, pk=product_id)
    quantity = int(request.POST.get("quantity", 1))
    add_to_cart(cart, product, quantity)
    return redirect(request.META.get("HTTP_REFERER", "cart:cart_detail"))


@login_required
@require_POST
def remove_from_cart_view(request, product_id):
    """POST — remove a product from the cart, then redirect to cart."""
    if not _customer_required(request):
        return redirect("accounts:dashboard")

    cart = get_or_create_cart(request.user)
    product = get_object_or_404(Product, pk=product_id)
    remove_from_cart(cart, product)
    return redirect("cart:cart_detail")


@login_required
@require_POST
def update_cart_view(request, product_id):
    """POST — update the quantity of a product in the cart."""
    if not _customer_required(request):
        return redirect("accounts:dashboard")

    cart = get_or_create_cart(request.user)
    product = get_object_or_404(Product, pk=product_id)
    quantity = int(request.POST.get("quantity", 1))
    update_quantity(cart, product, quantity)
    return redirect("cart:cart_detail")


@login_required
def checkout(request):
    """
    GET: Show checkout page with cart grouped by producer and min delivery dates.
    POST: Validate delivery dates, create orders, redirect to confirmation.
    TC-007 (single vendor), TC-008 (multi-vendor).
    """
    if not _customer_required(request):
        messages.error(request, "You need a customer account to checkout.")
        return redirect("accounts:dashboard")

    cart = get_or_create_cart(request.user)
    grouped = group_cart_by_producer(cart)

    if not grouped:
        messages.warning(request, "Your cart is empty.")
        return redirect("cart:cart_detail")

    earliest_delivery = get_earliest_delivery_date()

    if request.method == "POST":
        special_instructions = request.POST.get("special_instructions", "")

        # Collect and validate per-producer delivery dates
        delivery_dates_by_producer = {}
        errors = []

        for producer in grouped.keys():
            field_name = (
                f"delivery_date_{producer.pk}"
                if producer
                else "delivery_date_default"
            )
            raw_date = request.POST.get(field_name) or request.POST.get(
                "delivery_date"
            )

            producer_name = (
                producer.business_name if producer else "your order"
            )

            if not raw_date:
                errors.append(
                    f"Please select a delivery date for {producer_name}."
                )
                continue

            try:
                parsed = date.fromisoformat(raw_date)
            except ValueError:
                errors.append(
                    f"Invalid delivery date for {producer_name}."
                )
                continue

            if not validate_delivery_date(parsed):
                errors.append(
                    f"Delivery date for {producer_name} must be at least 48 hours "
                    f"from now (earliest: {earliest_delivery})."
                )
                continue

            if producer:
                delivery_dates_by_producer[str(producer.pk)] = parsed

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            main_delivery_date = (
                list(delivery_dates_by_producer.values())[0]
                if delivery_dates_by_producer
                else earliest_delivery
            )

            try:
                customer_order = create_orders_from_cart(
                    cart=cart,
                    customer_profile=request.user.customer_profile,
                    delivery_date=main_delivery_date,
                    delivery_dates_by_producer=delivery_dates_by_producer,
                    special_instructions=special_instructions,
                )
                messages.success(
                    request,
                    "Your order has been placed successfully!",
                )
                return redirect(
                    "cart:order_confirmed",
                    order_id=customer_order.pk,
                )
            except Exception as e:
                messages.error(
                    request,
                    f"There was a problem placing your order: {e}",
                )

    grouped_with_dates = {
        producer: {
            "items": items,
            "earliest_delivery": earliest_delivery.isoformat(),
            "subtotal_pence": sum(
                i.product.price_pence * i.quantity for i in items
            ),
        }
        for producer, items in grouped.items()
    }

    total_pence = get_cart_total_pence(cart)
    commission_pence = int(total_pence * 0.05)

    return render(
        request,
        "cart/checkout_multivendor.html",
        {
            "grouped": grouped_with_dates,
            "total_pence": total_pence,
            "commission_pence": commission_pence,
            "earliest_delivery": earliest_delivery.isoformat(),
            "customer_profile": request.user.customer_profile,
        },
    )


@login_required
def order_confirmed(request, order_id):
    """
    GET: Show order confirmation page.
    TC-007, TC-008.
    """
    if not _customer_required(request):
        return redirect("accounts:dashboard")

    order = get_object_or_404(CustomerOrder, id=order_id)

    if order.customer != request.user.customer_profile:
        messages.error(
            request,
            "You do not have permission to view this order.",
        )
        return redirect("marketplace:home")

    producer_orders = order.producer_orders.select_related("producer").all()
    items = order.items.select_related("product").all()

    return render(
        request,
        "cart/order_confirmed.html",
        {
            "order": order,
            "producer_orders": producer_orders,
            "items": items,
        },
    )