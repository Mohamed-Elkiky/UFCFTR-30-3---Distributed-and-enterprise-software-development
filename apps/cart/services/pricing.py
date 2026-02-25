from collections import defaultdict

from apps.cart.models import Cart, CartItem


def get_or_create_cart(user):
    """Return the Cart for *user*, creating one if it doesn't exist."""
    cart, _ = Cart.objects.get_or_create(customer=user.customer_profile)
    return cart


def group_cart_by_producer(cart):
    """Return cart items grouped by producer.

    Returns a dict: {ProducerProfile: [CartItem, ...]}
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
    """Add *product* to *cart*, or increment quantity if already present."""
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

    Removes the item if quantity is zero or less.
    """
    if quantity <= 0:
        remove_from_cart(cart, product)
    else:
        cart.items.filter(product=product).update(quantity=quantity)