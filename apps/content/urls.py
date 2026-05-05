# apps/content/urls.py

from django.urls import path

from . import views

app_name = "content"

urlpatterns = [
    path('', views.content_list, name='content_list'),
    path('new/', views.content_create, name='content_create'),
    path('<uuid:post_id>/delete/', views.content_delete, name='content_delete'),
]