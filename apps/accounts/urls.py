from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Single register page
    path('register/', views.register, name='register'),

    # Registration endpoints
    path('register/producer/', views.register_producer, name='register_producer'),
    path('register/customer/', views.register_customer, name='register_customer'),

    # Registration success
    path('register/success/', views.register_success, name='register_success'),

    # Dashboards
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/producer/', views.producer_dashboard, name='producer_dashboard'),
    path('dashboard/customer/', views.customer_dashboard, name='customer_dashboard'),

    # Terms and conditions
    path('terms/', views.terms_conditions, name='terms_conditions'),
]