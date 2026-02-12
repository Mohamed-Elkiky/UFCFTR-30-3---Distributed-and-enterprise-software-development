from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Single register page (NEW)
    path('register/', views.register, name='register'),

    # Existing registration endpoints (keep)
    path('register/producer/', views.register_producer, name='register_producer'),
    path('register/customer/', views.register_customer, name='register_customer'),

    # Dashboards
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/producer/', views.producer_dashboard, name='producer_dashboard'),
    path('dashboard/customer/', views.customer_dashboard, name='customer_dashboard'),
]
