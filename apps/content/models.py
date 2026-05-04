# apps/content/models.py
"""
Content models for Bristol Regional Food Network.
Handles recipes, farm stories, and educational content from producers.
Related test cases: TC-020
"""

import uuid
from django.db import models


class ContentPost(models.Model):
    """
    Educational content posted by producers (TC-020).
    Can be a recipe, farm story, or storage guide.
    """

    class Kind(models.TextChoices):
        RECIPE = 'recipe', 'Recipe'
        FARM_STORY = 'farm_story', 'Farm Story'
        STORAGE_GUIDE = 'storage_guide', 'Storage Guide'

    class SeasonalTag(models.TextChoices):
        SPRING = 'spring', 'Spring'
        SUMMER = 'summer', 'Summer'
        AUTUMN = 'autumn', 'Autumn'
        WINTER = 'winter', 'Winter'
        ALL_YEAR = 'all_year', 'All Year'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Author (producer)
    producer = models.ForeignKey(
        'accounts.ProducerProfile',
        on_delete=models.CASCADE,
        related_name='content_posts'
    )

    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.RECIPE
    )

    title = models.CharField(max_length=200)

    # Main content body — used for recipe instructions, farm story prose,
    # storage guide text, etc.
    body = models.TextField()

    seasonal_tag = models.CharField(
        max_length=20,
        choices=SeasonalTag.choices,
        default=SeasonalTag.ALL_YEAR
    )

    # Optional extras retained from the previous implementation; not in the
    # ticket spec but harmless and used by templates/views.
    image_url = models.URLField(blank=True, default='')
    is_published = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.kind}: {self.title}"


class ContentProductLink(models.Model):
    """
    Links a ContentPost (e.g. a recipe) to a specific Product.
    Allows showing related recipes/stories on product detail pages.
    Composite uniqueness on (content, product) prevents duplicate links.
    """

    content = models.ForeignKey(
        ContentPost,
        on_delete=models.CASCADE,
        related_name='product_links'
    )

    product = models.ForeignKey(
        'marketplace.Product',
        on_delete=models.CASCADE,
        related_name='content_links'
    )

    class Meta:
        unique_together = ['content', 'product']

    def __str__(self):
        return f"{self.content.title} → {self.product.name}"