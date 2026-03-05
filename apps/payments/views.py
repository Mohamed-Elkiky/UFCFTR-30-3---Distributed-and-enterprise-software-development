import csv
from datetime import date, timedelta

from django.http import HttpResponse
from django.shortcuts import render

from apps.common.permissions import admin_required, producer_required
from apps.payments.models import OrderCommission, ProducerSettlement


@producer_required
def producer_settlements(request):
    settlements = ProducerSettlement.objects.filter(
        producer=request.user.producer_profile
    ).order_by('-settlement_week__week_start')

    return render(request, 'producer/settlements.html', {
        'settlements': settlements,
    })


@admin_required
def admin_commission_report(request):
    today = date.today()
    default_from = today - timedelta(days=30)

    date_from_str = request.GET.get('date_from', default_from.isoformat())
    date_to_str = request.GET.get('date_to', today.isoformat())

    commissions = (
        OrderCommission.objects
        .filter(created_at__date__gte=date_from_str, created_at__date__lte=date_to_str)
        .select_related('customer_order')
        .order_by('created_at')
    )

    rows = [
        {
            'order_id': c.customer_order_id,
            'order_date': c.created_at.date().isoformat(),
            'gross': round(c.gross_pence / 100, 2),
            'commission': round(c.commission_pence / 100, 2),
            'net': round(c.net_pence / 100, 2),
        }
        for c in commissions
    ]

    total_gross = round(sum(r['gross'] for r in rows), 2)
    total_commission = round(sum(r['commission'] for r in rows), 2)
    total_net = round(sum(r['net'] for r in rows), 2)

    if request.GET.get('format') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="commission_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Order ID', 'Order Date', 'Gross (£)', 'Commission (£)', 'Net (£)'])
        for r in rows:
            writer.writerow([r['order_id'], r['order_date'], f"{r['gross']:.2f}", f"{r['commission']:.2f}", f"{r['net']:.2f}"])
        return response

    return render(request, 'admin/commission_report.html', {
        'rows': rows,
        'total_gross': total_gross,
        'total_commission': total_commission,
        'total_net': total_net,
        'date_from': date_from_str,
        'date_to': date_to_str,
    })