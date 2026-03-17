# apps/cart/views.py

from datetime import date

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.common.permissions import customer_required
from apps.cart.services.pricing import (
    add_to_cart,
    get_cart_total_pence,
    get_or_create_cart,
    group_cart_by_producer,
    remove_from_cart,
    update_quantity,
)
from apps.cart.services.guest_cart import (
    add_to_guest_cart,
    clear_guest_cart,
    get_guest_cart,
    get_guest_cart_total_pence,
    group_guest_cart_by_producer,
    remove_from_guest_cart,
    update_guest_cart,
)
from apps.marketplace.models import Product
from apps.orders.models import CustomerOrder
from apps.orders.services.lead_time import (
    get_earliest_delivery_date,
    validate_delivery_date,
)
from apps.orders.services.create_order import create_orders_from_cart
from apps.payments.gateways.mock import MockGateway
from apps.payments.services.commission import record_order_commission

_BUYER_ROLES = {"customer", "community_group"}


def _is_buyer(user):
    return user.is_authenticated and getattr(user, "role", None) in _BUYER_ROLES


def _get_buyer_profile(user):
    if hasattr(user, 'customer_profile'):
        return user.customer_profile

    from apps.accounts.models import CustomerProfile
    cg = user.community_group_profile
    profile, _ = CustomerProfile.objects.get_or_create(
        user=user,
        defaults={
            'full_name': cg.organisation_name,
            'street': cg.delivery_address,
            'city': '',
            'state': '',
            'postcode': cg.postcode,
            'country': 'UK',
        },
    )
    return profile


def cart_detail(request):
    """GET — display the shopping-cart page (works for guests and logged-in buyers)."""
    if _is_buyer(request.user):
        cart = get_or_create_cart(request.user)
        grouped = group_cart_by_producer(cart)
        total_pence = get_cart_total_pence(cart)
        is_guest = False

        total_food_miles = None
        try:
            from apps.logistics.services.distance import get_food_miles
            customer_profile = request.user.customer_profile
            if customer_profile.latitude and customer_profile.longitude:
                seen_producers = set()
                total = 0.0
                any_valid = False
                for item in cart.items.select_related("product__producer"):
                    producer = item.product.producer
                    if producer.id in seen_producers:
                        continue
                    seen_producers.add(producer.id)
                    miles = get_food_miles(item.product, customer_profile)
                    if miles is not None:
                        total += miles
                        any_valid = True
                if any_valid:
                    total_food_miles = round(total, 1)
        except Exception:
            pass
    else:
        grouped = group_guest_cart_by_producer(request.session)
        total_pence = get_guest_cart_total_pence(request.session)
        is_guest = True
        total_food_miles = None

    return render(
        request,
        "cart/cart_detail.html",
        {
            "grouped": grouped,
            "total_pence": total_pence,
            "total_display": f"{total_pence / 100:.2f}",
            "total_food_miles": total_food_miles,
            "is_guest": is_guest,
        },
    )


@require_POST
def add_to_cart_view(request, product_id):
    """POST — add a product to the cart, then redirect back."""
    product = get_object_or_404(Product, pk=product_id)
    quantity = int(request.POST.get("quantity", 1))

    if _is_buyer(request.user):
        cart = get_or_create_cart(request.user)
        add_to_cart(cart, product, quantity)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"status": "ok", "cart_count": cart.items.count()})
    else:
        add_to_guest_cart(request.session, str(product_id), quantity)
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            guest_cart = get_guest_cart(request.session)
            return JsonResponse({"status": "ok", "cart_count": len(guest_cart)})

    referer = request.META.get("HTTP_REFERER", "")
    return redirect(referer if referer else "cart:cart_detail")


@require_POST
def remove_from_cart_view(request, product_id):
    """POST — remove a product from the cart, then redirect to cart."""
    if _is_buyer(request.user):
        cart = get_or_create_cart(request.user)
        product = get_object_or_404(Product, pk=product_id)
        remove_from_cart(cart, product)
    else:
        remove_from_guest_cart(request.session, str(product_id))
    return redirect("cart:cart_detail")


@require_POST
def update_cart_view(request, product_id):
    """POST — update the quantity of a product in the cart."""
    quantity = int(request.POST.get("quantity", 1))
    if _is_buyer(request.user):
        cart = get_or_create_cart(request.user)
        product = get_object_or_404(Product, pk=product_id)
        update_quantity(cart, product, quantity)
    else:
        update_guest_cart(request.session, str(product_id), quantity)
    return redirect("cart:cart_detail")


@customer_required
def checkout(request):
    cart = get_or_create_cart(request.user)
    grouped = group_cart_by_producer(cart)

    if not grouped:
        messages.warning(request, "Your cart is empty.")
        return redirect("cart:cart_detail")

    earliest_delivery = get_earliest_delivery_date()

    impossible_groups = []
    for producer, items in grouped.items():
        best_befores = [
            i.product.best_before_date
            for i in items
            if i.product.best_before_date
        ]
        if best_befores:
            latest_allowed = min(best_befores)
            if latest_allowed < earliest_delivery:
                producer_name = producer.business_name if producer else "Unknown producer"
                impossible_groups.append(
                    f"{producer_name}: best-before date ({latest_allowed}) is earlier than the earliest delivery date ({earliest_delivery})."
                )

    if impossible_groups:
        for msg in impossible_groups:
            messages.error(
                request,
                f"Some items cannot be checked out because there is no valid delivery date. {msg}"
            )
        return redirect("cart:cart_detail")

    if request.method == "POST":
        special_instructions = request.POST.get("special_instructions", "")
        delivery_dates_by_producer = {}
        errors = []

        for producer in grouped.keys():
            field_name = (
                f"delivery_date_{producer.pk}"
                if producer
                else "delivery_date_default"
            )
            raw_date = request.POST.get(field_name) or request.POST.get("delivery_date")
            producer_name = producer.business_name if producer else "your order"

            if not raw_date:
                errors.append(f"Please select a delivery date for {producer_name}.")
                continue

            try:
                parsed = date.fromisoformat(raw_date)
            except ValueError:
                errors.append(f"Invalid delivery date for {producer_name}.")
                continue

            if not validate_delivery_date(parsed):
                errors.append(
                    f"Delivery date for {producer_name} must be at least 48 hours "
                    f"from now (earliest: {earliest_delivery})."
                )
                continue

            if producer:
                items_for_producer = grouped[producer]
                best_befores = [
                    i.product.best_before_date
                    for i in items_for_producer
                    if i.product.best_before_date
                ]
                if best_befores:
                    latest_allowed = min(best_befores)
                    if parsed > latest_allowed:
                        errors.append(
                            f"Delivery date for {producer_name} must be on or before "
                            f"{latest_allowed} (earliest best-before date in your order)."
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
                    customer_profile=_get_buyer_profile(request.user),
                    delivery_date=main_delivery_date,
                    delivery_dates_by_producer=delivery_dates_by_producer,
                    special_instructions=special_instructions,
                )

                gw = MockGateway()
                result = gw.initiate(customer_order.total_pence, customer_order.pk)
                gw.capture(result["ref"])
                record_order_commission(customer_order)

                messages.success(request, "Your order has been placed successfully!")
                return redirect("cart:order_confirmed", order_id=customer_order.pk)

            except Exception as e:
                messages.error(request, f"There was a problem placing your order: {e}")

    grouped_with_dates = {}
    for producer, items in grouped.items():
        best_befores = [
            i.product.best_before_date for i in items if i.product.best_before_date
        ]
        subtotal_pence = sum(i.product.price_pence * i.quantity for i in items)
        grouped_with_dates[producer] = {
            "items": items,
            "earliest_delivery": earliest_delivery.isoformat(),
            "latest_delivery": min(best_befores).isoformat() if best_befores else "",
            "subtotal_pence": subtotal_pence,
            "subtotal_display": f"{subtotal_pence / 100:.2f}",
        }

    total_pence = get_cart_total_pence(cart)
    commission_pence = int(total_pence * 0.05)
    grand_total_pence = total_pence + commission_pence

    return render(
        request,
        "cart/checkout_multivendor.html",
        {
            "grouped": grouped_with_dates,
            "total_pence": total_pence,
            "commission_pence": commission_pence,
            "grand_total_pence": grand_total_pence,
            "total_display": f"{total_pence / 100:.2f}",
            "commission_display": f"{commission_pence / 100:.2f}",
            "grand_total_display": f"{grand_total_pence / 100:.2f}",
            "earliest_delivery": earliest_delivery.isoformat(),
            "customer_profile": _get_buyer_profile(request.user),
        },
    )


def guest_checkout(request):
    grouped = group_guest_cart_by_producer(request.session)

    if not grouped:
        messages.warning(request, "Your cart is empty.")
        return redirect("cart:cart_detail")

    earliest_delivery = get_earliest_delivery_date()

    if request.method == "POST":
        guest_name = request.POST.get("guest_name", "").strip()
        guest_email = request.POST.get("guest_email", "").strip()
        street = request.POST.get("street", "").strip()
        city = request.POST.get("city", "").strip()
        state = request.POST.get("state", "").strip()
        postcode = request.POST.get("postcode", "").strip()
        country = request.POST.get("country", "").strip()
        special_instructions = request.POST.get("special_instructions", "")

        delivery_dates_by_producer = {}
        errors = []

        if not guest_name:
            errors.append("Please enter your name.")
        if not guest_email:
            errors.append("Please enter your email address.")
        if not street or not postcode:
            errors.append("Please fill in your delivery address (street and postcode required).")

        for producer in grouped.keys():
            field_name = (
                f"delivery_date_{producer.pk}" if producer else "delivery_date_default"
            )
            raw_date = request.POST.get(field_name) or request.POST.get("delivery_date")
            producer_name = producer.business_name if producer else "your order"

            if not raw_date:
                errors.append(f"Please select a delivery date for {producer_name}.")
                continue

            try:
                parsed = date.fromisoformat(raw_date)
            except ValueError:
                errors.append(f"Invalid delivery date for {producer_name}.")
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
            guest_address = f"{street}, {city}" if city else street

            try:
                customer_order = create_orders_from_cart(
                    guest_grouped=grouped,
                    customer_profile=None,
                    delivery_date=main_delivery_date,
                    delivery_dates_by_producer=delivery_dates_by_producer,
                    special_instructions=special_instructions,
                    guest_address=guest_address,
                    guest_postcode=postcode,
                )

                gw = MockGateway()
                result = gw.initiate(customer_order.total_pence, customer_order.pk)
                gw.capture(result["ref"])
                record_order_commission(customer_order)

                clear_guest_cart(request.session)
                request.session["last_guest_order_id"] = str(customer_order.pk)

                messages.success(request, "Your order has been placed successfully!")
                return redirect("cart:order_confirmed", order_id=customer_order.pk)

            except Exception as e:
                messages.error(request, f"There was a problem placing your order: {e}")

    grouped_with_dates = {}
    for producer, items in grouped.items():
        best_befores = [
            i.product.best_before_date for i in items if i.product.best_before_date
        ]
        subtotal_pence = sum(i.product.price_pence * i.quantity for i in items)
        grouped_with_dates[producer] = {
            "items": items,
            "earliest_delivery": earliest_delivery.isoformat(),
            "latest_delivery": min(best_befores).isoformat() if best_befores else "",
            "subtotal_pence": subtotal_pence,
            "subtotal_display": f"{subtotal_pence / 100:.2f}",
        }

    total_pence = get_guest_cart_total_pence(request.session)
    commission_pence = int(total_pence * 0.05)
    grand_total_pence = total_pence + commission_pence

    return render(
        request,
        "cart/guest_checkout.html",
        {
            "grouped": grouped_with_dates,
            "total_pence": total_pence,
            "commission_pence": commission_pence,
            "grand_total_pence": grand_total_pence,
            "total_display": f"{total_pence / 100:.2f}",
            "commission_display": f"{commission_pence / 100:.2f}",
            "grand_total_display": f"{grand_total_pence / 100:.2f}",
            "earliest_delivery": earliest_delivery.isoformat(),
        },
    )


def order_confirmed(request, order_id):
    order = get_object_or_404(CustomerOrder, id=order_id)

    if order.customer is None:
        if str(order_id) != request.session.get("last_guest_order_id"):
            messages.error(request, "You do not have permission to view this order.")
            return redirect("marketplace:home")
    else:
        if not request.user.is_authenticated:
            messages.error(request, "You do not have permission to view this order.")
            return redirect("marketplace:home")
        try:
            if order.customer != request.user.customer_profile:
                messages.error(request, "You do not have permission to view this order.")
                return redirect("marketplace:home")
        except Exception:
            messages.error(request, "You do not have permission to view this order.")
            return redirect("marketplace:home")

    producer_orders = order.producer_orders.select_related("producer").all()
    items = order.items.select_related("product").all()
    payment = getattr(order, "payment", None)

    return render(
        request,
        "cart/order_confirmed.html",
        {
            "order": order,
            "producer_orders": producer_orders,
            "items": items,
            "payment": payment,
        },
    )