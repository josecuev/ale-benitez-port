from django.contrib import admin, messages
from django.utils import timezone
from django.utils.safestring import mark_safe
from datetime import datetime
import re
from .models import Resource, WeeklyAvailability, Booking, PendingBooking


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


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('resource', 'start_datetime', 'end_datetime', 'status_display')
    list_filter = ('resource', 'status', 'start_datetime')
    search_fields = ('resource__name', 'notes')
    readonly_fields = ('created_at',)
    actions = ['cancelar', 'reactivar']
    fieldsets = (
        ('Información de la reserva', {
            'fields': ('resource', 'status')
        }),
        ('Horario', {
            'fields': ('start_datetime', 'end_datetime')
        }),
        ('Notas', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def status_display(self, obj):
        colors = {
            'CONFIRMED': 'green',
            'CANCELLED': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{obj.get_status_display()}</span>')
    status_display.short_description = 'Estado'

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
            self.message_user(
                request,
                f'{cancelled_count} reserva(s) cancelada(s).',
                messages.SUCCESS
            )
        if incompatible_count > 0:
            self.message_user(
                request,
                f'{incompatible_count} reserva(s) no se pueden cancelar.',
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
            self.message_user(
                request,
                f'{reactivated_count} reserva(s) reactivada(s).',
                messages.SUCCESS
            )
        if incompatible_count > 0:
            self.message_user(
                request,
                f'{incompatible_count} reserva(s) no se pueden reactivar.',
                messages.WARNING
            )

    cancelar.short_description = '❌ Cancelar'
    reactivar.short_description = '✅ Reactivar'


@admin.register(PendingBooking)
class PendingBookingAdmin(admin.ModelAdmin):
    list_display = (
        'reservation_code', 'client_name', 'resource', 'date', 'start_time',
        'end_time', 'status_badge', 'created_at'
    )
    list_filter = ('resource', 'status', 'date')
    search_fields = ('reservation_code',)
    readonly_fields = ('reservation_code', 'created_at')
    ordering = ('-created_at',)
    actions = ['confirmar', 'deshacer']

    def status_badge(self, obj):
        colors = {
            'PENDING': 'orange',
            'CONFIRMED': 'green',
            'REJECTED': 'red',
            'CANCELLED': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{obj.get_status_display()}</span>')
    status_badge.short_description = 'Estado'

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
                        notes=f'Código de reserva: {pending.reservation_code}'
                    )
                    pending.status = 'CONFIRMED'
                    pending.save()
                    confirmed_count += 1
                except Exception as e:
                    self.message_user(
                        request,
                        f'Error al confirmar {pending.reservation_code}: {str(e)}',
                        messages.ERROR
                    )
            else:
                incompatible_count += 1

        if confirmed_count > 0:
            self.message_user(
                request,
                f'{confirmed_count} reserva(s) confirmada(s).',
                messages.SUCCESS
            )
        if incompatible_count > 0:
            self.message_user(
                request,
                f'{incompatible_count} reserva(s) no se pueden confirmar.',
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
                    self.message_user(
                        request,
                        f'Error al deshacer {pending.reservation_code}: {str(e)}',
                        messages.ERROR
                    )
            else:
                incompatible_count += 1

        if undone_count > 0:
            self.message_user(
                request,
                f'{undone_count} reserva(s) vuelta(s) a pendiente.',
                messages.SUCCESS
            )
        if incompatible_count > 0:
            self.message_user(
                request,
                f'{incompatible_count} reserva(s) no se pueden deshacer.',
                messages.WARNING
            )

    confirmar.short_description = '✅ Confirmar'
    deshacer.short_description = '⏪ Deshacer confirmación'
