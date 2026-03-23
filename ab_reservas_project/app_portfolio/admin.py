from django.contrib import admin
from django.utils.html import format_html
from .models import Photo


@admin.action(description='Regenerar thumbnails de las fotos seleccionadas')
def regenerar_thumbnails(modeladmin, request, queryset):
    count = 0
    errors = 0
    for photo in queryset:
        if photo.image:
            Photo.objects.filter(pk=photo.pk).update(thumbnail='')
            photo.thumbnail = ''
            photo._generate_thumbnail()
            if photo.thumbnail:
                count += 1
            else:
                errors += 1
    if count:
        modeladmin.message_user(request, f'{count} thumbnail(s) regenerado(s) correctamente.')
    if errors:
        modeladmin.message_user(request, f'{errors} foto(s) fallaron al generar thumbnail.', level='warning')


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ['thumbnail_preview', 'title', 'order', 'active', 'created_at']
    list_display_links = ['thumbnail_preview']
    list_editable = ['order', 'active']
    ordering = ['order']
    list_per_page = 50
    actions = [regenerar_thumbnails]

    def thumbnail_preview(self, obj):
        src = obj.thumbnail.url if obj.thumbnail else (obj.image.url if obj.image else None)
        if src:
            return format_html(
                '<img src="{}" style="height:64px;width:64px;object-fit:cover;border-radius:4px;" />',
                src,
            )
        return '—'
    thumbnail_preview.short_description = 'Vista previa'
