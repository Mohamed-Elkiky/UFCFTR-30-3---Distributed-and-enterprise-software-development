# apps/orders/views.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from apps.common.permissions import producer_required
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