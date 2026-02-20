from django.contrib import admin, messages
from django.utils import timezone
from datetime import datetime
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
        return f'<span style="color: {color}; font-weight: bold;">{obj.get_status_display()}</span>'
    status_display.short_description = 'Estado'
    status_display.allow_tags = True


@admin.register(PendingBooking)
class PendingBookingAdmin(admin.ModelAdmin):
    list_display = ('reservation_code', 'resource', 'date', 'start_time', 'end_time', 'status_badge', 'created_at')
    list_filter = ('resource', 'status', 'date')
    search_fields = ('reservation_code',)
    readonly_fields = ('reservation_code', 'created_at')
    ordering = ('-created_at',)
    actions = ['confirmar_reserva']

    def status_badge(self, obj):
        colors = {
            'PENDING': 'orange',
            'CONFIRMED': 'green',
            'REJECTED': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return f'<span style="color: {color}; font-weight: bold;">{obj.get_status_display()}</span>'
    status_badge.short_description = 'Estado'
    status_badge.allow_tags = True

    def confirmar_reserva(self, request, queryset):
        confirmed_count = 0
        for pending in queryset.filter(status='PENDING'):
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

        self.message_user(
            request,
            f'{confirmed_count} reserva(s) confirmada(s) exitosamente.',
            messages.SUCCESS
        )

    confirmar_reserva.short_description = 'Confirmar reserva seleccionada'
