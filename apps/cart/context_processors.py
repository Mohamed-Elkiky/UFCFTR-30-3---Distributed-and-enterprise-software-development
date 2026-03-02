from apps.cart.models import Cart


def cart_count(request):
    """Inject cart_count into every template context."""
    if not request.user.is_authenticated:
        return {"cart_count": 0}
    try:
        cart = Cart.objects.get(customer=request.user.customer_profile)
        return {"cart_count": cart.items.count()}
    except (Cart.DoesNotExist, AttributeError):
        return {"cart_count": 0}
