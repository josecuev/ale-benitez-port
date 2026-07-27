from django.contrib import admin
from django.db.models import Count
from django.utils.safestring import mark_safe

from .models import Necesidad, UsoTool


@admin.register(Necesidad)
class NecesidadAdmin(admin.ModelAdmin):
    """La lista para decidir qué construir después, ordenada por cuánto duele."""

    list_display = ('resumen', 'veces', 'categoria', 'estado_color',
                    'tool_relacionada', 'ultima_vez')
    list_filter = ('estado', 'categoria')
    search_fields = ('descripcion', 'contexto', 'tool_relacionada')
    readonly_fields = ('clave', 'veces', 'usuario', 'primera_vez', 'ultima_vez')
    list_editable = ()
    actions = ('marcar_planificada', 'marcar_implementada', 'marcar_descartada')

    fieldsets = (
        ('Qué pasó', {'fields': ('descripcion', 'categoria', 'contexto',
                                 'tool_relacionada')}),
        ('Seguimiento', {'fields': ('estado', 'nota_equipo')}),
        ('Datos', {'fields': ('veces', 'usuario', 'primera_vez', 'ultima_vez',
                              'clave'),
                   'classes': ('collapse',)}),
    )

    @admin.display(description='Necesidad')
    def resumen(self, obj):
        return obj.descripcion[:80] + ('…' if len(obj.descripcion) > 80 else '')

    @admin.display(description='Estado', ordering='estado')
    def estado_color(self, obj):
        colores = {'nueva': '#b91c1c', 'en_analisis': '#c2410c',
                   'planificada': '#0369a1', 'implementada': '#15803d',
                   'descartada': '#6b7280'}
        return mark_safe(
            f'<b style="color:{colores.get(obj.estado, "#000")}">'
            f'{obj.get_estado_display()}</b>')

    def _cambiar(self, request, queryset, estado, etiqueta):
        n = queryset.update(estado=estado)
        self.message_user(request, f'{n} necesidad(es) marcada(s) como {etiqueta}.')

    @admin.action(description='Marcar como planificada')
    def marcar_planificada(self, request, queryset):
        self._cambiar(request, queryset, 'planificada', 'planificadas')

    @admin.action(description='Marcar como implementada')
    def marcar_implementada(self, request, queryset):
        self._cambiar(request, queryset, 'implementada', 'implementadas')

    @admin.action(description='Descartar')
    def marcar_descartada(self, request, queryset):
        self._cambiar(request, queryset, 'descartada', 'descartadas')


@admin.register(UsoTool)
class UsoToolAdmin(admin.ModelAdmin):
    list_display = ('tool', 'usuario', 'exito', 'duracion_ms', 'momento')
    list_filter = ('tool', 'exito')
    search_fields = ('tool', 'usuario', 'detalle_error')
    readonly_fields = [f.name for f in UsoTool._meta.fields]
    date_hierarchy = 'momento'

    def has_add_permission(self, request):
        return False  # se llena solo

    def changelist_view(self, request, extra_context=None):
        """Resumen arriba de la lista: qué se usa y qué falla."""
        resumen = (UsoTool.objects.values('tool')
                   .annotate(total=Count('id'))
                   .order_by('-total')[:10])
        fallas = (UsoTool.objects.filter(exito=False).values('tool')
                  .annotate(total=Count('id')).order_by('-total')[:5])
        extra_context = extra_context or {}
        extra_context['title'] = (
            'Uso de herramientas — más usadas: '
            + ', '.join(f"{r['tool']} ({r['total']})" for r in resumen)
            + ('  |  con fallas: '
               + ', '.join(f"{r['tool']} ({r['total']})" for r in fallas)
               if fallas else '')
        )
        return super().changelist_view(request, extra_context)
