# apps/content/views.py
"""
Views for the content app (TC-020).
Provides producer-only screens for listing and creating ContentPosts
(recipes, farm stories, storage guides).
"""

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from apps.common.permissions import producer_required

from .forms import ContentPostForm
from .models import ContentPost, ContentProductLink


@producer_required
def content_list(request):
    """
    List the producer's own ContentPosts, most recent first.
    """
    producer = request.user.producer_profile

    posts = (
        ContentPost.objects
        .filter(producer=producer)
        .prefetch_related('product_links__product')
        .order_by('-created_at')
    )

    return render(request, 'producer/content_list.html', {
        'posts': posts,
    })


@producer_required
def content_create(request):
    """
    Create a new ContentPost authored by the current producer, optionally
    linking it to one or more of the producer's own products.
    """
    producer = request.user.producer_profile

    if request.method == 'POST':
        form = ContentPostForm(request.POST, producer=producer)
        if form.is_valid():
            with transaction.atomic():
                post = form.save(commit=False)
                post.producer = producer
                post.save()

                # Create ContentProductLink rows for each selected product.
                # The form already restricts the queryset to the producer's
                # own products, so this is safe.
                for product in form.cleaned_data['products']:
                    ContentProductLink.objects.create(
                        content=post,
                        product=product,
                    )

            messages.success(
                request,
                f'"{post.title}" published successfully.',
            )
            return redirect('content:content_list')
    else:
        form = ContentPostForm(producer=producer)

    return render(request, 'producer/content_form.html', {
        'form': form,
    })


@producer_required
def content_delete(request, post_id):
    """
    Delete a ContentPost owned by the current producer.
    POST-only to prevent accidental deletes via stale GET links / prefetchers.
    Cascade removes any associated ContentProductLink rows automatically.
    """
    post = get_object_or_404(ContentPost, id=post_id)

    # Ownership check — producers can only delete their own posts.
    if post.producer != request.user.producer_profile:
        return HttpResponseForbidden('You do not own this post.')

    if request.method != 'POST':
        messages.warning(request, 'Invalid request method for deletion.')
        return redirect('content:content_list')

    title = post.title
    post.delete()
    messages.success(request, f'"{title}" has been deleted.')
    return redirect('content:content_list')


def public_stories(request):
    """
    Public listing of all published content — accessible to everyone (TC-020).
    Supports filtering by kind (recipe, farm_story, storage_guide) and
    seasonal_tag via GET parameters.
    """
    posts = ContentPost.objects.filter(is_published=True).select_related('producer')

    kind = request.GET.get('kind', '')
    season = request.GET.get('season', '')

    if kind in dict(ContentPost.Kind.choices):
        posts = posts.filter(kind=kind)
    if season in dict(ContentPost.SeasonalTag.choices):
        posts = posts.filter(seasonal_tag=season)

    return render(request, 'marketplace/stories.html', {
        'posts': posts,
        'current_kind': kind,
        'current_season': season,
        'kind_choices': ContentPost.Kind.choices,
        'season_choices': ContentPost.SeasonalTag.choices,
    })


def story_detail(request, post_id):
    """
    Public detail page for a single ContentPost (TC-020).
    Shows full body text, linked products, and producer info.
    """
    post = get_object_or_404(
        ContentPost.objects.select_related('producer'),
        id=post_id,
        is_published=True,
    )

    linked_products = post.product_links.select_related('product').all()

    return render(request, 'marketplace/story_detail.html', {
        'post': post,
        'linked_products': linked_products,
    })