from django.contrib import admin
from .models import User, ProducerProfile, CustomerProfile

admin.site.register(User)
admin.site.register(ProducerProfile)
admin.site.register(CustomerProfile)