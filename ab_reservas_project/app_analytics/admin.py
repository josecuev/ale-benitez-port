from datetime import timedelta, date

from django.contrib import admin
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.urls import path
from django.utils import timezone

from .models import PageView, PageViewMonthly, VALID_PAGES


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _pct(part, total):
    if not total:
        return 0
    return round(part / total * 100)


def _build_stats(days_range: int):
    today = timezone.localdate()
    start = today - timedelta(days=days_range - 1)

    # PageViews agregados por página y día
    views_qs = (
        PageView.objects
        .filter(timestamp__date__gte=start)
        .annotate(day=TruncDate('timestamp'))
        .values('day', 'page')
        .annotate(count=Count('id'))
    )
    views_by_day: dict[date, dict[str, int]] = {}
    for row in views_qs:
        views_by_day.setdefault(row['day'], {})[row['page']] = row['count']

    # Importar modelos de reservas aquí para evitar dependencia circular
    from app_fractalia.models import PendingBooking, Booking

    pending_qs = (
        PendingBooking.objects
        .filter(created_at__date__gte=start)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'))
    )
    pending_by_day = {row['day']: row['count'] for row in pending_qs}

    confirmed_qs = (
        Booking.objects
        .filter(created_at__date__gte=start)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'))
    )
    confirmed_by_day = {row['day']: row['count'] for row in confirmed_qs}

    # Construir lista de días (más reciente primero)
    days = []
    max_portfolio = 1
    current = start
    while current <= today:
        d = views_by_day.get(current, {})
        row = {
            'date': current,
            'portfolio': d.get('portfolio', 0),
            'links': d.get('links', 0),
            'calendar': d.get('fractalia_calendar', 0),
            'pending': pending_by_day.get(current, 0),
            'confirmed': confirmed_by_day.get(current, 0),
        }
        days.append(row)
        if row['portfolio'] > max_portfolio:
            max_portfolio = row['portfolio']
        current += timedelta(days=1)

    days.reverse()

    # Sparkbar widths (max 80px)
    for day in days:
        day['portfolio_bar'] = round(day['portfolio'] / max_portfolio * 80)

    # Totales
    totals = {
        'portfolio': sum(d['portfolio'] for d in days),
        'links': sum(d['links'] for d in days),
        'calendar': sum(d['calendar'] for d in days),
        'pending': sum(d['pending'] for d in days),
        'confirmed': sum(d['confirmed'] for d in days),
        'unique_visitors': PageView.objects.filter(
            timestamp__date__gte=start
        ).values('ip_hash').distinct().count(),
    }

    # Funnel
    steps = [
        {'label': 'Visitas al portfolio', 'count': totals['portfolio'], 'color': '#3b82f6',
         'description': 'Personas que abrieron el portafolio'},
        {'label': 'Visitas al calendario', 'count': totals['calendar'], 'color': '#f59e0b',
         'description': 'Continuaron para ver disponibilidad'},
        {'label': 'Pre-reservas recibidas', 'count': totals['pending'], 'color': '#f97316',
         'description': 'Enviaron una solicitud de turno'},
        {'label': 'Reservas confirmadas',  'count': totals['confirmed'], 'color': '#22c55e',
         'description': 'Turno asignado y confirmado'},
    ]
    funnel_top = max((s['count'] for s in steps), default=1) or 1
    for i, step in enumerate(steps):
        step['pct_of_top']  = _pct(step['count'], funnel_top)
        prev = steps[i - 1]['count'] if i > 0 else step['count']
        step['pct_of_prev'] = _pct(step['count'], prev) if i > 0 else 100

    # Datos para Chart.js (orden cronológico)
    chart_days = list(reversed(days))
    _weekdays = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    chart_days_labels = [
        [_weekdays[d['date'].weekday()], d['date'].strftime('%-d/%m')]
        for d in chart_days
    ]

    cal = totals['calendar'] or 1
    cal_to_confirmed_pct = round(totals['confirmed'] / cal * 100)

    return {
        'totals': totals,
        'days': days,
        'funnel': steps,
        'funnel_top': funnel_top,
        'cal_to_confirmed_pct': cal_to_confirmed_pct,
        'chart_days_labels': chart_days_labels,
        'chart_portfolio':  [d['portfolio'] for d in chart_days],
        'chart_links':      [d['links']     for d in chart_days],
        'chart_calendar':   [d['calendar']  for d in chart_days],
        'chart_pending':    [d['pending']   for d in chart_days],
        'chart_confirmed':  [d['confirmed'] for d in chart_days],
    }


# ─── Admin PageView (lectura) ──────────────────────────────────────────────────

@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    change_list_template = 'admin/app_analytics/pageview/change_list.html'
    list_display  = ('get_page_display_name', 'timestamp', 'referrer')
    list_filter   = ('page',)
    readonly_fields = ('page', 'timestamp', 'ip_hash', 'referrer', 'user_agent_hash')
    ordering      = ('-timestamp',)
    date_hierarchy = 'timestamp'

    # No se pueden crear ni editar registros manualmente
    def has_add_permission(self, request):    return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

    @admin.display(description='Página')
    def get_page_display_name(self, obj):
        return obj.get_page_display()

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('dashboard/', self.admin_site.admin_view(self.dashboard_view), name='analytics_dashboard'),
        ]
        return custom + urls

    def dashboard_view(self, request):
        try:
            days_range = int(request.GET.get('days', 30))
            if days_range not in (7, 30, 90):
                days_range = 30
        except (ValueError, TypeError):
            days_range = 30

        import json
        from datetime import datetime as dt
        from app_fractalia.models import PendingBooking

        stats = _build_stats(days_range)

        # ── Pre-reservas sin gestionar ────────────────────────────────────────
        now = timezone.now()
        today = timezone.localdate()

        unmanaged_qs = (
            PendingBooking.objects
            .filter(status='PENDING')
            .select_related('resource')
            .order_by('date', 'start_time')
        )

        def _waiting_label(hours):
            if hours < 1:
                mins = int(hours * 60)
                return f'hace {mins} min'
            if hours < 48:
                return f'hace {int(hours)}h'
            days = int(hours // 24)
            return f'hace {days} días'

        unmanaged = []
        for pb in unmanaged_qs:
            booking_dt = timezone.make_aware(
                dt.combine(pb.date, pb.start_time)
            )
            expired = booking_dt < now
            hours_waiting = (now - pb.created_at).total_seconds() / 3600
            unmanaged.append({
                'obj': pb,
                'expired': expired,
                'hours_waiting': round(hours_waiting, 1),
                'days_waiting': int(hours_waiting // 24),
                'waiting_label': _waiting_label(hours_waiting),
                'admin_url': f'/admin/app_fractalia/pendingbooking/{pb.pk}/change/',
            })

        unmanaged_active  = [u for u in unmanaged if not u['expired']]
        unmanaged_expired = [u for u in unmanaged if u['expired']]

        # ── Solapamientos: PendingBookings PENDING que chocan con Booking CONFIRMED ──
        from app_fractalia.models import Booking
        confirmed_bookings = list(Booking.objects.filter(status='CONFIRMED').values(
            'pk', 'start_datetime', 'end_datetime'
        ))
        overlapping = []
        for u in unmanaged_active:
            pb = u['obj']
            pb_start = timezone.make_aware(dt.combine(pb.date, pb.start_time))
            pb_end   = timezone.make_aware(dt.combine(pb.date, pb.end_time))
            conflicts = [
                b for b in confirmed_bookings
                if b['start_datetime'] < pb_end and b['end_datetime'] > pb_start
            ]
            if conflicts:
                overlapping.append({
                    'obj': pb,
                    'conflicts_count': len(conflicts),
                    'hours_waiting': u['hours_waiting'],
                })

        # ── Tiempo de confirmación: PendingBooking.created_at → Booking.created_at ──
        # Se calcula para las pre-reservas CONFIRMED del período cuya Booking
        # tiene el código en notes (flujo normal de confirmación desde el admin).
        confirmed_pbs = PendingBooking.objects.filter(
            status='CONFIRMED',
            created_at__date__gte=today - timedelta(days=days_range - 1),
        ).values('reservation_code', 'created_at')

        response_hours = []
        for pb in confirmed_pbs:
            code = pb['reservation_code']
            booking = (
                Booking.objects
                .filter(notes__contains=code)
                .values('created_at')
                .first()
            )
            if booking and booking['created_at']:
                delta = (booking['created_at'] - pb['created_at']).total_seconds() / 3600
                if 0 < delta < 720:  # entre 0 y 30 días (excluir anomalías de seed)
                    response_hours.append(round(delta, 1))

        if response_hours:
            resp_avg = round(sum(response_hours) / len(response_hours), 1)
            resp_min = min(response_hours)
            resp_max = max(response_hours)
        else:
            resp_avg = resp_min = resp_max = None

        # ── Métricas ejecutivas de gestión (dentro del período seleccionado) ──
        period_start = today - timedelta(days=days_range - 1)

        all_period = PendingBooking.objects.filter(created_at__date__gte=period_start)
        total_period    = all_period.count()
        confirmed_count = all_period.filter(status='CONFIRMED').count()
        cancelled_count = all_period.filter(status='CANCELLED').count()

        # Vencidas sin gestionar en el período (status PENDING y fecha ya pasó)
        expired_unmanaged_count = sum(
            1 for pb in all_period.filter(status='PENDING')
            if timezone.make_aware(dt.combine(pb.date, pb.start_time)) < now
        )

        pending_conversion_rate = _pct(confirmed_count, total_period)
        pending_expired_rate    = _pct(expired_unmanaged_count, total_period)

        # ── Datos por día para gráfico apilado de gestión ─────────────────────
        from django.db.models.functions import TruncDate as TD

        def _pending_by_day_status(status_filter):
            qs = (
                all_period.filter(**status_filter)
                .annotate(day=TD('created_at'))
                .values('day')
                .annotate(count=Count('id'))
            )
            return {row['day']: row['count'] for row in qs}

        conf_by_day   = _pending_by_day_status({'status': 'CONFIRMED'})
        canc_by_day   = _pending_by_day_status({'status': 'CANCELLED'})

        # Vencidas sin acción: PENDING cuya fecha de turno < hoy, agrupadas por created_at date
        expired_pbs = [
            pb for pb in all_period.filter(status='PENDING')
            if timezone.make_aware(dt.combine(pb.date, pb.start_time)) < now
        ]
        expired_by_day: dict = {}
        for pb in expired_pbs:
            d = pb.created_at.date()
            expired_by_day[d] = expired_by_day.get(d, 0) + 1

        # Esperando respuesta: PENDING cuyo turno aún no llegó
        waiting_pbs = [
            pb for pb in all_period.filter(status='PENDING')
            if timezone.make_aware(dt.combine(pb.date, pb.start_time)) >= now
        ]
        waiting_by_day: dict = {}
        for pb in waiting_pbs:
            d = pb.created_at.date()
            waiting_by_day[d] = waiting_by_day.get(d, 0) + 1

        # Construir arrays en orden cronológico (igual que chart_days en stats)
        chart_days_ordered = list(reversed(stats['days']))  # más antiguo primero
        chart_pending_confirmed = [conf_by_day.get(d['date'], 0)   for d in chart_days_ordered]
        chart_pending_cancelled = [canc_by_day.get(d['date'], 0)   for d in chart_days_ordered]
        chart_pending_expired   = [expired_by_day.get(d['date'], 0) for d in chart_days_ordered]
        chart_pending_waiting   = [waiting_by_day.get(d['date'], 0) for d in chart_days_ordered]

        # ── Próximos 15 días con pre-reservas pendientes (vista ejecutiva) ─────
        upcoming_days = []
        for offset in range(15):
            day = today + timedelta(days=offset)
            pbs_day = PendingBooking.objects.filter(
                date=day, status='PENDING'
            ).select_related('resource').order_by('start_time')
            bookings_count = PendingBooking.objects.filter(
                date=day, status='CONFIRMED'
            ).count()
            upcoming_days.append({
                'date': day,
                'pending_count': pbs_day.count(),
                'confirmed_count': bookings_count,
                'bookings': [
                    {
                        'start': str(pb.start_time)[:5],
                        'end':   str(pb.end_time)[:5],
                        'client': pb.client_name or 'Sin nombre',
                        'status': pb.status,
                        'hours_waiting': round((now - pb.created_at).total_seconds() / 3600, 1),
                        'overlaps': any(
                            b['start_datetime'] < timezone.make_aware(dt.combine(pb.date, pb.end_time))
                            and b['end_datetime'] > timezone.make_aware(dt.combine(pb.date, pb.start_time))
                            for b in confirmed_bookings
                        ),
                    }
                    for pb in pbs_day
                ],
            })

        # Histórico mensual
        monthly = PageViewMonthly.objects.all().order_by('-year', '-month')[:24]

        # Agregar totales mensuales para el chart (todos los pages sumados por mes)
        monthly_map: dict[str, int] = {}
        for m in monthly:
            key = f"{m.year}/{m.month:02d}"
            monthly_map[key] = monthly_map.get(key, 0) + m.total_views
        chart_month_labels = list(reversed(list(monthly_map.keys())))
        chart_month_views  = list(reversed(list(monthly_map.values())))

        context = {
            **self.admin_site.each_context(request),
            **stats,
            'days_range': days_range,
            'monthly': monthly,
            'unmanaged_active': unmanaged_active,
            'unmanaged_expired': unmanaged_expired,
            'overlapping': overlapping,
            'pending_conversion_rate': pending_conversion_rate,
            'pending_expired_rate': pending_expired_rate,
            'resp_avg': resp_avg,
            'resp_min': resp_min,
            'resp_max': resp_max,
            'upcoming_days': upcoming_days,
            'today': today,
            'upcoming_days_json': json.dumps([
                {
                    'date': d['date'].strftime('%-d/%m'),
                    'full_date': (
                        ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'][d['date'].weekday()]
                        + d['date'].strftime(' %-d de ')
                        + ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'][d['date'].month - 1]
                    ),
                    'pending_count': d['pending_count'],
                    'confirmed_count': d['confirmed_count'],
                    'bookings': d['bookings'],
                }
                for d in upcoming_days
            ], ensure_ascii=False),
            'chart_month_labels': json.dumps(chart_month_labels),
            'chart_month_views':  json.dumps(chart_month_views),
            # Serializar listas para Chart.js
            'chart_days_labels': json.dumps(stats['chart_days_labels']),
            'chart_portfolio':   json.dumps(stats['chart_portfolio']),
            'chart_links':       json.dumps(stats['chart_links']),
            'chart_calendar':    json.dumps(stats['chart_calendar']),
            'chart_pending':     json.dumps(stats['chart_pending']),
            'chart_confirmed':   json.dumps(stats['chart_confirmed']),
            'chart_pending_confirmed': json.dumps(chart_pending_confirmed),
            'chart_pending_cancelled': json.dumps(chart_pending_cancelled),
            'chart_pending_expired':   json.dumps(chart_pending_expired),
            'chart_pending_waiting':   json.dumps(chart_pending_waiting),
            'title': f'Analytics — últimos {days_range} días',
            'has_permission': True,
        }
        return render(request, 'app_analytics/stats.html', context)


@admin.register(PageViewMonthly)
class PageViewMonthlyAdmin(admin.ModelAdmin):
    list_display = ('page', 'year', 'month', 'total_views', 'unique_visitors')
    list_filter  = ('page', 'year')
    ordering     = ('-year', '-month')

    def has_add_permission(self, request):    return False
    def has_change_permission(self, request, obj=None): return False
