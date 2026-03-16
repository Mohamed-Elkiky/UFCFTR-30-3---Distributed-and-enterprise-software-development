# apps/reviews/views.py

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Avg
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.common.permissions import customer_required
from apps.marketplace.models import Product
from apps.orders.models import CustomerOrder

from .forms import ReviewForm
from .models import ProductReview


@require_POST
@customer_required
def submit_review(request, product_id):
    """
    Submit a review for a product.

    Rules:
    - Customer only
    - Customer must have at least one delivered order containing the product
    - One review per (product, customer)
    """
    product = get_object_or_404(Product, id=product_id)
    customer_profile = request.user.customer_profile

    has_delivered_order = CustomerOrder.objects.filter(
        customer=customer_profile,
        status=CustomerOrder.Status.DELIVERED,
        items__product=product,
    ).exists()

    if not has_delivered_order:
        raise PermissionDenied(
            "You can only review products you have received in a delivered order."
        )

    if ProductReview.objects.filter(product=product, customer=customer_profile).exists():
        raise PermissionDenied("You have already reviewed this product.")

    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.product = product
        review.customer = customer_profile
        review.save()
        messages.success(request, "Your review has been submitted.")
    else:
        messages.error(request, "Please correct the errors in the review form.")

    return redirect("marketplace:product_detail", product_id=product.id)


@require_GET
def product_reviews(request, product_id):
    """
    Display all reviews for a product with average stars.
    """
    product = get_object_or_404(Product, id=product_id)

    reviews = ProductReview.objects.filter(product=product).select_related("customer")
    average_stars = reviews.aggregate(avg=Avg("stars"))["avg"]

    return render(
        request,
        "reviews/product_reviews.html",
        {
            "product": product,
            "reviews": reviews,
            "average_stars": average_stars,
            "review_count": reviews.count(),
        },
    )