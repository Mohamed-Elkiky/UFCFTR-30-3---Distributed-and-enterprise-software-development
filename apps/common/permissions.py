# apps/common/permissions.py

from functools import wraps

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render


def producer_required(view_func):
    """
    Decorator that checks request.user is authenticated and request.user.role == 'producer'.
    Otherwise renders a styled access-restricted page.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return render(
                request,
                "errors/customer_only.html",
                {
                    "page_title": "Login Required",
                    "message": "You need to be logged in to view this page.",
                    "submessage": "Please sign in with the correct account and try again.",
                    "icon": "🔐",
                },
                status=403,
            )

        if getattr(user, "role", None) != "producer":
            return render(
                request,
                "errors/customer_only.html",
                {
                    "page_title": "Producer Access Required",
                    "message": "This page is only available to producer accounts.",
                    "submessage": "Please sign in with a producer account to continue.",
                    "icon": "🌾",
                },
                status=403,
            )

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def customer_required(view_func):
    """
    Decorator that checks request.user is authenticated, has role == 'customer',
    and has a customer_profile. Otherwise renders a styled access-restricted page.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return render(
                request,
                "errors/customer_only.html",
                {
                    "page_title": "Login Required",
                    "message": "You need to be logged in to view this page.",
                    "submessage": "Please sign in with your customer account and try again.",
                    "icon": "🔐",
                },
                status=403,
            )

        if getattr(user, "role", None) != "customer":
            return render(
                request,
                "errors/customer_only.html",
                {
                    "page_title": "Customer Access Required",
                    "message": "This page is only available to customer accounts.",
                    "submessage": (
                        "You are currently signed in as a producer account, "
                        "so you cannot access the shopping cart or checkout pages."
                    ),
                    "icon": "🛒",
                },
                status=403,
            )

        if not hasattr(user, "customer_profile"):
            return render(
                request,
                "errors/customer_only.html",
                {
                    "page_title": "Customer Profile Required",
                    "message": "Your customer profile could not be found.",
                    "submessage": "Please complete your registration before continuing.",
                    "icon": "👤",
                },
                status=403,
            )

        return view_func(request, *args, **kwargs)

    return _wrapped_view


class ProducerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    LoginRequiredMixin + UserPassesTestMixin that tests self.request.user.is_producer.
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
    Otherwise renders a styled access-restricted page.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return render(
                request,
                "errors/customer_only.html",
                {
                    "page_title": "Login Required",
                    "message": "You need to be logged in to view this page.",
                    "submessage": "Please sign in with an admin account and try again.",
                    "icon": "🔐",
                },
                status=403,
            )

        if getattr(user, "role", None) != "admin":
            return render(
                request,
                "errors/customer_only.html",
                {
                    "page_title": "Admin Access Required",
                    "message": "This page is only available to admin accounts.",
                    "submessage": "Please sign in with the correct account to continue.",
                    "icon": "🛠️",
                },
                status=403,
            )

        return view_func(request, *args, **kwargs)

    return _wrapped_view


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    LoginRequiredMixin + UserPassesTestMixin that tests self.request.user.role == 'admin'.
    """
    def test_func(self):
        return getattr(self.request.user, "role", None) == "admin"