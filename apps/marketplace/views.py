# apps/marketplace/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.utils import timezone

from .models import Product, ProductCategory, ProductAllergen
from .forms import ProductForm


def home(request):
    """
    Marketplace homepage showing featured products and categories.
    """
    categories = ProductCategory.objects.all()
    products = Product.objects.filter(
        availability__isnull=False
    ).exclude(
        availability='unavailable'
    ).order_by('-created_at')[:8]
    
    context = {
        'categories': categories,
        'products': products,
    }
    return render(request, 'marketplace/home.html', context)


# =============================================================================
# PRODUCER PRODUCT MANAGEMENT VIEWS (TC-003, TC-011)
# =============================================================================

def producer_required(view_func):
    """
    Decorator that checks if the user is logged in and has a producer role.
    """
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to access this page.')
            return redirect('accounts:login')
        if not request.user.is_producer:
            messages.error(request, 'Access denied. Producer account required.')
            return HttpResponseForbidden('Producer access required.')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@producer_required
def product_list(request):
    """
    List all products belonging to the logged-in producer (TC-003, TC-011).
    """
    products = Product.objects.filter(
        producer=request.user.producer_profile
    ).order_by('-created_at')
    
    context = {
        'products': products,
    }
    return render(request, 'producer/product_list.html', context)


@login_required
@producer_required
def product_create(request):
    """
    Create a new product listing (TC-003).
    GET: Display empty ProductForm
    POST: Validate and save new product
    """
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            # Save the product but don't commit yet (we need to set producer)
            product = form.save(commit=False)
            product.producer = request.user.producer_profile
            product.created_at = timezone.now()
            product.updated_at = timezone.now()
            product.save()
            
            # Save allergen associations
            form.save_allergens(product)
            
            messages.success(request, f'Product "{product.name}" created successfully!')
            return redirect('marketplace:product_list')
    else:
        form = ProductForm()
    
    context = {
        'form': form,
        'action': 'Create',
    }
    return render(request, 'producer/product_form.html', context)


@login_required
@producer_required
def product_edit(request, product_id):
    """
    Edit an existing product (TC-003, TC-011).
    GET: Display ProductForm pre-filled with existing data
    POST: Validate and update product
    
    Authorization: Only the product's owner can edit.
    """
    product = get_object_or_404(Product, id=product_id)
    
    # Authorization check: ensure the producer owns this product
    if product.producer != request.user.producer_profile:
        messages.error(request, 'You do not have permission to edit this product.')
        return HttpResponseForbidden('You do not own this product.')
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save(commit=False)
            product.updated_at = timezone.now()
            product.save()
            
            # Save allergen associations
            form.save_allergens(product)
            
            messages.success(request, f'Product "{product.name}" updated successfully!')
            return redirect('marketplace:product_list')
    else:
        form = ProductForm(instance=product)
        # Load existing allergens for the product
        form.load_allergens(product)
    
    context = {
        'form': form,
        'product': product,
        'action': 'Edit',
    }
    return render(request, 'producer/product_form.html', context)


@login_required
@producer_required
def product_delete(request, product_id):
    """
    Delete a product (TC-011).
    POST only: Deletes the product and redirects to product list.
    
    Authorization: Only the product's owner can delete.
    """
    product = get_object_or_404(Product, id=product_id)
    
    # Authorization check: ensure the producer owns this product
    if product.producer != request.user.producer_profile:
        messages.error(request, 'You do not have permission to delete this product.')
        return HttpResponseForbidden('You do not own this product.')
    
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f'Product "{product_name}" has been deleted.')
        return redirect('marketplace:product_list')
    
    # If not POST, redirect back (delete should only be POST)
    messages.warning(request, 'Invalid request method for deletion.')
    return redirect('marketplace:product_list')


# =============================================================================
# CUSTOMER-FACING MARKETPLACE VIEWS (TC-004) - To be implemented in DESDG2-14
# =============================================================================

def category_list(request):
    """
    Display all product categories (TC-004).
    """
    categories = ProductCategory.objects.all()
    
    context = {
        'categories': categories,
    }
    return render(request, 'marketplace/category_list.html', context)


def product_list_by_category(request, category_id):
    """
    Display products filtered by category (TC-004).
    Only shows available products (not 'unavailable').
    """
    category = get_object_or_404(ProductCategory, id=category_id)
    products = Product.objects.filter(
        category=category
    ).exclude(
        availability='unavailable'
    ).order_by('-created_at')
    
    context = {
        'category': category,
        'products': products,
    }
    return render(request, 'marketplace/product_list.html', context)


def product_detail(request, product_id):
    """
    Display detailed product information including allergens (TC-004, TC-015).
    """
    product = get_object_or_404(Product, id=product_id)
    
    # Get allergens for this product (for TC-015)
    allergens = ProductAllergen.objects.filter(
        product=product
    ).select_related('allergen')
    
    # Get product images
    images = product.images.all()
    
    context = {
        'product': product,
        'allergens': allergens,
        'images': images,
    }
    return render(request, 'marketplace/product_detail.html', context)