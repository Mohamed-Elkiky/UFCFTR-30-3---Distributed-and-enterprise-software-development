from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('settlements/', views.producer_settlements, name='producer_settlements'),
]