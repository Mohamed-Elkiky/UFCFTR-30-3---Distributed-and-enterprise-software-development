# brfn/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('cart/', include('apps.cart.urls', namespace='cart')),
    path('orders/', include('apps.orders.urls', namespace='orders')),
    path('payments/', include('apps.payments.urls', namespace='payments')),
    path('', include('apps.marketplace.urls', namespace='marketplace')),
    path('reviews/', include('apps.reviews.urls', namespace='reviews')),
    path('content/', include('apps.content.urls', namespace='content')),
]

from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)