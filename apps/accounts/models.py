# apps/accounts/models.py

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Custom manager for User model with email as the unique identifier."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.ADMIN)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model for Bristol Regional Food Network.
    Uses email as the unique identifier instead of username.
    Supports multiple roles: Producer, Customer, Community Group, Restaurant, Admin.
    """

    class Role(models.TextChoices):
        CUSTOMER = 'customer', 'Customer'
        PRODUCER = 'producer', 'Producer'
        COMMUNITY_GROUP = 'community_group', 'Community Group'
        RESTAURANT = 'restaurant', 'Restaurant'
        ADMIN = 'admin', 'Admin'

    username = None
    email = models.EmailField('email address', unique=True)

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER
    )

    phone = models.CharField(max_length=20, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email

    @property
    def is_producer(self):
        return self.role == self.Role.PRODUCER

    @property
    def is_customer(self):
        return self.role == self.Role.CUSTOMER

    @property
    def is_community_group(self):
        return self.role == self.Role.COMMUNITY_GROUP

    @property
    def is_restaurant(self):
        return self.role == self.Role.RESTAURANT


class ProducerProfile(models.Model):
    """
    Extended profile for Producer accounts (TC-001).
    Stores business-specific information.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='producer_profile'
    )
    business_name = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=100)
    business_address = models.TextField()
    postcode = models.CharField(max_length=10)

    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.business_name


class CustomerProfile(models.Model):
    """
    Extended profile for Customer accounts (TC-002).
    Stores delivery address as separate fields.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='customer_profile'
    )
    full_name = models.CharField(max_length=200)
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postcode = models.CharField(max_length=20)
    country = models.CharField(max_length=100)

    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name


class CommunityGroupProfile(models.Model):
    """Extended profile for Community Group accounts (TC-017)."""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='community_group_profile'
    )
    organisation_name = models.CharField(max_length=200)
    organisation_type = models.CharField(max_length=100)
    contact_name = models.CharField(max_length=100)
    delivery_address = models.TextField()
    postcode = models.CharField(max_length=10)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.organisation_name


class RestaurantProfile(models.Model):
    """Extended profile for Restaurant accounts (TC-018)."""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='restaurant_profile'
    )
    restaurant_name = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=100)
    delivery_address = models.TextField()
    postcode = models.CharField(max_length=10)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.restaurant_name