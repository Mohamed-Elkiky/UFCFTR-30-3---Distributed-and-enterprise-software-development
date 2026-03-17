from collections import defaultdict

from apps.cart.models import Cart, CartItem
from apps.marketplace.services.surplus import apply_surplus_discount


def get_or_create_cart(user):
    """Return the Cart for *user*, creating one if it doesn't exist.

    Community group users may not have a CustomerProfile yet; one is created
    on demand so the Cart FK can be satisfied.
    """
    if hasattr(user, 'customer_profile'):
        profile = user.customer_profile
    else:
        # Community group user — create a minimal CustomerProfile on demand
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
    cart, _ = Cart.objects.get_or_create(customer=profile)
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
    """Return the total price of all items in the cart (in pence).

    Uses the surplus-discounted price for any product with an active deal.
    """
    total = 0
    for item in cart.items.select_related("product").all():
        unit_price = apply_surplus_discount(item.product)
        total += unit_price * item.quantity
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