from django.contrib import admin

from .models import ProductReview


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "customer", "stars", "created_at")
    list_filter = ("stars", "created_at")
    search_fields = ("product__name", "customer__full_name", "title", "body")