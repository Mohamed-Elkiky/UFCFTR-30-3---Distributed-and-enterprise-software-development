# apps/accounts/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.urls import reverse_lazy

from .forms import LoginForm, ProducerRegistrationForm, CustomerRegistrationForm

User = get_user_model()


class CustomLoginView(LoginView):
    """Custom login view using email authentication."""
    template_name = 'auth/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('accounts:dashboard')
    
    def form_invalid(self, form):
        messages.error(self.request, 'Invalid email or password.')
        return super().form_invalid(form)


def logout_view(request):
    """Log out the user and redirect to login page."""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('accounts:login')


def register_producer(request):
    """
    Producer registration view (TC-001).
    Creates user account with producer role and business profile.
    """
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        form = ProducerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                f'Welcome, {user.producer_profile.business_name}! Your producer account has been created.'
            )
            return redirect('accounts:dashboard')
    else:
        form = ProducerRegistrationForm()
    
    return render(request, 'auth/register_producer.html', {'form': form})


def register_customer(request):
    """
    Customer registration view (TC-002).
    Creates user account with customer role and delivery profile.
    """
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                f'Welcome, {user.customer_profile.full_name}! Your account has been created.'
            )
            return redirect('accounts:dashboard')
    else:
        form = CustomerRegistrationForm()
    
    return render(request, 'auth/register_customer.html', {'form': form})


@login_required
def dashboard(request):
    """
    Dashboard view that redirects to role-appropriate dashboard (TC-022).
    Demonstrates role-based access control.
    """
    user = request.user
    
    if user.is_producer:
        return redirect('accounts:producer_dashboard')
    elif user.is_community_group:
        return redirect('accounts:community_dashboard')
    elif user.is_restaurant:
        return redirect('accounts:restaurant_dashboard')
    else:
        # Default: customer dashboard
        return redirect('accounts:customer_dashboard')


@login_required
def producer_dashboard(request):
    """Producer dashboard - only accessible by producers (TC-022)."""
    if not request.user.is_producer:
        messages.error(request, 'Access denied. Producer account required.')
        return redirect('accounts:dashboard')
    
    context = {
        'profile': request.user.producer_profile
    }
    return render(request, 'producer/dashboard.html', context)


@login_required
def customer_dashboard(request):
    """Customer dashboard - accessible by customers."""
    if not request.user.is_customer:
        messages.error(request, 'Access denied.')
        return redirect('accounts:dashboard')
    
    context = {
        'profile': request.user.customer_profile
    }
    return render(request, 'customer/dashboard.html', context)