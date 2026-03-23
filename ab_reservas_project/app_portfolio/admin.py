from django.contrib import admin
from django.utils.html import format_html
from .models import Photo


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = ['thumbnail_preview', 'title', 'order', 'active', 'created_at']
    list_display_links = ['thumbnail_preview']
    list_editable = ['order', 'active']
    ordering = ['order']
    list_per_page = 50

    def thumbnail_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height:64px;width:64px;object-fit:cover;border-radius:4px;" />',
                obj.image.url,
            )
        return '—'
    thumbnail_preview.short_description = 'Vista previa'
