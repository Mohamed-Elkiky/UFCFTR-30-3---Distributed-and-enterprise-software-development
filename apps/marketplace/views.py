# apps/marketplace/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.db.models import Q, Avg

from apps.common.permissions import producer_required
from apps.notifications.services.low_stock import check_and_notify_low_stock
from apps.orders.models import CustomerOrder
from apps.reviews.forms import ReviewForm
from apps.reviews.models import ProductReview

from .models import Product, ProductCategory, ProductAllergen
from .forms import ProductForm
from .services.surplus import create_surplus_deal, get_active_surplus_deals, apply_surplus_discount


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

    products = list(products.prefetch_related('surplus_deal').order_by('-created_at')[:24])

    # Attach discounted_display to each product so the template can use it directly
    for p in products:
        discounted = apply_surplus_discount(p)
        p.discounted_display = f'£{discounted / 100:.2f}' if discounted < p.price_pence else None

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
    ).prefetch_related('surplus_deal').order_by('-created_at')

    return render(request, 'producer/product_list.html', {
        'products': products,
        'now': timezone.now(),
    })


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
    organic = request.GET.get('organic', '')

    products = Product.objects.filter(
        category=category
    ).exclude(
        availability='unavailable'
    ).order_by('-created_at')

    if organic == '1':
        products = products.filter(organic_certified=True)

    return render(request, 'marketplace/product_list.html', {
        'category': category,
        'products': products,
        'organic': organic,
    })


@producer_required
def update_stock(request, product_id):
    """POST only — update stock_qty and availability for a product (TC-011)."""
    if request.method != 'POST':
        return HttpResponseForbidden('POST only.')

    product = get_object_or_404(Product, id=product_id)

    if product.producer != request.user.producer_profile:
        return HttpResponseForbidden('You do not own this product.')

    raw_qty = request.POST.get('stock_qty', '').strip()
    availability = request.POST.get('availability', '').strip()

    try:
        stock_qty = int(raw_qty)
        if stock_qty < 0:
            raise ValueError
    except ValueError:
        messages.error(request, 'Stock quantity must be a whole number of 0 or more.')
        return redirect('marketplace:product_list')

    product.stock_qty = stock_qty
    if availability:
        product.availability = availability
    product.save()

    check_and_notify_low_stock(product)

    messages.success(request, f'Stock updated for "{product.name}".')
    return redirect('marketplace:product_list')


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    allergens = ProductAllergen.objects.filter(
        product=product
    ).select_related('allergen')

    images = product.images.all()

    food_miles = None
    if request.user.is_authenticated:
        try:
            from apps.logistics.services.distance import get_food_miles
            customer_profile = request.user.customer_profile
            if customer_profile.latitude and customer_profile.longitude:
                food_miles = get_food_miles(product, customer_profile)
        except Exception:
            pass

    reviews = ProductReview.objects.filter(product=product).select_related("customer").order_by("-created_at")
    average_stars = reviews.aggregate(avg=Avg("stars"))["avg"]
    review_count = reviews.count()

    review_form = ReviewForm()
    can_review = False
    has_review = False

    if request.user.is_authenticated and getattr(request.user, "is_customer", False):
        try:
            customer_profile = request.user.customer_profile

            can_review = CustomerOrder.objects.filter(
                customer=customer_profile,
                status=CustomerOrder.Status.DELIVERED,
                items__product=product,
            ).exists()

            has_review = ProductReview.objects.filter(
                product=product,
                customer=customer_profile,
            ).exists()
        except Exception:
            pass

    # Surplus pricing
    discounted_pence = apply_surplus_discount(product)
    has_surplus = discounted_pence < product.price_pence
    discounted_display = f'£{discounted_pence / 100:.2f}' if has_surplus else None
    try:
        surplus_deal = product.surplus_deal if has_surplus else None
    except Exception:
        surplus_deal = None

    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'allergens': allergens,
        'images': images,
        'food_miles': food_miles,
        'reviews': reviews,
        'average_stars': average_stars,
        'review_count': review_count,
        'review_form': review_form,
        'can_review': can_review,
        'has_review': has_review,
        'discounted_display': discounted_display,
        'surplus_deal': surplus_deal,
    })


def product_search(request):
    q = request.GET.get('q', '').strip()
    organic = request.GET.get('organic', '')

    products = Product.objects.filter(
        availability__in=['in_season', 'available_year_round']
    ).select_related('producer', 'category')

    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(producer__business_name__icontains=q)
        )

    if organic == '1':
        products = products.filter(organic_certified=True)

    products = products.order_by('-created_at')

    return render(request, 'marketplace/product_list.html', {
        'products': products,
        'query': q,
        'organic': organic,
    })


# =============================================================================
# SURPLUS DEALS VIEWS (TC-019)
# =============================================================================

def surplus_deals(request):
    qs = get_active_surplus_deals().select_related('product__producer', 'product__category')
    enriched = []
    for deal in qs:
        discounted_pence = apply_surplus_discount(deal.product)
        enriched.append({
            'deal': deal,
            'product': deal.product,
            'original_pence': deal.product.price_pence,
            'discounted_pence': discounted_pence,
            'original_display': f'£{deal.product.price_pence / 100:.2f}',
            'discounted_display': f'£{discounted_pence / 100:.2f}',
            'discount_pct': deal.discount_bp // 100,
        })
    return render(request, 'marketplace/surplus_deals.html', {'enriched_deals': enriched})


@producer_required
def mark_as_surplus(request, product_id):
    if request.method != 'POST':
        return HttpResponseForbidden('POST only.')

    product = get_object_or_404(Product, id=product_id)

    if product.producer != request.user.producer_profile:
        return HttpResponseForbidden('You do not own this product.')

    try:
        discount_percent = int(request.POST.get('discount_percent', 0))
        hours_valid = int(request.POST.get('hours_valid', 0))
    except (ValueError, TypeError):
        messages.error(request, 'Invalid discount or duration.')
        return redirect('marketplace:product_list')

    note = request.POST.get('note', '')

    try:
        create_surplus_deal(product, discount_percent, hours_valid, note=note)
        messages.success(request, f'Surplus deal created for "{product.name}".')
    except Exception as e:
        messages.error(request, str(e))

    return redirect('marketplace:product_list')


@producer_required
def cancel_surplus_deal(request, product_id):
    if request.method != 'POST':
        return HttpResponseForbidden('POST only.')

    product = get_object_or_404(Product, id=product_id)

    if product.producer != request.user.producer_profile:
        return HttpResponseForbidden('You do not own this product.')

    try:
        product.surplus_deal.delete()
        messages.success(request, f'Surplus deal for "{product.name}" cancelled.')
    except Product.surplus_deal.RelatedObjectDoesNotExist:
        messages.warning(request, 'No active surplus deal found for this product.')

    return redirect('marketplace:product_list')


def product_search_json(request):
    q = request.GET.get('q', '').strip()
    products = Product.objects.filter(
        availability__in=['in_season', 'available_year_round']
    ).select_related('producer', 'category').prefetch_related('images')

    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(producer__business_name__icontains=q)
        )

    results = []
    for p in products[:24]:
        img = p.images.first()
        if img and img.image:
            image_url = img.image.url
        elif img and img.url:
            image_url = img.url
        else:
            image_url = None

        results.append({
            'id': str(p.pk),
            'name': p.name,
            'url': f'/product/{p.pk}/',
            'price_display': p.price_display,
            'unit': p.unit,
            'category': p.category.name if p.category else '',
            'producer': p.producer.business_name if p.producer else '',
            'availability': p.availability,
            'organic_certified': p.organic_certified,
            'image_url': image_url,
        })

    return JsonResponse({'results': results})