from django.urls import path

from .views import product_reviews, submit_review

app_name = "reviews"

urlpatterns = [
    path("reviews/<uuid:product_id>/submit/", submit_review, name="review_submit"),
    path("reviews/<uuid:product_id>/", product_reviews, name="product_reviews"),
]