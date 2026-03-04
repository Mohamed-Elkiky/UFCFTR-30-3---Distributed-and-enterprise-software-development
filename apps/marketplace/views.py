# apps/marketplace/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.db.models import Q

from apps.common.permissions import producer_required

from .models import Product, ProductCategory, ProductAllergen
from .forms import ProductForm


def home(request):
    categories = ProductCategory.objects.all()

    products = Product.objects.exclude(
        availability='unavailable'
    ).exclude(
        availability='out_of_season'
    ).select_related('producer', 'category').prefetch_related('allergen_links__allergen', 'images')

    q = request.GET.get('q', '').strip()
    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(producer__business_name__icontains=q)
        )

    category_id = request.GET.get('category', '').strip()
    if category_id:
        try:
            products = products.filter(category__id=int(category_id))
        except (ValueError, TypeError):
            category_id = ""

    if request.GET.get('organic'):
        products = products.filter(organic_certified=True)

    if request.GET.get('in_season'):
        products = products.filter(availability='in_season')

    products = products.order_by('-created_at')[:24]

    context = {
        'categories': categories,
        'products': products,
        'q': q,
        'selected_category': category_id,
        'filter_organic': request.GET.get('organic', ''),
        'filter_in_season': request.GET.get('in_season', ''),
    }
    return render(request, 'marketplace/home.html', context)


# =============================================================================
# PRODUCER PRODUCT MANAGEMENT VIEWS (TC-003, TC-011)
# =============================================================================

@producer_required
def product_list(request):
    products = Product.objects.filter(
        producer=request.user.producer_profile
    ).order_by('-created_at')

    return render(request, 'producer/product_list.html', {'products': products})


@producer_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.producer = request.user.producer_profile
            product.created_at = timezone.now()
            product.updated_at = timezone.now()
            product.save()
            form.save_allergens(product)
            form.save_image(product)
            messages.success(request, f'Product "{product.name}" created successfully!')
            return redirect('marketplace:product_list')
    else:
        form = ProductForm()

    return render(request, 'producer/product_form.html', {'form': form, 'action': 'Create'})


@producer_required
def product_edit(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if product.producer != request.user.producer_profile:
        messages.error(request, 'You do not have permission to edit this product.')
        return HttpResponseForbidden('You do not own this product.')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save(commit=False)
            product.updated_at = timezone.now()
            product.save()
            form.save_allergens(product)
            form.save_image(product)
            messages.success(request, f'Product "{product.name}" updated successfully!')
            return redirect('marketplace:product_list')
    else:
        form = ProductForm(instance=product)
        form.load_allergens(product)

    return render(request, 'producer/product_form.html', {
        'form': form,
        'product': product,
        'action': 'Edit',
    })


@producer_required
def product_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if product.producer != request.user.producer_profile:
        messages.error(request, 'You do not have permission to delete this product.')
        return HttpResponseForbidden('You do not own this product.')

    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f'Product "{product_name}" has been deleted.')
        return redirect('marketplace:product_list')

    messages.warning(request, 'Invalid request method for deletion.')
    return redirect('marketplace:product_list')


# =============================================================================
# CUSTOMER-FACING MARKETPLACE VIEWS (TC-004)
# =============================================================================

def category_list(request):
    categories = ProductCategory.objects.all()
    return render(request, 'marketplace/category_list.html', {'categories': categories})


def product_list_by_category(request, category_id):
    category = get_object_or_404(ProductCategory, id=category_id)
    products = Product.objects.filter(
        category=category
    ).exclude(
        availability='unavailable'
    ).order_by('-created_at')

    return render(request, 'marketplace/product_list.html', {
        'category': category,
        'products': products,
    })


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    allergens = ProductAllergen.objects.filter(
        product=product
    ).select_related('allergen')

    images = product.images.all()

    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'allergens': allergens,
        'images': images,
    })


def product_search(request):
    q = request.GET.get('q', '').strip()

    products = Product.objects.filter(
        availability__in=['in_season', 'available_year_round']
    ).select_related('producer', 'category')

    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(producer__business_name__icontains=q)
        )

    products = products.order_by('-created_at')

    return render(request, 'marketplace/product_list.html', {
        'products': products,
        'query': q,
    })