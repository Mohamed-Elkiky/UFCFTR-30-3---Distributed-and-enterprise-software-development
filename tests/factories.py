# tests/factories.py

import uuid
from datetime import date, timedelta

import factory
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import CustomerProfile, ProducerProfile
from apps.cart.models import Cart, CartItem
from apps.marketplace.models import (
    Allergen,
    Product,
    ProductAllergen,
    ProductCategory,
    ProductImage,
)
from apps.orders.models import CustomerOrder, OrderItem, ProducerOrder


# =============================================================================
# USERS / PROFILES
# =============================================================================

class UserFactory(factory.django.DjangoModelFactory):
    """
    Default user is a CUSTOMER (per model default).
    """
    class Meta:
        model = get_user_model()
        django_get_or_create = ("email",)

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "password123")
    role = "customer"
    phone = factory.Sequence(lambda n: f"+447700900{n:03d}")


class ProducerUserFactory(UserFactory):
    role = "producer"


class CustomerUserFactory(UserFactory):
    role = "customer"


class ProducerProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProducerProfile

    user = factory.SubFactory(ProducerUserFactory)
    business_name = factory.Sequence(lambda n: f"Producer Business {n}")
    contact_name = factory.Sequence(lambda n: f"Producer Contact {n}")
    business_address = factory.Sequence(lambda n: f"{n} Market Street, Bristol")
    postcode = "BS1 1AA"
    latitude = None
    longitude = None


class CustomerProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomerProfile

    user = factory.SubFactory(CustomerUserFactory)
    full_name = factory.Sequence(lambda n: f"Customer {n} Example")
    street = factory.Sequence(lambda n: f"{n} High Street")
    city = "Bristol"
    state = "Bristol"
    postcode = "BS1 2BB"
    country = "UK"
    latitude = None
    longitude = None


# =============================================================================
# MARKETPLACE
# =============================================================================

class ProductCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductCategory

    name = factory.Sequence(lambda n: f"Category {n}")
    created_at = factory.LazyFunction(timezone.now)


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    id = factory.LazyFunction(uuid.uuid4)
    producer = factory.SubFactory(ProducerProfileFactory)
    category = factory.SubFactory(ProductCategoryFactory)

    name = factory.Sequence(lambda n: f"Product {n}")
    description = factory.Faker("sentence")

    price_pence = 250
    unit = "kg"

    availability = Product.AvailabilityStatus.AVAILABLE_YEAR_ROUND
    seasonal_start_month = None
    seasonal_end_month = None

    stock_qty = 50
    low_stock_threshold = 10

    organic_certified = False

    harvest_date = None
    best_before_date = factory.LazyFunction(lambda: date.today() + timedelta(days=7))


class AllergenFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Allergen

    name = factory.Sequence(lambda n: f"Allergen {n}")


class ProductAllergenFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductAllergen

    product = factory.SubFactory(ProductFactory)
    allergen = factory.SubFactory(AllergenFactory)


class ProductImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductImage

    id = factory.LazyFunction(uuid.uuid4)
    product = factory.SubFactory(ProductFactory)
    url = factory.Sequence(lambda n: f"https://example.com/image{n}.jpg")
    created_at = factory.LazyFunction(timezone.now)


# =============================================================================
# CART
# =============================================================================

class CartFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Cart

    id = factory.LazyFunction(uuid.uuid4)
    customer = factory.SubFactory(CustomerProfileFactory)


class CartItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CartItem

    cart = factory.SubFactory(CartFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = 1


# =============================================================================
# ORDERS
# =============================================================================

class CustomerOrderFactory(factory.django.DjangoModelFactory):
    """
    Creates a basic CustomerOrder. Does NOT automatically create items.
    """
    class Meta:
        model = CustomerOrder

    id = factory.LazyFunction(uuid.uuid4)
    customer = factory.SubFactory(CustomerProfileFactory)

    delivery_address = factory.LazyAttribute(
        lambda o: f"{o.customer.street}, {o.customer.city}, {o.customer.postcode}"
    )
    delivery_postcode = factory.LazyAttribute(lambda o: o.customer.postcode)
    delivery_date = factory.LazyFunction(lambda: date.today() + timedelta(days=3))
    special_instructions = ""

    subtotal_pence = 0
    commission_pence = 0
    total_pence = 0
    status = CustomerOrder.Status.PENDING


class ProducerOrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProducerOrder

    id = factory.LazyFunction(uuid.uuid4)
    customer_order = factory.SubFactory(CustomerOrderFactory)
    producer = factory.SubFactory(ProducerProfileFactory)

    subtotal_pence = 0
    commission_pence = 0
    producer_payment_pence = 0
    status = ProducerOrder.Status.PENDING
    status_notes = ""
    delivery_date = factory.LazyAttribute(lambda o: o.customer_order.delivery_date)


class OrderItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrderItem

    id = factory.LazyFunction(uuid.uuid4)
    order = factory.SubFactory(CustomerOrderFactory)
    product = factory.SubFactory(ProductFactory)

    product_name = factory.LazyAttribute(lambda o: o.product.name)
    product_unit = factory.LazyAttribute(lambda o: o.product.unit)
    price_pence = factory.LazyAttribute(lambda o: o.product.price_pence)
    quantity = 1
    # line_total_pence calculated in model save()