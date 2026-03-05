# apps/common/permissions.py

from functools import wraps

from django.http import HttpResponseForbidden
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


def producer_required(view_func):
    """
    Decorator that checks request.user is authenticated and request.user.role == 'producer'.
    Otherwise returns HttpResponseForbidden.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return HttpResponseForbidden("Authentication required.")

        if getattr(user, "role", None) != "producer":
            return HttpResponseForbidden("Producer access required.")

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def customer_required(view_func):
    """
    Decorator that checks request.user is authenticated and request.user.role == 'customer'.
    Otherwise returns HttpResponseForbidden.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return HttpResponseForbidden("Authentication required.")

        if getattr(user, "role", None) != "customer":
            return HttpResponseForbidden("Customer access required.")

        return view_func(request, *args, **kwargs)

    return _wrapped_view


class ProducerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    LoginRequiredMixin + UserPassesTestMixin that tests self.request.user.is_producer
    (as per Jira requirement).
    """
    def test_func(self):
        return bool(getattr(self.request.user, "is_producer", False))


class CustomerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    LoginRequiredMixin + UserPassesTestMixin that tests self.request.user.is_customer.
    """
    def test_func(self):
        return bool(getattr(self.request.user, "is_customer", False))


def admin_required(view_func):
    """
    Decorator that checks request.user is authenticated and request.user.role == 'admin'.
    Otherwise returns HttpResponseForbidden.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return HttpResponseForbidden("Authentication required.")

        if getattr(user, "role", None) != "admin":
            return HttpResponseForbidden("Admin access required.")

        return view_func(request, *args, **kwargs)

    return _wrapped_view


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    LoginRequiredMixin + UserPassesTestMixin that tests self.request.user.role == 'admin'.
    """
    def test_func(self):
        return getattr(self.request.user, "role", None) == "admin"