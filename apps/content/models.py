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
    Can be recipes, farm stories, storage guides, etc.
    """
    
    class ContentType(models.TextChoices):
        RECIPE = 'recipe', 'Recipe'
        FARM_STORY = 'farm_story', 'Farm Story'
        STORAGE_GUIDE = 'storage_guide', 'Storage Guide'
        NEWS = 'news', 'News Update'
    
    class Season(models.TextChoices):
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
    
    content_type = models.CharField(
        max_length=20,
        choices=ContentType.choices,
        default=ContentType.RECIPE
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    content = models.TextField()  # Main content/instructions
    
    # For recipes
    ingredients = models.TextField(blank=True, default='')  # JSON or text list
    
    # Seasonal tag
    season = models.CharField(
        max_length=20,
        choices=Season.choices,
        default=Season.ALL_YEAR
    )
    
    # Image URL
    image_url = models.URLField(blank=True, default='')
    
    is_published = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.content_type}: {self.title}"


class ContentProductLink(models.Model):
    """
    Links content (like recipes) to specific products.
    Allows showing related recipes on product pages.
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