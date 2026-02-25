# apps/marketplace/urls.py
from django.urls import path
from . import views

app_name = 'marketplace'

urlpatterns = [
    path('', views.home, name='home'),
    
    # Producer product management (DESDG2-13)
    path('products/', views.product_list, name='product_list'),
    path('products/new/', views.product_create, name='product_create'),
    path('products/<uuid:product_id>/edit/', views.product_edit, name='product_edit'),
    path('products/<uuid:product_id>/delete/', views.product_delete, name='product_delete'),
    
    # Customer browsing (DESDG2-14)
    path('categories/', views.category_list, name='category_list'),
    path('category/<int:category_id>/', views.product_list_by_category, name='product_list_by_category'),
    path('product/<uuid:product_id>/', views.product_detail, name='product_detail'),
]