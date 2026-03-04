from django.shortcuts import render
from apps.common.permissions import producer_required
from apps.payments.models import ProducerSettlement


@producer_required
def producer_settlements(request):
    settlements = ProducerSettlement.objects.filter(
        producer=request.user.producer_profile
    ).order_by('-settlement_week__week_start')

    return render(request, 'producer/settlements.html', {
        'settlements': settlements,
    })