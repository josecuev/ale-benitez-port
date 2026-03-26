from django.contrib import admin, messages
from django.utils import timezone
from django.utils.safestring import mark_safe
from datetime import datetime, date as date_cls
import re
import zoneinfo
from .models import (
    Resource, WeeklyAvailability, Booking, PendingBooking, Product, FractaboxPackage,
    get_fractabox_package_for_hours,
)

_ASUNCION = zoneinfo.ZoneInfo('America/Asuncion')


def _now_asuncion():
    """Retorna el datetime actual en zona horaria America/Asuncion."""
    return timezone.now().astimezone(_ASUNCION)


def _asuncion(naive_dt):
    """Convierte un datetime naive a America/Asuncion aware."""
    return naive_dt.replace(tzinfo=_ASUNCION)


class EstadoGestionFilter(admin.SimpleListFilter):
    """Filtro que replica los 3 paneles del dashboard de analytics."""
    title = 'Estado de gestión'
    parameter_name = 'gestion'

    def lookups(self, request, model_admin):
        return [
            ('vencidas',    '⚠️  Vencidas sin respuesta'),
            ('activas',     '🕐  Activas sin confirmar'),
            ('conflicto',           '🔴  Conflicto con reserva confirmada'),
            ('conflicto_prereservas', '⚡  Compite con otra pre-reserva'),
            ('confirmadas', '✅  Confirmadas'),
            ('respondidas', '💬  Respondidas'),
            ('canceladas',  '❌  Canceladas'),
        ]

    def queryset(self, request, queryset):
        from django.db.models import Q
        now_local = _now_asuncion()
        today = now_local.date()
        current_time = now_local.time()
        if self.value() == 'vencidas':
            return queryset.filter(status='PENDING').filter(
                Q(date__lt=today) | Q(date=today, start_time__lt=current_time)
            )
        if self.value() == 'activas':
            return queryset.filter(status='PENDING').filter(
                Q(date__gt=today) | Q(date=today, start_time__gte=current_time)
            )
        if self.value() == 'conflicto':
            # PRE-reservas PENDING activas que solapan con un Booking confirmado
            pending_activas = queryset.filter(status='PENDING').filter(
                Q(date__gt=today) | Q(date=today, start_time__gte=current_time)
            )
            confirmed_bookings = list(
                Booking.objects.filter(status='CONFIRMED')
                .values('start_datetime', 'end_datetime')
            )
            conflicting_ids = []
            for pb in pending_activas:
                pb_start = _asuncion(datetime.combine(pb.date, pb.start_time))
                pb_end   = _asuncion(datetime.combine(pb.date, pb.end_time))
                if any(
                    b['start_datetime'] < pb_end and b['end_datetime'] > pb_start
                    for b in confirmed_bookings
                ):
                    conflicting_ids.append(pb.pk)
            return queryset.filter(pk__in=conflicting_ids)
        if self.value() == 'conflicto_prereservas':
            pending_activas = queryset.filter(status='PENDING').filter(
                Q(date__gt=today) | Q(date=today, start_time__gte=current_time)
            )
            all_pending = list(pending_activas)
            conflicting_ids = set()
            for i, pb1 in enumerate(all_pending):
                pb1_start = _asuncion(datetime.combine(pb1.date, pb1.start_time))
                pb1_end   = _asuncion(datetime.combine(pb1.date, pb1.end_time))
                for pb2 in all_pending[i + 1:]:
                    if pb1.resource_id != pb2.resource_id:
                        continue
                    pb2_start = _asuncion(datetime.combine(pb2.date, pb2.start_time))
                    pb2_end   = _asuncion(datetime.combine(pb2.date, pb2.end_time))
                    if pb1_start < pb2_end and pb1_end > pb2_start:
                        conflicting_ids.add(pb1.pk)
                        conflicting_ids.add(pb2.pk)
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


class FractaboxPackageInline(admin.TabularInline):
    model = FractaboxPackage
    extra = 1
    fields = ('label', 'slots_to_block', 'order', 'is_active')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_type', 'resource', 'is_public', 'is_active')
    list_editable = ('is_public', 'is_active')
    list_filter = ('product_type', 'is_active', 'is_public')
    inlines = [FractaboxPackageInline]


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
    list_display = ('resource', 'formatted_date', 'client_name', 'end_datetime', 'client_phone', 'product', 'status_display', 'whatsapp_contact')
    list_filter = ('resource', 'status', 'start_datetime')
    search_fields = ('resource__name', 'notes', 'client_phone', 'client_name', 'product__name')
    readonly_fields = ('created_at', 'whatsapp_link_display')
    date_hierarchy = 'start_datetime'
    ordering = ('start_datetime',)
    actions = ['cancelar', 'reactivar']
    fieldsets = (
        ('Información de la reserva', {
            'fields': ('resource', 'product', 'status', 'client_name', 'client_phone')
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
        duration_hours = int((obj.end_datetime - obj.start_datetime).total_seconds() / 3600)

        days = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        months = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

        day_name = days[date.weekday()]
        month_name = months[date.month - 1]
        date_str = f'{day_name.capitalize()}, {date.day} de {month_name} de {date.year}'

        resource_name = obj.resource.name
        code = ''
        product_name = resource_name
        if obj.product and obj.product.product_type == 'FRACTABOX':
            package = get_fractabox_package_for_hours(obj.product, duration_hours)
            if package:
                product_name = f'Fractabox ({package.label})'

        # Extract code from notes if available
        if obj.notes:
            match = re.search(r'Código de reserva: (\w+)', obj.notes)
            if match:
                code = f' (Código: {match.group(1)})'

        if obj.product and obj.product.product_type == 'FRACTABOX':
            message = f'Hola, te escribo en relacion a tu reserva de {product_name} el {date_str} a las {start_time}{code}.'
        else:
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
        'estado_gestion', 'formatted_date', 'horario',
        'client_name', 'product', 'resource', 'recibida_hace', 'whatsapp_link_list',
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
            'fields': ('reservation_code', 'resource', 'product', 'date', 'start_time', 'end_time', 'status')
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
        now_local = _now_asuncion()
        today = now_local.date()
        current_time = now_local.time()
        if obj.status == 'PENDING':
            expired = obj.date < today or (obj.date == today and obj.start_time < current_time)
            if expired:
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

    def horario(self, obj):
        return mark_safe(
            f'<span style="font-weight:700; font-size:13px; font-variant-numeric:tabular-nums;">'
            f'{obj.start_time.strftime("%H:%M")} – {obj.end_time.strftime("%H:%M")}</span>'
        )
    horario.short_description = 'Horario'
    horario.admin_order_field = 'start_time'

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
        now_local2 = _now_asuncion()
        today2 = now_local2.date()
        current_time2 = now_local2.time()
        expired = obj.date < today2 or (obj.date == today2 and obj.start_time < current_time2)
        if obj.status == 'PENDING' and expired:
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
        duration_hours = int(
            (datetime.combine(date, obj.end_time) - datetime.combine(date, obj.start_time)).total_seconds() / 3600
        )

        days = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        months = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                  'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']

        day_name = days[date.weekday()]
        month_name = months[date.month - 1]
        date_str = f'{day_name.capitalize()}, {date.day} de {month_name} de {date.year}'

        resource_name = obj.resource.name
        code = obj.reservation_code
        product_name = resource_name
        if obj.product and obj.product.product_type == 'FRACTABOX':
            package = get_fractabox_package_for_hours(obj.product, duration_hours)
            if package:
                product_name = f'Fractabox ({package.label})'

        if obj.product and obj.product.product_type == 'FRACTABOX':
            message = (
                f'Hola, te escribo en relacion a tu pre-reserva de {product_name} '
                f'el {date_str} a las {start_time} (Código: {code}).'
            )
        else:
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
                    start_dt = _asuncion(datetime.combine(pending.date, pending.start_time))
                    end_dt   = _asuncion(datetime.combine(pending.date, pending.end_time))
                    duration_hours = int((end_dt - start_dt).total_seconds() / 3600)
                    fractabox_package = None
                    if pending.product and pending.product.product_type == 'FRACTABOX':
                        fractabox_package = get_fractabox_package_for_hours(pending.product, duration_hours)
                        if not fractabox_package:
                            raise ValueError('Duración inválida para Fractabox')

                    Booking.objects.create(
                        resource=pending.resource,
                        product=pending.product,
                        fractabox_package=fractabox_package,
                        client_name=pending.client_name,
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
