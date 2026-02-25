# apps/marketplace/forms.py

from django import forms
from django.core.exceptions import ValidationError

from .models import Product, ProductAllergen, Allergen


class ProductForm(forms.ModelForm):
    """
    Form for producers to create and edit product listings (TC-003).
    Handles all product fields with validation for price and stock.
    """
    
    # Allergens as a multiple choice field (handled separately from the Product model)
    allergens = forms.ModelMultipleChoiceField(
        queryset=Allergen.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'allergen-checkbox-list'
        }),
        required=False,
        help_text='Select all allergens that apply to this product'
    )
    
    class Meta:
        model = Product
        fields = [
            'name',
            'category',
            'description',
            'price_pence',
            'unit',
            'availability',
            'seasonal_start_month',
            'seasonal_end_month',
            'stock_qty',
            'low_stock_threshold',
            'organic_certified',
            'harvest_date',
            'best_before_date',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Organic Free Range Eggs'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe your product...'
            }),
            'price_pence': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Price in pence (e.g. 350 for £3.50)',
                'min': '1'
            }),
            'unit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. kg, dozen, bunch, bag'
            }),
            'availability': forms.Select(attrs={
                'class': 'form-control'
            }),
            'seasonal_start_month': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '1-12',
                'min': '1',
                'max': '12'
            }),
            'seasonal_end_month': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '1-12',
                'min': '1',
                'max': '12'
            }),
            'stock_qty': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Available quantity',
                'min': '0'
            }),
            'low_stock_threshold': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Alert when stock falls below this',
                'min': '0'
            }),
            'organic_certified': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'harvest_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'best_before_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        labels = {
            'price_pence': 'Price (in pence)',
            'stock_qty': 'Stock Quantity',
            'low_stock_threshold': 'Low Stock Alert Threshold',
            'organic_certified': 'Organic Certified',
            'seasonal_start_month': 'Season Start Month (1-12)',
            'seasonal_end_month': 'Season End Month (1-12)',
            'harvest_date': 'Harvest Date',
            'best_before_date': 'Best Before Date',
        }
    
    def clean_price_pence(self):
        """Validate that price is greater than 0."""
        price = self.cleaned_data.get('price_pence')
        if price is not None and price <= 0:
            raise ValidationError('Price must be greater than 0 pence.')
        return price
    
    def clean_stock_qty(self):
        """Validate that stock quantity is not negative."""
        stock = self.cleaned_data.get('stock_qty')
        if stock is not None and stock < 0:
            raise ValidationError('Stock quantity cannot be negative.')
        return stock
    
    def clean_low_stock_threshold(self):
        """Validate that low stock threshold is not negative."""
        threshold = self.cleaned_data.get('low_stock_threshold')
        if threshold is not None and threshold < 0:
            raise ValidationError('Low stock threshold cannot be negative.')
        return threshold
    
    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        
        # Validate seasonal months if both are provided
        start_month = cleaned_data.get('seasonal_start_month')
        end_month = cleaned_data.get('seasonal_end_month')
        
        if start_month is not None and (start_month < 1 or start_month > 12):
            self.add_error('seasonal_start_month', 'Month must be between 1 and 12.')
        
        if end_month is not None and (end_month < 1 or end_month > 12):
            self.add_error('seasonal_end_month', 'Month must be between 1 and 12.')
        
        # Validate best_before_date is after harvest_date if both provided
        harvest = cleaned_data.get('harvest_date')
        best_before = cleaned_data.get('best_before_date')
        
        if harvest and best_before and best_before < harvest:
            self.add_error('best_before_date', 'Best before date cannot be earlier than harvest date.')
        
        return cleaned_data
    
    def save_allergens(self, product):
        """
        Save the allergen associations for a product.
        Call this after saving the product instance.
        """
        # Clear existing allergen links
        ProductAllergen.objects.filter(product=product).delete()
        
        # Create new allergen links
        allergens = self.cleaned_data.get('allergens', [])
        for allergen in allergens:
            ProductAllergen.objects.create(product=product, allergen=allergen)
    
    def load_allergens(self, product):
        """
        Load existing allergens for a product when editing.
        Call this when initializing the form for editing.
        """
        existing_allergens = Allergen.objects.filter(
            product_links__product=product
        )
        self.fields['allergens'].initial = existing_allergens


class ProductAllergenInlineForm(forms.ModelForm):
    """
    Inline form for managing individual ProductAllergen entries.
    Can be used with Django formsets if more granular control is needed.
    """
    
    class Meta:
        model = ProductAllergen
        fields = ['allergen']
        widgets = {
            'allergen': forms.Select(attrs={
                'class': 'form-control'
            })
        }