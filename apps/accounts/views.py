# apps/accounts/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.db import transaction
from django.urls import reverse_lazy

from .forms import LoginForm, ProducerRegistrationForm, CustomerRegistrationForm

User = get_user_model()


class CustomLoginView(LoginView):
    """Custom login view using email authentication."""
    template_name = 'auth/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('marketplace:home')  # go to home after login

    def form_invalid(self, form):
        messages.error(self.request, 'Invalid email or password.')
        return super().form_invalid(form)


def logout_view(request):
    """Log out the user and redirect to login page."""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('accounts:login')


def _register_context(customer_form=None, producer_form=None):
    """Return the context dict that auth/register.html expects."""
    return {
        "customer_form": customer_form or CustomerRegistrationForm(prefix="customer"),
        "producer_form": producer_form or ProducerRegistrationForm(prefix="producer"),
    }


def register(request):
    """Render the combined registration page (GET only)."""
    if request.user.is_authenticated:
        return redirect('marketplace:home')

    return render(request, 'auth/register.html', _register_context())


def register_customer(request):
    if request.user.is_authenticated:
        return redirect('marketplace:home')

    if request.method != 'POST':
        return redirect('accounts:register')

    form = CustomerRegistrationForm(request.POST, prefix="customer")

    if not form.is_valid():
        return render(request, 'auth/register.html', _register_context(customer_form=form))

    with transaction.atomic():
        user = form.save()

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return redirect('accounts:register_success')


def register_producer(request):
    if request.user.is_authenticated:
        return redirect('marketplace:home')

    if request.method != 'POST':
        return redirect('accounts:register')

    form = ProducerRegistrationForm(request.POST, prefix="producer")

    if not form.is_valid():
        return render(request, 'auth/register.html', _register_context(producer_form=form))

    with transaction.atomic():
        user = form.save()

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return redirect('accounts:register_success')


def register_success(request):
    """Show confirmation page after successful registration."""
    return render(request, 'auth/register_success.html')


@login_required
def dashboard(request):
    return redirect('marketplace:home')


@login_required
def producer_dashboard(request):
    return redirect('marketplace:home')


@login_required
def customer_dashboard(request):
    return redirect('marketplace:home')


def terms_conditions(request):
    """Display the terms and conditions page."""
    return render(request, 'terms/terms_conditions.html')