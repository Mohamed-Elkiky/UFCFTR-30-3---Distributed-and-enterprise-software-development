# apps/common/permissions.py

from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def producer_required(view_func):
    """
    Allow access only to authenticated users who have a producer profile.
    Redirect non-producer users away with an error message.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return redirect("accounts:login")

        if not hasattr(user, "producer_profile"):
            messages.error(request, "You must be logged in as a producer to access this page.")
            return redirect("accounts:dashboard")

        return view_func(request, *args, **kwargs)

    return _wrapped_view