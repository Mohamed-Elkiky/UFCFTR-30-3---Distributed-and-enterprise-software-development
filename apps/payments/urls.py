from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('settlements/', views.producer_settlements, name='producer_settlements'),
    path('admin/commission-report/', views.admin_commission_report, name='admin_commission_report'),
]