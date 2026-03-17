# apps/cart/services/guest_cart.py
"""Session-based cart for unauthenticated (guest) users."""

from collections import defaultdict
from dataclasses import dataclass

from apps.marketplace.models import Product
from apps.marketplace.services.surplus import apply_surplus_discount

GUEST_CART_KEY = "guest_cart"


def get_guest_cart(session):
    """Return {product_id_str: quantity} dict from session."""
    return session.get(GUEST_CART_KEY, {})


def save_guest_cart(session, cart):
    session[GUEST_CART_KEY] = cart
    session.modified = True


def add_to_guest_cart(session, product_id_str, quantity=1):
    cart = get_guest_cart(session)
    cart[product_id_str] = cart.get(product_id_str, 0) + quantity
    save_guest_cart(session, cart)


def remove_from_guest_cart(session, product_id_str):
    cart = get_guest_cart(session)
    cart.pop(product_id_str, None)
    save_guest_cart(session, cart)


def update_guest_cart(session, product_id_str, quantity):
    cart = get_guest_cart(session)
    if quantity <= 0:
        cart.pop(product_id_str, None)
    else:
        cart[product_id_str] = quantity
    save_guest_cart(session, cart)


def clear_guest_cart(session):
    session.pop(GUEST_CART_KEY, None)
    session.modified = True


@dataclass
class GuestCartItem:
    product: object
    quantity: int


def get_guest_cart_items(session):
    """Return list of GuestCartItem for items stored in session."""
    cart = get_guest_cart(session)
    if not cart:
        return []
    products = {
        str(p.pk): p
        for p in Product.objects.filter(pk__in=list(cart.keys())).select_related("producer")
    }
    return [
        GuestCartItem(product=products[pid], quantity=qty)
        for pid, qty in cart.items()
        if pid in products
    ]


def group_guest_cart_by_producer(session):
    """Return {ProducerProfile: [GuestCartItem, ...]} for the session cart."""
    grouped = defaultdict(list)
    for item in get_guest_cart_items(session):
        grouped[item.product.producer].append(item)
    return dict(grouped)


def get_guest_cart_total_pence(session):
    """Return total price (in pence) for the session cart, respecting surplus deals."""
    return sum(
        apply_surplus_discount(item.product) * item.quantity
        for item in get_guest_cart_items(session)
    )
