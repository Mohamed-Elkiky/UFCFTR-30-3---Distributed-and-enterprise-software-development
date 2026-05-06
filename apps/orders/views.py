# apps/orders/views.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.common.permissions import producer_required, customer_required
from apps.cart.services.pricing import add_to_cart, get_or_create_cart
from apps.marketplace.models import Product
from apps.orders.models import (
    CustomerOrder,
    ProducerOrder,
    RecurringOrderTemplate,
    RecurringOrderInstance,
)
from apps.orders.services.status_flow import transition_producer_order
from apps.orders.services.recurring import create_recurring_template


def _get_buyer_profile(user):
    """Return a CustomerProfile for customer or community_group users."""
    if hasattr(user, "customer_profile"):
        return user.customer_profile

    from apps.accounts.models import CustomerProfile

    cg = getattr(user, "community_group_profile", None)
    if cg is None:
        return None

    profile, _ = CustomerProfile.objects.get_or_create(
        user=user,
        defaults={
            "full_name": cg.organisation_name,
            "street": cg.delivery_address,
            "city": "",
            "state": "",
            "postcode": cg.postcode,
            "country": "UK",
        },
    )
    return profile


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


# ---------------------------------------------------------------------------
# Recurring Orders (TC-018)
# ---------------------------------------------------------------------------


@login_required
@customer_required
def recurring_orders(request):
    """
    List all RecurringOrderTemplate for the logged-in customer (TC-018).
    Shows all recurring order templates the customer has created.
    """
    buyer_profile = _get_buyer_profile(request.user)
    if buyer_profile is None:
        return HttpResponseForbidden("Buyer profile required.")

    templates = (
        RecurringOrderTemplate.objects
        .filter(customer=buyer_profile)
        .prefetch_related('items__product')
        .order_by('-created_at')
    )

    return render(
        request,
        "customer/recurring_orders.html",
        {"templates": templates},
    )


@login_required
@customer_required
@require_POST
def create_recurring_order(request):
    """
    Create a new RecurringOrderTemplate from form data (TC-018).
    POST only. Reads template name, rrule, and product/quantity pairs.
    Calls create_recurring_template and redirects to recurring_orders list.
    """
    buyer_profile = _get_buyer_profile(request.user)
    if buyer_profile is None:
        return HttpResponseForbidden("Buyer profile required.")

    template_name = (request.POST.get("name") or "").strip()
    rrule = (request.POST.get("rrule") or "").strip()

    if not template_name:
        messages.error(request, "Please provide a template name.")
        return redirect("orders:recurring_orders")

    if not rrule:
        messages.error(request, "Please provide a recurrence rule (RRULE).")
        return redirect("orders:recurring_orders")

    # Collect product/quantity pairs from POST data.
    # Expected format: product_id_1=qty_1, product_id_2=qty_2, etc.
    items = []
    for key in request.POST:
        if key.startswith("product_"):
            product_id = key.split("_", 1)[1]
            qty_str = request.POST.get(key, "").strip()
            
            if not qty_str or not qty_str.isdigit() or int(qty_str) < 1:
                continue

            try:
                product = Product.objects.get(id=product_id)
                items.append((product, int(qty_str)))
            except Product.DoesNotExist:
                continue

    if not items:
        messages.error(request, "Please select at least one product with a quantity.")
        return redirect("orders:recurring_orders")

    try:
        created_template = create_recurring_template(
            customer_profile=buyer_profile,
            name=template_name,
            rrule_str=rrule,
            items=items,
        )
        messages.success(
            request,
            f"Recurring order template '{created_template.name}' created successfully.",
        )
    except ValueError as e:
        messages.error(request, f"Error creating template: {str(e)}")
        return redirect("orders:recurring_orders")

    return redirect("orders:recurring_orders")


@login_required
@customer_required
def modify_next_instance(request, template_id):
    """
    Allow editing quantities for the next scheduled RecurringOrderInstance (TC-018).
    GET: Show form with next instance items.
    POST: Store modified quantities and redirect to recurring_orders list.
    """
    buyer_profile = _get_buyer_profile(request.user)
    if buyer_profile is None:
        return HttpResponseForbidden("Buyer profile required.")

    template = get_object_or_404(
        RecurringOrderTemplate,
        id=template_id,
        customer=buyer_profile,
    )

    # Get the next scheduled instance for this template
    next_instance = (
        RecurringOrderInstance.objects
        .filter(
            template=template,
            status=RecurringOrderInstance.Status.SCHEDULED,
        )
        .order_by('scheduled_for')
        .first()
    )

    if not next_instance:
        messages.warning(
            request,
            "No upcoming scheduled instances for this template.",
        )
        return redirect("orders:recurring_orders")

    if request.method == "POST":
        # Read modified quantities from POST data
        # Expected format: product_<product_id>=<quantity>
        modifications = {}
        all_items = template.items.all()
        
        for item in all_items:
            qty_key = f"product_{item.product.id}"
            qty_str = request.POST.get(qty_key, "").strip()
            
            if qty_str and qty_str.isdigit() and int(qty_str) >= 1:
                modifications[str(item.product.id)] = int(qty_str)

        # Store modifications persistently in the model field
        if modifications:
            next_instance.quantity_overrides = modifications
            next_instance.save()
            messages.success(
                request,
                "Quantities updated. They will be used when this order is placed.",
            )
        else:
            # Clear any previous overrides if no changes provided
            if next_instance.quantity_overrides:
                next_instance.quantity_overrides = {}
                next_instance.save()
            messages.warning(
                request,
                "No valid quantity changes were made.",
            )

        return redirect("orders:recurring_orders")

    # GET request: show the form with current template items
    template_items = (
        template.items
        .select_related('product')
        .all()
    )

    return render(
        request,
        "customer/recurring_order_modify.html",
        {
            "template": template,
            "next_instance": next_instance,
            "items": template_items,
        },
    )