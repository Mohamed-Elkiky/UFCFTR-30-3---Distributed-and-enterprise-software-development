# brfn/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('cart/', include('apps.cart.urls', namespace='cart')),
    path('orders/', include('apps.orders.urls', namespace='orders')),
    path('', include('apps.marketplace.urls', namespace='marketplace')),
    path('reviews/', include('apps.reviews.urls', namespace='reviews')),
    path('content/', include('apps.content.urls', namespace='content')),
]