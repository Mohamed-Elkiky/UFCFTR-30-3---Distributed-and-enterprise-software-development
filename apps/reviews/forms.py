# apps/reviews/forms.py

from django import forms

from .models import ProductReview


class ReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ["stars", "title", "body"]
        widgets = {
            # stars is now submitted via the hidden input populated by the
            # star-picker JavaScript in product_detail.html
            "stars": forms.HiddenInput(),
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Review title",
                }
            ),
            "body": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Write your review here...",
                }
            ),
        }