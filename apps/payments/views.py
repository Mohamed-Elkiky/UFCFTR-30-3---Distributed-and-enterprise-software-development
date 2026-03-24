import csv
from datetime import date, timedelta
from collections import defaultdict

from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404

from apps.common.permissions import admin_required, producer_required
from apps.orders.models import CustomerOrder, ProducerOrder
from apps.payments.models import OrderCommission, ProducerSettlement
from apps.accounts.models import ProducerProfile


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
    default_from = today - timedelta(days=14)

    # ---- Parse filter params with safe fallback ----
    date_from_str = request.GET.get('date_from', '')
    date_to_str = request.GET.get('date_to', '')

    try:
        date_from = date.fromisoformat(date_from_str) if date_from_str else default_from
    except ValueError:
        date_from = default_from

    try:
        date_to = date.fromisoformat(date_to_str) if date_to_str else today
    except ValueError:
        date_to = today

    producer_filter = request.GET.get('producer', '')
    status_filter = request.GET.get('status', '')

    # ---- Build queryset ----
    commissions = (
        OrderCommission.objects
        .filter(
            created_at__date__gte=date_from,
            created_at__date__lte=date_to,
        )
        .select_related('customer_order', 'customer_order__customer')
        .order_by('-created_at')
    )

    # Filter by producer: only orders that have a ProducerOrder for this producer
    if producer_filter:
        commissions = commissions.filter(
            customer_order__producer_orders__producer_id=producer_filter
        ).distinct()

    # Filter by order status
    if status_filter:
        commissions = commissions.filter(customer_order__status=status_filter)

    # ---- Build row data ----
    rows = []
    for c in commissions:
        order = c.customer_order
        # Get producer breakdown for this order
        producer_orders = (
            ProducerOrder.objects
            .filter(customer_order=order)
            .select_related('producer')
        )
        producer_breakdown = []
        for po in producer_orders:
            producer_name = po.producer.business_name if po.producer else 'Unknown'
            po_gross = round(po.subtotal_pence / 100, 2)
            po_commission = round(po.commission_pence / 100, 2)
            po_payment = round(po.producer_payment_pence / 100, 2)
            producer_breakdown.append({
                'name': producer_name,
                'gross': po_gross,
                'commission': po_commission,
                'payment': po_payment,
                'status': po.get_status_display(),
            })

        num_producers = len(producer_breakdown)
        customer_name = '\u2014'
        if order.customer:
            customer_name = order.customer.full_name or str(order.customer)

        rows.append({
            'order_id': str(order.id),
            'order_id_short': str(order.id)[:8],
            'order_date': c.created_at.date(),
            'customer_name': customer_name,
            'order_status': order.get_status_display(),
            'order_status_raw': order.status,
            'gross': round(c.gross_pence / 100, 2),
            'commission': round(c.commission_pence / 100, 2),
            'net': round(c.net_pence / 100, 2),
            'num_producers': num_producers,
            'is_multi_vendor': num_producers > 1,
            'producer_breakdown': producer_breakdown,
            'payment_status': _get_payment_status(order),
        })

    # ---- Summary stats ----
    total_gross = round(sum(r['gross'] for r in rows), 2)
    total_commission = round(sum(r['commission'] for r in rows), 2)
    total_net = round(sum(r['net'] for r in rows), 2)
    total_orders = len(rows)

    # ---- Monthly summary ----
    monthly_base = OrderCommission.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    )
    if producer_filter:
        monthly_base = monthly_base.filter(
            customer_order__producer_orders__producer_id=producer_filter
        ).distinct()
    if status_filter:
        monthly_base = monthly_base.filter(customer_order__status=status_filter)

    monthly_qs = (
        monthly_base
        .annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(
            month_gross=Sum('gross_pence'),
            month_commission=Sum('commission_pence'),
            month_net=Sum('net_pence'),
            month_orders=Count('id'),
        )
        .order_by('-month')
    )
    monthly_summary = [
        {
            'month': m['month'],
            'gross': round((m['month_gross'] or 0) / 100, 2),
            'commission': round((m['month_commission'] or 0) / 100, 2),
            'net': round((m['month_net'] or 0) / 100, 2),
            'orders': m['month_orders'],
        }
        for m in monthly_qs
    ]

    # ---- Year-to-date totals ----
    year_start = date(today.year, 1, 1)
    ytd_agg = (
        OrderCommission.objects
        .filter(created_at__date__gte=year_start, created_at__date__lte=today)
        .aggregate(
            ytd_gross=Sum('gross_pence'),
            ytd_commission=Sum('commission_pence'),
            ytd_net=Sum('net_pence'),
            ytd_orders=Count('id'),
        )
    )
    ytd = {
        'gross': round((ytd_agg['ytd_gross'] or 0) / 100, 2),
        'commission': round((ytd_agg['ytd_commission'] or 0) / 100, 2),
        'net': round((ytd_agg['ytd_net'] or 0) / 100, 2),
        'orders': ytd_agg['ytd_orders'] or 0,
    }

    # ---- Producer list for filter dropdown ----
    producers = ProducerProfile.objects.order_by('business_name')

    # ---- CSV / Excel export ----
    fmt = request.GET.get('format', '')
    if fmt == 'csv':
        return _export_csv(rows, date_from, date_to)

    return render(request, 'admin/commission_report.html', {
        'rows': rows,
        'total_gross': total_gross,
        'total_commission': total_commission,
        'total_net': total_net,
        'total_orders': total_orders,
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
        'producers': producers,
        'producer_filter': producer_filter,
        'status_filter': status_filter,
        'status_choices': CustomerOrder.Status.choices,
        'monthly_summary': monthly_summary,
        'ytd': ytd,
    })


@admin_required
def admin_order_commission_detail(request, order_id):
    """Standalone detail view for a single order's commission breakdown."""
    order = get_object_or_404(
        CustomerOrder.objects.select_related('customer'),
        pk=order_id,
    )
    commission = get_object_or_404(OrderCommission, customer_order=order)

    producer_orders = (
        ProducerOrder.objects
        .filter(customer_order=order)
        .select_related('producer')
    )
    breakdown = []
    for po in producer_orders:
        breakdown.append({
            'producer': po.producer.business_name if po.producer else 'Unknown',
            'gross': round(po.subtotal_pence / 100, 2),
            'commission': round(po.commission_pence / 100, 2),
            'payment': round(po.producer_payment_pence / 100, 2),
            'status': po.get_status_display(),
        })

    customer_name = '\u2014'
    if order.customer:
        customer_name = order.customer.full_name or str(order.customer)

    return render(request, 'admin/commission_order_detail.html', {
        'order': order,
        'commission': commission,
        'breakdown': breakdown,
        'customer_name': customer_name,
        'gross': round(commission.gross_pence / 100, 2),
        'comm': round(commission.commission_pence / 100, 2),
        'net': round(commission.net_pence / 100, 2),
        'payment_status': _get_payment_status(order),
    })


# ---- Helpers ----

def _get_payment_status(order):
    """Return payment status string for an order."""
    try:
        txn = order.payment
        return txn.get_status_display()
    except Exception:
        return 'No payment recorded'


def _export_csv(rows, date_from, date_to):
    """Export detailed commission report as CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="commission_report_{date_from}_{date_to}.csv"'
    )
    writer = csv.writer(response)

    # Header
    writer.writerow([
        'Order ID', 'Order Date', 'Customer', 'Order Status', 'Payment Status',
        'Gross (\u00a3)', 'Commission 5% (\u00a3)', 'Net to Producers (\u00a3)',
        'Multi-vendor', 'Producer', 'Producer Gross (\u00a3)',
        'Producer Commission (\u00a3)', 'Producer Payment 95% (\u00a3)',
    ])

    for r in rows:
        if r['producer_breakdown']:
            for i, pb in enumerate(r['producer_breakdown']):
                writer.writerow([
                    r['order_id'] if i == 0 else '',
                    r['order_date'].isoformat() if i == 0 else '',
                    r['customer_name'] if i == 0 else '',
                    r['order_status'] if i == 0 else '',
                    r['payment_status'] if i == 0 else '',
                    f"{r['gross']:.2f}" if i == 0 else '',
                    f"{r['commission']:.2f}" if i == 0 else '',
                    f"{r['net']:.2f}" if i == 0 else '',
                    'Yes' if r['is_multi_vendor'] and i == 0 else ('No' if i == 0 else ''),
                    pb['name'],
                    f"{pb['gross']:.2f}",
                    f"{pb['commission']:.2f}",
                    f"{pb['payment']:.2f}",
                ])
        else:
            writer.writerow([
                r['order_id'], r['order_date'].isoformat(),
                r['customer_name'], r['order_status'], r['payment_status'],
                f"{r['gross']:.2f}", f"{r['commission']:.2f}", f"{r['net']:.2f}",
                'No', '', '', '', '',
            ])

    # Totals row
    total_gross = sum(r['gross'] for r in rows)
    total_commission = sum(r['commission'] for r in rows)
    total_net = sum(r['net'] for r in rows)
    writer.writerow([])
    writer.writerow([
        'TOTALS', '', '', '', '',
        f"{total_gross:.2f}", f"{total_commission:.2f}", f"{total_net:.2f}",
        '', '', '', '', '',
    ])
    writer.writerow([f'Total Orders: {len(rows)}'])
    writer.writerow([f'Report Period: {date_from} to {date_to}'])

    return response