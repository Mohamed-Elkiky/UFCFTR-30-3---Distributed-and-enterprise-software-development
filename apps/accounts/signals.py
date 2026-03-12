from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ProducerProfile, CustomerProfile


@receiver(post_save, sender=ProducerProfile)
def geocode_producer(sender, instance, **kwargs):
    if instance.postcode and (instance.latitude is None or instance.longitude is None):
        from apps.logistics.services.geocoding import update_producer_coordinates
        update_producer_coordinates(instance)


@receiver(post_save, sender=CustomerProfile)
def geocode_customer(sender, instance, **kwargs):
    if instance.postcode and (instance.latitude is None or instance.longitude is None):
        from apps.logistics.services.geocoding import update_customer_coordinates
        update_customer_coordinates(instance)