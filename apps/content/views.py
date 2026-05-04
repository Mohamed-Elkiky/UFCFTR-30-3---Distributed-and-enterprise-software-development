# apps/content/views.py
"""
Views for the content app (TC-020).
Provides producer-only screens for listing and creating ContentPosts
(recipes, farm stories, storage guides).
"""

from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render

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