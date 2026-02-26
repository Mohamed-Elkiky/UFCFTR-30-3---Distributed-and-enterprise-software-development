import uuid
from django.db import models


class ProductCategory(models.Model):
    # SQL: product_category(id bigserial PK, name text UNIQUE NOT NULL, created_at timestamptz)
    name = models.TextField(unique=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "product_category"

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    # SQL enum: availability_status
    class AvailabilityStatus(models.TextChoices):
        IN_SEASON = "in_season", "in_season"
        AVAILABLE_YEAR_ROUND = "available_year_round", "available_year_round"
        OUT_OF_SEASON = "out_of_season", "out_of_season"
        UNAVAILABLE = "unavailable", "unavailable"

    # SQL: product(id uuid PK, ...)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # SQL: producer_id uuid FK -> producer_profile(user_id)
    producer = models.ForeignKey(
        "accounts.ProducerProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="producer_id",
        related_name="products",
    )

    # SQL: category_id bigint FK -> product_category(id)
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="category_id",
        related_name="products",
    )

    # Product name - REQUIRED
    name = models.CharField(max_length=255)  # Changed: required, max_length
    description = models.TextField(blank=True, default='')  # Changed: has default

    # Price and unit - REQUIRED for commerce
    price_pence = models.PositiveIntegerField()  # Changed: required, positive only
    unit = models.CharField(max_length=50)  # Changed: required, max_length

    availability = models.CharField(
        max_length=32,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.AVAILABLE_YEAR_ROUND,  # Changed: has default
    )

    seasonal_start_month = models.SmallIntegerField(null=True, blank=True)
    seasonal_end_month = models.SmallIntegerField(null=True, blank=True)

    stock_qty = models.PositiveIntegerField(default=0)  # Changed: required, default
    low_stock_threshold = models.PositiveIntegerField(default=10)  # Changed: has default

    organic_certified = models.BooleanField(default=False)  # Changed: has default

    harvest_date = models.DateField(null=True, blank=True)
    best_before_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)  # Changed: auto-populate
    updated_at = models.DateTimeField(auto_now=True)  # Changed: auto-populate

    class Meta:
        db_table = "product"

    @property
    def price_display(self):
        """Return price formatted as £X.XX"""
        return f"£{self.price_pence / 100:.2f}"

    def __str__(self) -> str:
        return str(self.name) if self.name else str(self.id)


class Allergen(models.Model):
    # SQL: allergen(id bigserial PK, name text UNIQUE)
    name = models.TextField(unique=True, null=True, blank=True)

    class Meta:
        db_table = "allergen"

    def __str__(self) -> str:
        return self.name or f"Allergen({self.pk})"


class ProductAllergen(models.Model):
    # SQL: product_allergen(product_id uuid, allergen_id bigint, PK(product_id, allergen_id))
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        db_column="product_id",
        related_name="allergen_links",
    )
    allergen = models.ForeignKey(
        Allergen,
        on_delete=models.CASCADE,
        db_column="allergen_id",
        related_name="product_links",
    )

    class Meta:
        db_table = "product_allergen"
        # Django doesn't support true composite PKs in the normal ORM API,
        # so we enforce the same uniqueness rule:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "allergen"],
                name="product_allergen_pk",
            )
        ]

    def __str__(self) -> str:
        return f"{self.product_id} - {self.allergen_id}"


class ProductImage(models.Model):
    # SQL: product_image(id uuid PK, product_id uuid, url text, created_at timestamptz)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        db_column="product_id",
        related_name="images",
    )
    url = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "product_image"

    def __str__(self) -> str:
        return self.url or str(self.id)