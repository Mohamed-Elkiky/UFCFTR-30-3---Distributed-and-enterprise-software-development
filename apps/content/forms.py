# apps/content/forms.py
"""
Forms for the content app (TC-020).
"""

from django import forms

from apps.marketplace.models import Product

from .models import ContentPost


class ContentPostForm(forms.ModelForm):
    """
    Form for producers to create or edit a ContentPost (recipe, farm story,
    or storage guide) and link it to one or more of their own products.

    The `products` field is added on top of the model fields so the view can
    persist ContentProductLink rows after the post itself is saved.
    """

    products = forms.ModelMultipleChoiceField(
        queryset=Product.objects.none(),  # narrowed in __init__ to the producer's own products
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Linked products",
        help_text="Select products this content relates to (e.g. ingredients used in a recipe).",
    )

    class Meta:
        model = ContentPost
        fields = ['kind', 'title', 'body', 'seasonal_tag']
        widgets = {
            'body': forms.Textarea(attrs={'rows': 10}),
        }

    def __init__(self, *args, producer=None, **kwargs):
        """
        Args:
            producer: ProducerProfile of the user creating the post. Used to
                      restrict the `products` queryset to that producer's own
                      products only.
        """
        super().__init__(*args, **kwargs)

        if producer is not None:
            self.fields['products'].queryset = Product.objects.filter(
                producer=producer
            ).order_by('name')