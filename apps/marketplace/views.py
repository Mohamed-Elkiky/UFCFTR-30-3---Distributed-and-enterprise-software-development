# apps/marketplace/views.py
from django.shortcuts import render

def home(request):
    return render(request, 'marketplace/home.html')