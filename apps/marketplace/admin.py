from django.contrib import admin

from .models import (
    Product,
    ProductCategory,
    Allergen,
    ProductAllergen,
    ProductImage,
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "producer", "category", "availability", "stock_qty")


admin.site.register(ProductCategory)
admin.site.register(Allergen)
admin.site.register(ProductAllergen)
admin.site.register(ProductImage)