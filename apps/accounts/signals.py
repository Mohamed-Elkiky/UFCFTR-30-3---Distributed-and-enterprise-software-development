from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User, ProducerProfile, CustomerProfile


@receiver(post_save, sender=User)
def ensure_customer_profile(sender, instance, created, **kwargs):
    if instance.role == User.Role.CUSTOMER and not hasattr(instance, "customer_profile"):
        default_name = (
            instance.email.split("@")[0].replace(".", " ").replace("_", " ").title()
            if instance.email else "Customer"
        )

        CustomerProfile.objects.create(
            user=instance,
            full_name=default_name,
            street="",
            city="",
            state="",
            postcode="",
            country="",
        )


@receiver(post_save, sender=ProducerProfile)
def geocode_producer(sender, instance, **kwargs):
    if instance.postcode and (instance.latitude is None or instance.longitude is None):
        try:
            from apps.logistics.services.geocoding import update_producer_coordinates
            update_producer_coordinates(instance)
        except Exception:
            pass


@receiver(post_save, sender=CustomerProfile)
def geocode_customer(sender, instance, **kwargs):
    if instance.postcode and (instance.latitude is None or instance.longitude is None):
        try:
            from apps.logistics.services.geocoding import update_customer_coordinates
            update_customer_coordinates(instance)
        except Exception:
            pass