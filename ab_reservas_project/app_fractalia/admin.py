from django.contrib import admin
from .models import Resource, WeeklyAvailability, Booking


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
