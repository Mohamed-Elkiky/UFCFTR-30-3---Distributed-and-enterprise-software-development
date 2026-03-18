# apps/orders/views.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.common.permissions import producer_required
from apps.cart.services.pricing import add_to_cart, get_or_create_cart
from apps.orders.models import CustomerOrder, ProducerOrder
from apps.orders.services.status_flow import transition_producer_order


@login_required
@producer_required
def producer_orders(request):
    """
    Producer dashboard list view (TC-009).
    Shows all ProducerOrders for the logged-in producer, ordered by delivery_date.
    """
    producer_profile = getattr(request.user, "producer_profile", None)
    if producer_profile is None:
        return HttpResponseForbidden("Producer profile required.")

    orders = (
        ProducerOrder.objects
        .filter(producer=producer_profile)
        .order_by("delivery_date")
    )

    return render(request, "producer/orders.html", {"orders": orders})


@login_required
@producer_required
def producer_order_detail(request, order_id):
    """
    Producer order detail view (TC-009).
    Only allows access to orders owned by the logged-in producer.
    """
    producer_profile = getattr(request.user, "producer_profile", None)
    if producer_profile is None:
        return HttpResponseForbidden("Producer profile required.")

    producer_order = get_object_or_404(
        ProducerOrder,
        id=order_id,
        producer=producer_profile,
    )

    return render(
        request,
        "producer/order_detail.html",
        {"producer_order": producer_order},
    )


@login_required
@producer_required
def update_producer_order_status(request, order_id):
    """
    Producer updates a ProducerOrder status (TC-010).
    POST only. Reads new_status from POST and uses transition_producer_order().
    On ValueError: show error + redirect back.
    On success: redirect to producer_order_detail.
    """
    if request.method != "POST":
        return HttpResponseForbidden("POST only")

    producer_profile = getattr(request.user, "producer_profile", None)
    if producer_profile is None:
        return HttpResponseForbidden("Producer profile required.")

    producer_order = get_object_or_404(
        ProducerOrder,
        id=order_id,
        producer=producer_profile,
    )

    new_status = (request.POST.get("new_status") or "").strip().lower()
    if not new_status:
        messages.error(request, "Please select a new status.")
        return redirect("orders:producer_order_detail", order_id=producer_order.id)

    try:
        transition_producer_order(
            producer_order=producer_order,
            new_status=new_status,
            actor_user=request.user,
        )
    except ValueError as e:
        messages.error(request, str(e))
        return redirect(
            request.META.get("HTTP_REFERER") or "orders:producer_order_detail",
            order_id=producer_order.id,
        )

    messages.success(request, f"Order status updated to '{new_status}'.")
    return redirect("orders:producer_order_detail", order_id=producer_order.id)


@login_required
def customer_orders(request):
    """
    Customer order history list view.
    Shows all CustomerOrders for the logged-in customer.
    """
    if not hasattr(request.user, "customer_profile"):
        messages.error(request, "You need a customer account to view orders.")
        return redirect("accounts:dashboard")

    orders = (
        CustomerOrder.objects
        .filter(customer=request.user.customer_profile)
        .prefetch_related("producer_orders__producer")
        .order_by("-created_at")
    )

    return render(request, "orders/customer_orders.html", {"orders": orders})


@login_required
def customer_order_detail(request, order_id):
    """
    Customer order detail view.
    Only allows access to orders belonging to the logged-in customer.
    """
    if not hasattr(request.user, "customer_profile"):
        messages.error(request, "You need a customer account to view orders.")
        return redirect("accounts:dashboard")

    order = get_object_or_404(
        CustomerOrder,
        id=order_id,
        customer=request.user.customer_profile,
    )
    payment = getattr(order, "payment", None)

    return render(
        request,
        "orders/customer_order_detail.html",
        {
            "order": order,
            "payment": payment,
        },
    )


@login_required
@require_POST
def reorder(request, order_id):
    """
    Reorder view (TC-021).
    POST only. Fetches original OrderItem rows from a previous order,
    calls add_to_cart for each item checking current product.availability
    != 'unavailable'. For unavailable items, adds a warning message.
    Redirects to cart_detail.
    """
    if not hasattr(request.user, "customer_profile"):
        messages.error(request, "You need a customer account to reorder.")
        return redirect("accounts:dashboard")

    order = get_object_or_404(
        CustomerOrder,
        id=order_id,
        customer=request.user.customer_profile,
    )

    cart = get_or_create_cart(request.user)
    items = order.items.select_related("product").all()

    added = 0
    unavailable = []

    for item in items:
        product = item.product
        if product is None:
            unavailable.append(item.product_name)
            continue

        if product.availability == "unavailable":
            unavailable.append(product.name)
            continue

        add_to_cart(cart, product, item.quantity)
        added += 1

    if added:
        messages.success(request, f"{added} item(s) added to your cart.")

    if unavailable:
        names = ", ".join(unavailable)
        messages.warning(
            request,
            f"Some items are currently unavailable and were skipped: {names}",
        )

    return redirect("cart:cart_detail")