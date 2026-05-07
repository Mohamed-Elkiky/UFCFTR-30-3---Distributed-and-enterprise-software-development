# apps/marketplace/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.db.models import Q, Avg, Case, When, IntegerField

from apps.content.models import ContentProductLink
from apps.common.permissions import producer_required
from apps.notifications.services.low_stock import check_and_notify_low_stock
from apps.orders.models import CustomerOrder
from apps.reviews.forms import ReviewForm
from apps.reviews.models import ProductReview

from .models import Product, ProductCategory, ProductAllergen
from .forms import ProductForm
from .services.surplus import create_surplus_deal, get_active_surplus_deals, apply_surplus_discount


def _annotate_food_miles(products, user):
    """Attach ``food_miles`` and ``within_20`` to each product for a logged-in buyer."""
    if not (user.is_authenticated and hasattr(user, 'customer_profile')):
        return
    cp = user.customer_profile
    if not (cp.latitude and cp.longitude):
        return
    from apps.logistics.services.distance import get_food_miles
    for p in products:
        miles = get_food_miles(p, cp)
        p.food_miles = miles
        p.within_20 = (miles <= 20.0) if miles is not None else None


def _get_suggested_products(user, limit=6):
    """Return AI-powered suggestions for a logged-in customer, or a
    seasonal fallback for anonymous / non-customer users."""
    from .services.ai_client import get_suggestions

    available = Product.objects.exclude(
        availability='unavailable'
    ).exclude(
        availability='out_of_season'
    ).filter(stock_qty__gt=0).select_related('producer', 'category').prefetch_related('images')

    print(f"[suggestions] user authenticated={user.is_authenticated}, "
          f"has_customer_profile={hasattr(user, 'customer_profile') if user.is_authenticated else 'N/A'}, "
          f"available products={available.count()}")

    # Try the AI service for logged-in customers
    if user.is_authenticated and hasattr(user, 'customer_profile'):
        raw = get_suggestions(str(user.pk), top_n=limit)
        print(f"[suggestions] AI response: {raw}")
        if raw:
            q_filter = Q()
            for item in raw:
                term = item.get('product', '')
                if term:
                    q_filter |= Q(name__icontains=term) | Q(category__name__icontains=term)
            if q_filter:
                matched = list(available.filter(q_filter)[:limit])
                print(f"[suggestions] matched {len(matched)} products from AI")
                if matched:
                    return matched

    # Fallback: in-season first, then year-round, newest first
    fallback = list(available.order_by(
        Case(
            When(availability='in_season', then=0),
            default=1,
            output_field=IntegerField(),
        ),
        '-created_at',
    )[:limit])
    print(f"[suggestions] fallback returning {len(fallback)} products")
    return fallback


def _get_homepage_deals(limit=6):
    """Active surplus deals enriched with display prices."""
    deals_qs = get_active_surplus_deals().select_related(
        'product__producer', 'product__category'
    ).prefetch_related('product__images')[:limit]

    enriched = []
    for deal in deals_qs:
        p = deal.product
        discounted = apply_surplus_discount(p)
        p.discounted_display = f'£{discounted / 100:.2f}' if discounted < p.price_pence else None
        p.discount_pct = deal.discount_bp // 100
        enriched.append(p)
    return enriched


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
            Q(name__icontains=q) | Q(description__icontains=q) |
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

    # Attach food_miles to each product for logged-in buyers (TC-013)
    _annotate_food_miles(products, request.user)

    # AI-powered suggestions + active surplus deals for homepage sections
    # Hide suggestions when the user is actively filtering
    has_filters = q or category_id or request.GET.get('organic') or request.GET.get('in_season')
    suggested = [] if has_filters else _get_suggested_products(request.user)
    deals = _get_homepage_deals()

    # Producer's own products for "Your Products" section on homepage
    producer_products = []
    if request.user.is_authenticated and request.user.is_producer:
        producer_products = list(
            Product.objects.filter(producer=request.user.producer_profile)
            .select_related('category')
            .prefetch_related('images')
            .order_by('-created_at')[:6]
        )

    context = {
        'categories': categories,
        'products': products,
        'suggested_products': suggested,
        'producer_products': producer_products,
        'deal_products': deals,
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
            check_and_notify_low_stock(product)
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


@producer_required
def quality_check(request):
    """Upload a produce photo and get an AI quality grade."""
    from .services.ai_client import check_quality

    result = None
    if request.method == 'POST' and request.FILES.get('image'):
        image_file = request.FILES['image']
        image_bytes = image_file.read()
        result = check_quality(image_bytes)

        if result is None:
            messages.error(request, 'Quality check service is currently unavailable. Please try again later.')

    return render(request, 'producer/quality_check.html', {'result': result})


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
    ).select_related('producer').order_by('-created_at')

    if organic == '1':
        products = products.filter(organic_certified=True)

    products = list(products)
    _annotate_food_miles(products, request.user)

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
    within_20 = None
    if request.user.is_authenticated:
        try:
            from apps.logistics.services.distance import get_food_miles
            customer_profile = request.user.customer_profile
            if customer_profile.latitude and customer_profile.longitude:
                food_miles = get_food_miles(product, customer_profile)
                if food_miles is not None:
                    within_20 = food_miles <= 20.0
        except Exception:
            pass

    reviews = ProductReview.objects.filter(product=product).select_related("customer").order_by("-created_at")
    average_stars = reviews.aggregate(avg=Avg("stars"))["avg"]
    review_count = reviews.count()

    review_form = ReviewForm()
    can_review = False
    has_review = False

    buyer_roles = {"customer", "community_group", "restaurant"}
    if request.user.is_authenticated and getattr(request.user, "role", None) in buyer_roles:
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

    # Linked content (recipes, farm stories, storage guides) — TC-020
    linked_content = ContentProductLink.objects.filter(
        product=product
    ).select_related('content')

    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'allergens': allergens,
        'images': images,
        'food_miles': food_miles,
        'within_20': within_20,
        'reviews': reviews,
        'average_stars': average_stars,
        'review_count': review_count,
        'review_form': review_form,
        'can_review': can_review,
        'has_review': has_review,
        'discounted_display': discounted_display,
        'surplus_deal': surplus_deal,
        'linked_content': linked_content
    })


def product_search(request):
    q = request.GET.get('q', '').strip()
    organic = request.GET.get('organic', '')

    products = Product.objects.filter(
        availability__in=['in_season', 'available_year_round']
    ).select_related('producer', 'category')

    if q:
        products = products.filter(
            Q(name__icontains=q) | Q(description__icontains=q) |
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
# API ENDPOINTS (TC-024)
# =============================================================================

def api_products(request):
    """
    JSON API endpoint for dynamic product selection (TC-024).
    Returns products with availability status for AJAX-based selectors.
    
    Query params:
    - in_season: 'true' to return only in-season products
    - producer_id: filter by producer ID
    - category_id: filter by category ID
    - search: search by name or producer name
    - limit: max results (default: 100)
    
    Response format:
    {
        'products': [
            {
                'id': '123e4567-e89b-12d3-a456-426614174000',
                'name': 'Organic Tomatoes',
                'producer': 'Bristol Valley Farm',
                'category': 'Vegetables',
                'price_pence': 250,
                'price_display': '£2.50',
                'stock_qty': 50,
                'availability': 'in_season',
                'available': true
            },
            ...
        ]
    }
    """
    from django.core.paginator import Paginator
    
    # Start with base queryset
    products = Product.objects.select_related('producer', 'category')
    
    # Filter by seasonal availability
    if request.GET.get('in_season') == 'true':
        products = products.filter(availability=Product.AvailabilityStatus.IN_SEASON)
    
    # Filter by producer
    producer_id = request.GET.get('producer_id', '').strip()
    if producer_id:
        products = products.filter(producer__id=producer_id)
    
    # Filter by category
    category_id = request.GET.get('category_id', '').strip()
    if category_id:
        products = products.filter(category__id=category_id)
    
    # Search
    search_q = request.GET.get('search', '').strip()
    if search_q:
        products = products.filter(
            Q(name__icontains=search_q) |
            Q(producer__business_name__icontains=search_q) |
            Q(category__name__icontains=search_q)
        )
    
    # Order by name
    products = products.order_by('name')
    
    # Pagination
    limit = min(int(request.GET.get('limit', 100)), 1000)  # Max 1000
    paginator = Paginator(products, limit)
    page = paginator.get_page(request.GET.get('page', 1))
    
    # Serialize response
    product_list = [
        {
            'id': str(p.id),
            'name': p.name,
            'producer': p.producer.business_name if p.producer else 'Unknown',
            'category': p.category.name if p.category else 'Uncategorized',
            'price_pence': p.price_pence,
            'price_display': f'£{p.price_pence / 100:.2f}',
            'stock_qty': p.stock_qty,
            'availability': p.availability,
            'available': p.availability not in ['unavailable', 'out_of_season'] and p.stock_qty > 0,
        }
        for p in page.object_list
    ]
    
    return JsonResponse({
        'products': product_list,
        'count': paginator.count,
        'page': page.number,
        'total_pages': paginator.num_pages,
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
            Q(name__icontains=q) | Q(description__icontains=q) |
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
            'stock_qty': p.stock_qty,
        })

    return JsonResponse({'results': results})