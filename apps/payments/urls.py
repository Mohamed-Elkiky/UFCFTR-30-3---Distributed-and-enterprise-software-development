from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('settlements/', views.producer_settlements, name='producer_settlements'),
    path('admin/commission-report/', views.admin_commission_report, name='admin_commission_report'),
    path('admin/commission-report/order/<uuid:order_id>/', views.admin_order_commission_detail, name='admin_order_detail'),
]