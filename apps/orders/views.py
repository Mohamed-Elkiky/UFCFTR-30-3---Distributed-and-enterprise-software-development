# apps/orders/views.py

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from apps.common.permissions import producer_required
from apps.orders.models import ProducerOrder


@login_required
@producer_required
def producer_orders(request):
    """
    Producer dashboard list view (TC-009).
    Shows all ProducerOrders for the logged-in producer, ordered by delivery_date.
    """
    orders = (
        ProducerOrder.objects
        .filter(producer=request.user.producer_profile)
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
    producer_order = get_object_or_404(
        ProducerOrder,
        id=order_id,
        producer=request.user.producer_profile,
    )

    return render(
        request,
        "producer/order_detail.html",
        {"producer_order": producer_order},
    )