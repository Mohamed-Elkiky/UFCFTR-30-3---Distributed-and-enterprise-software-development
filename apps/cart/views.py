from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.cart.models import Cart, CartItem
from apps.marketplace.models import Product


# ---------------------------------------------------------------------------
# Service helpers
# ---------------------------------------------------------------------------

def get_or_create_cart(user):
    """Return the Cart for *user*, creating one if it doesn't exist."""
    cart, _created = Cart.objects.get_or_create(customer=user.customer_profile)
    return cart


def group_cart_by_producer(cart):
    """Return cart items grouped by producer.

    Returns a dict: {ProducerProfile | None: [CartItem, ...]}
    """
    items = cart.items.select_related("product__producer").all()
    grouped = defaultdict(list)
    for item in items:
        grouped[item.product.producer].append(item)
    return dict(grouped)


def get_cart_total_pence(cart):
    """Return the total price of all items in the cart (in pence)."""
    total = 0
    for item in cart.items.select_related("product").all():
        total += (item.product.price_pence or 0) * item.quantity
    return total


def add_to_cart(cart, product, quantity=1):
    """Add *product* to *cart* (or increment its quantity)."""
    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={"quantity": quantity},
    )
    if not created:
        item.quantity += quantity
        item.save()
    return item


def remove_from_cart(cart, product):
    """Remove *product* from *cart* entirely."""
    cart.items.filter(product=product).delete()


def update_quantity(cart, product, quantity):
    """Set the quantity of *product* in *cart*.

    If quantity is zero or less the item is removed.
    """
    if quantity <= 0:
        remove_from_cart(cart, product)
    else:
        cart.items.filter(product=product).update(quantity=quantity)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

@login_required
def cart_detail(request):
    """GET — display the shopping-cart page."""
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
    cart = get_or_create_cart(request.user)
    product = get_object_or_404(Product, pk=product_id)
    quantity = int(request.POST.get("quantity", 1))
    add_to_cart(cart, product, quantity)
    return redirect(request.META.get("HTTP_REFERER", "cart:cart_detail"))


@login_required
@require_POST
def remove_from_cart_view(request, product_id):
    """POST — remove a product from the cart, then redirect to cart."""
    cart = get_or_create_cart(request.user)
    product = get_object_or_404(Product, pk=product_id)
    remove_from_cart(cart, product)
    return redirect("cart:cart_detail")


@login_required
@require_POST
def update_cart_view(request, product_id):
    """POST — update the quantity of a product in the cart."""
    cart = get_or_create_cart(request.user)
    product = get_object_or_404(Product, pk=product_id)
    quantity = int(request.POST.get("quantity", 1))
    update_quantity(cart, product, quantity)
    return redirect("cart:cart_detail")
