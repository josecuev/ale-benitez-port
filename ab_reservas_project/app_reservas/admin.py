from django.contrib import admin
from django import forms
from django.utils.html import format_html
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import ServicioAdicional, HorarioDisponible, Reserva


# ============================================================================
# ServicioAdicional Admin
# ============================================================================
@admin.register(ServicioAdicional)
class ServicioAdicionalAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'precio_formateado', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre', 'descripcion']
    list_editable = ['activo']
    
    def precio_formateado(self, obj):
        # Convertir a float y formatear
        precio = f"{float(obj.precio):,.0f}"
        return f"Gs. {precio}"
    precio_formateado.short_description = 'Precio'
    precio_formateado.admin_order_field = 'precio'


# ============================================================================
# HorarioDisponible Admin
# ============================================================================
@admin.register(HorarioDisponible)
class HorarioDisponibleAdmin(admin.ModelAdmin):
    list_display = [
        'tipo_icon', 
        'dia_semana_display', 
        'hora_inicio', 
        'hora_fin',
        'duracion_display', 
        'duracion_minima_display',
        'activo'
    ]
    list_filter = ['tipo', 'dia_semana', 'activo']
    list_editable = ['activo']
    ordering = ['dia_semana', 'hora_inicio']

    fieldsets = (
        ('Configuración Básica', {
            'fields': ('tipo', 'dia_semana', 'hora_inicio', 'hora_fin', 'activo')
        }),
        ('Configuración para Slots CONTINUOS', {
            'fields': ('duracion_minima_minutos',),
            'description': 'La duración mínima solo aplica a slots tipo CONTINUO (cliente elige horario dentro del rango).',
            'classes': ('collapse',)
        }),
    )

    def tipo_icon(self, obj):
        icono = '📦' if obj.tipo == 'DISCRETO' else '🔄'
        titulo = 'Discreto - Slot completo' if obj.tipo == 'DISCRETO' else 'Continuo - Horario flexible'
        return format_html('<span style="font-size:18px" title="{}">{}</span>', titulo, icono)
    tipo_icon.short_description = ''

    def dia_semana_display(self, obj):
        return obj.get_dia_semana_display()
    dia_semana_display.short_description = 'Día'
    dia_semana_display.admin_order_field = 'dia_semana'

    def duracion_display(self, obj):
        duracion = obj.duracion_minutos()
        horas = duracion // 60
        minutos = duracion % 60
        if horas and minutos:
            return f"{horas}h {minutos}min"
        if horas:
            return f"{horas}h"
        return f"{minutos}min"
    duracion_display.short_description = 'Duración Total'

    def duracion_minima_display(self, obj):
        if obj.tipo == 'CONTINUO':
            return f"Mín: {obj.duracion_minima_minutos} min"
        return "—"
    duracion_minima_display.short_description = 'Duración Mínima'


# ============================================================================
# Reserva Admin Form (filtra estados según configuración)
# ============================================================================
class ReservaAdminForm(forms.ModelForm):
    class Meta:
        model = Reserva
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar estados permitidos según configuración
        self.fields['estado'].choices = Reserva.estados_permitidos()


# ============================================================================
# Reserva Admin
# ============================================================================
@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    form = ReservaAdminForm

    list_display = [
        'codigo_corto', 
        'nombre_cliente', 
        'cedula',
        'telefono_cliente',
        'fecha', 
        'horario_display',
        'duracion_display',
        'estado_badge', 
        'total_display', 
        'creada_en'
    ]
    
    list_filter = [
        'estado', 
        'fecha', 
        'email_verificado_en',
        'confirmada_en',
        'creada_en'
    ]
    
    search_fields = [
        'nombre_cliente', 
        'email_cliente', 
        'telefono_cliente', 
        'codigo', 
        'cedula', 
        'ruc'
    ]

    date_hierarchy = 'fecha'
    
    # Para M2M con muchos registros, usar autocomplete
    autocomplete_fields = ['servicios_adicionales']

    # Readonly fields
    readonly_fields = [
        'codigo', 
        'token_verificacion', 
        'creada_en', 
        'actualizada_en',
        'email_verificado_en',
        'confirmada_en',
        'total_servicios_display',
        'link_verificacion'
    ]

    # Acciones personalizadas
    actions = ['confirmar_reservas_action', 'cancelar_reservas_action']

    def get_fieldsets(self, request, obj=None):
        """Fieldsets dinámicos según configuración"""
        requiere_verificacion = getattr(settings, "RESERVAS_REQUIRE_EMAIL_VERIFICATION", True)

        fieldsets = [
            ('Información del Cliente', {
                'fields': (
                    'nombre_cliente',
                    ('cedula', 'ruc'),
                    ('email_cliente', 'telefono_cliente')
                )
            }),
            ('Detalles de la Reserva', {
                'fields': (
                    'fecha',
                    ('hora_inicio', 'hora_fin'),
                    'servicios_adicionales',
                    'total_servicios_display',
                    'notas_cliente'
                )
            }),
            ('Gestión del Asistente', {
                'fields': ('estado', 'notas_internas'),
                'classes': ('wide',)
            }),
        ]

        # Sistema info
        sistema_fields = ['codigo', 'token_verificacion', 'creada_en', 'actualizada_en']
        if requiere_verificacion:
            sistema_fields.extend(['email_verificado_en', 'link_verificacion', 'confirmada_en'])
        else:
            sistema_fields.append('confirmada_en')

        fieldsets.append(
            ('Información del Sistema', {
                'fields': tuple(sistema_fields),
                'classes': ('collapse',)
            })
        )

        return fieldsets

    # ========================================================================
    # Display methods
    # ========================================================================
    
    def codigo_corto(self, obj):
        return format_html('<code style="background:#f0f0f0;padding:2px 6px;border-radius:3px">{}</code>', 
                          str(obj.codigo)[:8])
    codigo_corto.short_description = 'Código'

    def horario_display(self, obj):
        return f"{obj.hora_inicio.strftime('%H:%M')} — {obj.hora_fin.strftime('%H:%M')}"
    horario_display.short_description = 'Horario'

    def duracion_display(self, obj):
        from datetime import datetime
        inicio = datetime.combine(obj.fecha, obj.hora_inicio)
        fin = datetime.combine(obj.fecha, obj.hora_fin)
        duracion_min = int((fin - inicio).total_seconds() / 60)
        
        horas = duracion_min // 60
        minutos = duracion_min % 60
        
        if horas > 0 and minutos > 0:
            return f"{horas}h {minutos}min"
        elif horas > 0:
            return f"{horas}h"
        else:
            return f"{minutos}min"
    duracion_display.short_description = 'Duración'

    def total_display(self, obj):
        total = obj.total()
        if total > 0:
            # Convertir a float y formatear antes de pasar a format_html
            total_formateado = f"{float(total):,.0f}"
            return format_html('<strong style="color:#16a34a">Gs. {}</strong>', total_formateado)
        return format_html('<span style="color:#999">—</span>')
    total_display.short_description = 'Total Servicios'

    def total_servicios_display(self, obj):
        """Para usar en el formulario"""
        total = obj.total()
        if total > 0:
            # Convertir a float y formatear antes de pasar a format_html
            total_formateado = f"{float(total):,.0f}"
            return format_html('<strong style="color:#16a34a;font-size:16px">Gs. {}</strong>', total_formateado)
        return 'Sin servicios adicionales'
    total_servicios_display.short_description = 'Total Servicios Adicionales'

    def estado_badge(self, obj):
        """Badge con color e icono según estado"""
        config = {
            'PENDIENTE_VERIFICACION': {
                'color': '#f59e0b',
                'bg': '#fef3c7',
                'icono': '📧'
            },
            'PENDIENTE_CONFIRMACION': {
                'color': '#3b82f6',
                'bg': '#dbeafe',
                'icono': '⏳'
            },
            'CONFIRMADA': {
                'color': '#16a34a',
                'bg': '#dcfce7',
                'icono': '✓'
            },
            'CANCELADA': {
                'color': '#ef4444',
                'bg': '#fee2e2',
                'icono': '✗'
            },
        }
        
        info = config.get(obj.estado, {
            'color': '#6b7280',
            'bg': '#f3f4f6',
            'icono': '●'
        })
        
        return format_html(
            '<span style="background:{}; color:{}; padding:4px 10px; border-radius:6px; '
            'font-size:12px; font-weight:600; display:inline-block">'
            '{} {}</span>',
            info['bg'],
            info['color'],
            info['icono'],
            obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'
    estado_badge.admin_order_field = 'estado'

    def link_verificacion(self, obj):
        """Link de verificación para copiar"""
        if not obj.pk:
            return "—"
        
        url = reverse('verificar_reserva', kwargs={'token': obj.token_verificacion})
        
        return format_html(
            '<div style="margin:10px 0">'
            '<a href="{}" target="_blank" style="color:#3b82f6;text-decoration:none">'
            '🔗 Abrir link de verificación →</a>'
            '</div>'
            '<div style="background:#f9fafb;padding:8px;border-radius:4px;font-family:monospace;font-size:11px">'
            '{}</div>',
            url,
            url
        )
    link_verificacion.short_description = 'Link de Verificación'

    # ========================================================================
    # Acciones personalizadas
    # ========================================================================

    def confirmar_reservas_action(self, request, queryset):
        """Confirma las reservas pendientes seleccionadas"""
        # Filtrar solo las pendientes de confirmación
        pendientes = queryset.filter(estado='PENDIENTE_CONFIRMACION')
        
        if not pendientes.exists():
            self.message_user(
                request,
                '⚠️ No hay reservas en estado "Pendiente de Confirmación" entre las seleccionadas.',
                level=messages.WARNING
            )
            return
        
        confirmadas = 0
        errores = []
        
        for reserva in pendientes:
            try:
                exito, mensaje = reserva.confirmar_reserva()
                if exito:
                    confirmadas += 1
                else:
                    errores.append(f"{reserva.nombre_cliente} ({str(reserva.codigo)[:8]}): {mensaje}")
            except Exception as e:
                errores.append(f"{reserva.nombre_cliente} ({str(reserva.codigo)[:8]}): {str(e)}")
        
        # Mensajes de resultado
        if confirmadas:
            self.message_user(
                request,
                f'✓ Se confirmaron {confirmadas} reserva(s) exitosamente. '
                f'Se enviaron emails de confirmación a los clientes.',
                level=messages.SUCCESS
            )
        
        if errores:
            for error in errores[:5]:  # Mostrar máximo 5 errores
                self.message_user(request, f'✗ Error: {error}', level=messages.ERROR)
            
            if len(errores) > 5:
                self.message_user(
                    request,
                    f'... y {len(errores) - 5} error(es) más. Revisa los detalles en cada reserva.',
                    level=messages.WARNING
                )
    
    confirmar_reservas_action.short_description = "✓ Confirmar reservas seleccionadas"

    def cancelar_reservas_action(self, request, queryset):
        """Cancela las reservas confirmadas seleccionadas"""
        # Filtrar solo las confirmadas
        confirmadas = queryset.filter(estado='CONFIRMADA')
        
        if not confirmadas.exists():
            self.message_user(
                request,
                '⚠️ No hay reservas confirmadas entre las seleccionadas.',
                level=messages.WARNING
            )
            return
        
        canceladas = 0
        errores = []
        
        for reserva in confirmadas:
            try:
                if reserva.cancelar_confirmacion():
                    canceladas += 1
                else:
                    errores.append(f"{reserva.nombre_cliente} ({str(reserva.codigo)[:8]}): No se pudo cancelar")
            except Exception as e:
                errores.append(f"{reserva.nombre_cliente} ({str(reserva.codigo)[:8]}): {str(e)}")
        
        # Mensajes de resultado
        if canceladas:
            self.message_user(
                request,
                f'✓ Se cancelaron {canceladas} reserva(s). Los horarios vuelven a estar disponibles.',
                level=messages.SUCCESS
            )
        
        if errores:
            for error in errores[:5]:
                self.message_user(request, f'✗ Error: {error}', level=messages.ERROR)
            
            if len(errores) > 5:
                self.message_user(
                    request,
                    f'... y {len(errores) - 5} error(es) más.',
                    level=messages.WARNING
                )
    
    cancelar_reservas_action.short_description = "✗ Cancelar reservas confirmadas"

    def save_model(self, request, obj, form, change):
        """Validación extra antes de guardar"""
        try:
            obj.full_clean()
            super().save_model(request, obj, form, change)
            
            # Mensaje de éxito con información útil
            if change:
                self.message_user(
                    request,
                    f'✓ Reserva actualizada: {obj.nombre_cliente} - {obj.fecha} - {obj.get_estado_display()}',
                    level=messages.SUCCESS
                )
        except Exception as e:
            self.message_user(
                request,
                f'✗ Error al guardar la reserva: {str(e)}',
                level=messages.ERROR
            )
            raise


# ============================================================================
# Personalización del sitio admin
# ============================================================================
admin.site.site_header = "Estudio Fotográfico - Panel de Administración"
admin.site.site_title = "Admin Reservas"
admin.site.index_title = "Gestión de Reservas y Horarios"