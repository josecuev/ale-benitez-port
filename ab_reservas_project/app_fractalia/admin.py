from django.contrib import admin, messages
from django.utils import timezone
from django.utils.safestring import mark_safe
from datetime import datetime, date as date_cls
import re
from .models import Resource, WeeklyAvailability, Booking, PendingBooking


class EstadoGestionFilter(admin.SimpleListFilter):
    """Filtro que replica los 3 paneles del dashboard de analytics."""
    title = 'Estado de gestión'
    parameter_name = 'gestion'

    def lookups(self, request, model_admin):
        return [
            ('vencidas',    '⚠️  Vencidas sin respuesta'),
            ('activas',     '🕐  Activas sin confirmar'),
            ('conflicto',   '🔴  Con conflicto de horario'),
            ('confirmadas', '✅  Confirmadas'),
            ('respondidas', '💬  Respondidas'),
            ('canceladas',  '❌  Canceladas'),
        ]

    def queryset(self, request, queryset):
        today = date_cls.today()
        if self.value() == 'vencidas':
            return queryset.filter(status='PENDING', date__lt=today)
        if self.value() == 'activas':
            return queryset.filter(status='PENDING', date__gte=today)
        if self.value() == 'conflicto':
            # PRE-reservas PENDING activas que solapan con un Booking confirmado
            pending_activas = queryset.filter(status='PENDING', date__gte=today)
            confirmed_bookings = list(
                Booking.objects.filter(status='CONFIRMED')
                .values('start_datetime', 'end_datetime')
            )
            conflicting_ids = []
            for pb in pending_activas:
                pb_start = timezone.make_aware(datetime.combine(pb.date, pb.start_time))
                pb_end   = timezone.make_aware(datetime.combine(pb.date, pb.end_time))
                if any(
                    b['start_datetime'] < pb_end and b['end_datetime'] > pb_start
                    for b in confirmed_bookings
                ):
                    conflicting_ids.append(pb.pk)
            return queryset.filter(pk__in=conflicting_ids)
        if self.value() == 'confirmadas':
            return queryset.filter(status='CONFIRMED')
        if self.value() == 'respondidas':
            return queryset.filter(status='RESPONDED')
        if self.value() == 'canceladas':
            return queryset.filter(status='CANCELLED')


class WeeklyAvailabilityInline(admin.TabularInline):
    model = WeeklyAvailability
    extra = 1


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'whatsapp_number', 'active')
    list_editable = ('active',)
    inlines = [WeeklyAvailabilityInline]


@admin.register(WeeklyAvailability)
class WeeklyAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('resource', 'weekday', 'start_time', 'end_time')
    list_filter = ('resource', 'weekday')
    ordering = ('resource', 'weekday')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('resource', 'formatted_date', 'end_datetime', 'client_phone', 'status_display', 'whatsapp_contact')
    list_filter = ('resource', 'status', 'start_datetime')
    search_fields = ('resource__name', 'notes', 'client_phone')
    readonly_fields = ('created_at', 'whatsapp_link_display')
    date_hierarchy = 'start_datetime'
    ordering = ('start_datetime',)
    actions = ['cancelar', 'reactivar']
    fieldsets = (
        ('Información de la reserva', {
            'fields': ('resource', 'status', 'client_phone')
        }),
        ('Horario', {
            'fields': ('start_datetime', 'end_datetime')
        }),
        ('Contacto', {
            'fields': ('whatsapp_link_display',)
        }),
        ('Notas', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def formatted_date(self, obj):
        """Format date as: martes, 25 de julio de 2026"""
        date = obj.start_datetime.date()
        time = obj.start_datetime.strftime('%H:%M')

        days = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        months = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

        day_name = days[date.weekday()]
        month_name = months[date.month - 1]

        formatted = f'{day_name.capitalize()}, {date.day} de {month_name} de {date.year} - {time}'
        return formatted
    formatted_date.short_description = 'Fecha'

    def status_display(self, obj):
        colors = {
            'CONFIRMED': 'green',
            'CANCELLED': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{obj.get_status_display()}</span>')
    status_display.short_description = 'Estado'

    def _build_whatsapp_url(self, obj):
        """Helper method to build WhatsApp URL with message"""
        if not obj.client_phone:
            return None

        date = obj.start_datetime.date()
        start_time = obj.start_datetime.strftime('%H:%M')
        end_time = obj.end_datetime.strftime('%H:%M')

        days = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        months = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

        day_name = days[date.weekday()]
        month_name = months[date.month - 1]
        date_str = f'{day_name.capitalize()}, {date.day} de {month_name} de {date.year}'

        resource_name = obj.resource.name
        code = ''

        # Extract code from notes if available
        if obj.notes:
            match = re.search(r'Código de reserva: (\w+)', obj.notes)
            if match:
                code = f' (Código: {match.group(1)})'

        message = f'Hola, te escribo en relacion a tu reserva en {resource_name} el {date_str} de {start_time} a {end_time}{code}.'

        return f"https://wa.me/{obj.resource.whatsapp_number}?text={message}"

    def whatsapp_contact(self, obj):
        """Display link in list view"""
        if not obj.client_phone:
            return mark_safe('<span style="color: #ccc;">—</span>')

        url = self._build_whatsapp_url(obj)
        if not url:
            return mark_safe('<span style="color: #ccc;">—</span>')

        client_info = f'{obj.client_phone}'
        if hasattr(obj, 'client_name') and obj.client_name:
            client_info = f'{obj.client_name} - {obj.client_phone}'

        return mark_safe(
            f'<a href="{url}" target="_blank" '
            f'style="background-color: #25D366; color: white; padding: 6px 12px; '
            f'border-radius: 4px; text-decoration: none; font-weight: bold; font-size: 12px;">'
            f'{client_info}</a>'
        )
    whatsapp_contact.short_description = 'Contacto'

    def whatsapp_link_display(self, obj):
        """Display link in detail view"""
        if not obj.client_phone:
            return mark_safe('<span style="color: #ccc;">Sin teléfono registrado</span>')

        url = self._build_whatsapp_url(obj)
        if not url:
            return mark_safe('<span style="color: #ccc;">Sin teléfono registrado</span>')

        client_info = f'{obj.client_phone}'
        if hasattr(obj, 'client_name') and obj.client_name:
            client_info = f'{obj.client_name} - {obj.client_phone}'

        return mark_safe(
            f'<a href="{url}" target="_blank" '
            f'style="background-color: #25D366; color: white; padding: 10px 16px; '
            f'border-radius: 4px; text-decoration: none; font-weight: bold; display: inline-block;">'
            f'Contactar por WhatsApp: {client_info}</a>'
        )
    whatsapp_link_display.short_description = 'Enviar mensaje'

    def cancelar(self, request, queryset):
        """Cambiar estado de CONFIRMED a CANCELLED y marcar PendingBooking padre como CANCELLED"""
        cancelled_count = 0
        incompatible_count = 0
        for booking in queryset:
            if booking.status == 'CONFIRMED':
                booking.status = 'CANCELLED'
                booking.save()
                cancelled_count += 1

                # Buscar y marcar la PendingBooking padre como CANCELLED
                if booking.notes:
                    match = re.search(r'Código de reserva: (\w+)', booking.notes)
                    if match:
                        code = match.group(1)
                        try:
                            pending = PendingBooking.objects.get(reservation_code=code)
                            pending.status = 'CANCELLED'
                            pending.save()
                        except PendingBooking.DoesNotExist:
                            pass
            else:
                incompatible_count += 1

        if cancelled_count > 0:
            mensaje = f'{cancelled_count} reserva cancelada.' if cancelled_count == 1 else f'{cancelled_count} reservas canceladas.'
            self.message_user(request, mensaje, messages.SUCCESS)
        if incompatible_count > 0:
            palabra = 'reserva' if incompatible_count == 1 else 'reservas'
            self.message_user(
                request,
                f'{incompatible_count} {palabra} no estaba en estado Confirmada.',
                messages.WARNING
            )

    def reactivar(self, request, queryset):
        """Cambiar estado de CANCELLED a CONFIRMED y marcar PendingBooking padre como CONFIRMED"""
        reactivated_count = 0
        incompatible_count = 0
        for booking in queryset:
            if booking.status == 'CANCELLED':
                booking.status = 'CONFIRMED'
                booking.save()
                reactivated_count += 1

                # Buscar y marcar la PendingBooking padre como CONFIRMED
                if booking.notes:
                    match = re.search(r'Código de reserva: (\w+)', booking.notes)
                    if match:
                        code = match.group(1)
                        try:
                            pending = PendingBooking.objects.get(reservation_code=code)
                            pending.status = 'CONFIRMED'
                            pending.save()
                        except PendingBooking.DoesNotExist:
                            pass
            else:
                incompatible_count += 1

        if reactivated_count > 0:
            mensaje = f'{reactivated_count} reserva reactivada.' if reactivated_count == 1 else f'{reactivated_count} reservas reactivadas.'
            self.message_user(request, mensaje, messages.SUCCESS)
        if incompatible_count > 0:
            palabra = 'reserva' if incompatible_count == 1 else 'reservas'
            self.message_user(
                request,
                f'{incompatible_count} {palabra} no estaba en estado Cancelada.',
                messages.WARNING
            )

    cancelar.short_description = 'Cancelar'
    reactivar.short_description = 'Reactivar'


@admin.register(PendingBooking)
class PendingBookingAdmin(admin.ModelAdmin):
    list_display = (
        'estado_gestion', 'formatted_date', 'client_name',
        'resource', 'recibida_hace', 'whatsapp_link_list',
    )
    list_filter = (EstadoGestionFilter, 'resource')
    search_fields = ('reservation_code', 'client_name', 'client_phone')
    readonly_fields = ('reservation_code', 'created_at', 'whatsapp_link_display')
    ordering = ('date', 'start_time')
    date_hierarchy = 'date'
    actions = ['confirmar', 'responder', 'deshacer']
    fieldsets = (
        ('Información del cliente', {
            'fields': ('client_name', 'client_phone', 'whatsapp_link_display')
        }),
        ('Detalles de la pre-reserva', {
            'fields': ('reservation_code', 'resource', 'date', 'start_time', 'end_time', 'status')
        }),
        ('Notas', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def formatted_date(self, obj):
        """Format date as: martes, 25 de julio de 2026"""
        date = obj.date

        days = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        months = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

        day_name = days[date.weekday()]
        month_name = months[date.month - 1]

        formatted = f'{day_name.capitalize()}, {date.day} de {month_name} de {date.year}'
        return formatted
    formatted_date.short_description = 'Fecha'

    def estado_gestion(self, obj):
        today = date_cls.today()
        if obj.status == 'PENDING':
            if obj.date < today:
                return mark_safe(
                    '<span style="color:#b91c1c; font-weight:700; font-size:12px;">'
                    '⚠️ Vencida</span>'
                )
            else:
                return mark_safe(
                    '<span style="color:#c2410c; font-weight:700; font-size:12px;">'
                    '🕐 Pendiente</span>'
                )
        elif obj.status == 'CONFIRMED':
            return mark_safe(
                '<span style="color:#15803d; font-weight:700; font-size:12px;">'
                '✅ Confirmada</span>'
            )
        elif obj.status == 'RESPONDED':
            return mark_safe(
                '<span style="color:#0369a1; font-weight:700; font-size:12px;">'
                '💬 Respondida</span>'
            )
        elif obj.status == 'CANCELLED':
            return mark_safe(
                '<span style="color:#6b7280; font-weight:700; font-size:12px;">'
                '❌ Cancelada</span>'
            )
        return mark_safe(f'<span style="color:#888;">{obj.get_status_display()}</span>')
    estado_gestion.short_description = 'Estado'

    def recibida_hace(self, obj):
        from django.utils import timezone as tz
        delta = tz.now() - obj.created_at
        hours = delta.total_seconds() / 3600
        if hours < 1:
            label = f'{int(delta.total_seconds() / 60)} min'
        elif hours < 48:
            label = f'{int(hours)}h'
        else:
            label = f'{int(hours / 24)} días'
        if obj.status == 'PENDING' and obj.date < date_cls.today():
            color = '#b91c1c'
        elif obj.status == 'PENDING':
            color = '#c2410c'
        elif obj.status == 'RESPONDED':
            color = '#0369a1'
        else:
            color = '#9ca3af'
        return mark_safe(f'<span style="color:{color}; font-size:12px;">hace {label}</span>')
    recibida_hace.short_description = 'Recibida'

    def _build_whatsapp_url(self, obj):
        """Helper method to build WhatsApp URL with message"""
        if not obj.client_phone:
            return None

        date = obj.date
        start_time = obj.start_time.strftime('%H:%M')
        end_time = obj.end_time.strftime('%H:%M')

        days = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        months = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

        day_name = days[date.weekday()]
        month_name = months[date.month - 1]
        date_str = f'{day_name.capitalize()}, {date.day} de {month_name} de {date.year}'

        resource_name = obj.resource.name
        code = obj.reservation_code

        message = (
            f'Hola, te escribo en relacion a tu pre-reserva en {resource_name} '
            f'el {date_str} de {start_time} a {end_time} (Código: {code}).'
        )

        return f"https://wa.me/{obj.resource.whatsapp_number}?text={message}"

    def whatsapp_link_list(self, obj):
        """Display preformatted WhatsApp link in list view"""
        if not obj.client_phone:
            return mark_safe('<span style="color: #ccc;">—</span>')

        url = self._build_whatsapp_url(obj)
        if not url:
            return mark_safe('<span style="color: #ccc;">—</span>')

        client_info = f'{obj.client_phone}'
        if obj.client_name:
            client_info = f'{obj.client_name} - {obj.client_phone}'

        return mark_safe(
            f'<a href="{url}" target="_blank" '
            f'style="background-color: #25D366; color: white; padding: 8px 14px; '
            f'border-radius: 4px; text-decoration: none; font-weight: bold; font-size: 13px; '
            f'display: inline-block;">'
            f'WhatsApp: {client_info}</a>'
        )
    whatsapp_link_list.short_description = 'Enviar mensaje'

    def whatsapp_link_display(self, obj):
        """Display link in detail view"""
        if not obj.client_phone:
            return mark_safe('<span style="color: #ccc;">Sin teléfono registrado</span>')

        url = self._build_whatsapp_url(obj)
        if not url:
            return mark_safe('<span style="color: #ccc;">Sin teléfono registrado</span>')

        client_info = f'{obj.client_phone}'
        if obj.client_name:
            client_info = f'{obj.client_name} - {obj.client_phone}'

        return mark_safe(
            f'<a href="{url}" target="_blank" '
            f'style="background-color: #25D366; color: white; padding: 10px 16px; '
            f'border-radius: 4px; text-decoration: none; font-weight: bold; display: inline-block;">'
            f'Contactar por WhatsApp: {client_info}</a>'
        )
    whatsapp_link_display.short_description = 'Enviar mensaje'

    def confirmar(self, request, queryset):
        """PENDING/REJECTED → CONFIRMED: Crea Booking y marca como confirmada"""
        confirmed_count = 0
        incompatible_count = 0
        for pending in queryset:
            if pending.status in ('PENDING', 'REJECTED'):
                try:
                    start_dt = timezone.make_aware(
                        datetime.combine(pending.date, pending.start_time)
                    )
                    end_dt = timezone.make_aware(
                        datetime.combine(pending.date, pending.end_time)
                    )

                    Booking.objects.create(
                        resource=pending.resource,
                        start_datetime=start_dt,
                        end_datetime=end_dt,
                        status='CONFIRMED',
                        client_phone=pending.client_phone,
                        notes=f'Código de reserva: {pending.reservation_code}'
                    )
                    pending.status = 'CONFIRMED'
                    pending.save()
                    confirmed_count += 1
                except Exception as e:
                    error_msg = str(e).replace('["__all__"]', '').replace('{', '').replace('}', '').strip("'\"")
                    self.message_user(
                        request,
                        f'No se pudo confirmar {pending.reservation_code}: {error_msg}',
                        messages.ERROR
                    )
            else:
                incompatible_count += 1

        if confirmed_count > 0:
            mensaje = f'{confirmed_count} solicitud confirmada.' if confirmed_count == 1 else f'{confirmed_count} solicitudes confirmadas.'
            self.message_user(request, mensaje, messages.SUCCESS)
        if incompatible_count > 0:
            palabra = 'solicitud' if incompatible_count == 1 else 'solicitudes'
            self.message_user(
                request,
                f'{incompatible_count} {palabra} no estaba Pendiente o Rechazada.',
                messages.WARNING
            )

    def deshacer(self, request, queryset):
        """CONFIRMED → PENDING: Borra Booking asociado y vuelve a PENDING"""
        undone_count = 0
        incompatible_count = 0
        for pending in queryset:
            if pending.status == 'CONFIRMED':
                try:
                    Booking.objects.filter(
                        resource=pending.resource,
                        notes__contains=pending.reservation_code
                    ).delete()
                    pending.status = 'PENDING'
                    pending.save()
                    undone_count += 1
                except Exception as e:
                    error_msg = str(e).replace('["__all__"]', '').replace('{', '').replace('}', '').strip("'\"")
                    self.message_user(
                        request,
                        f'No se pudo deshacer {pending.reservation_code}: {error_msg}',
                        messages.ERROR
                    )
            else:
                incompatible_count += 1

        if undone_count > 0:
            mensaje = f'{undone_count} solicitud volvió a Pendiente.' if undone_count == 1 else f'{undone_count} solicitudes volvieron a Pendiente.'
            self.message_user(request, mensaje, messages.SUCCESS)
        if incompatible_count > 0:
            palabra = 'solicitud' if incompatible_count == 1 else 'solicitudes'
            self.message_user(
                request,
                f'{incompatible_count} {palabra} no estaba Confirmada.',
                messages.WARNING
            )

    def responder(self, request, queryset):
        """PENDING → RESPONDED: marca como respondida al cliente (no se confirma el turno)."""
        count = 0
        skipped = 0
        for pending in queryset:
            if pending.status == 'PENDING':
                pending.status = 'RESPONDED'
                pending.save()
                count += 1
            else:
                skipped += 1
        if count:
            palabra = 'solicitud marcada' if count == 1 else 'solicitudes marcadas'
            self.message_user(request, f'{count} {palabra} como Respondida.', messages.SUCCESS)
        if skipped:
            palabra = 'solicitud' if skipped == 1 else 'solicitudes'
            self.message_user(request, f'{skipped} {palabra} no estaba Pendiente.', messages.WARNING)

    confirmar.short_description = 'Confirmar turno'
    responder.short_description = 'Marcar como Respondida (sin confirmar turno)'
    deshacer.short_description = 'Deshacer confirmación'
