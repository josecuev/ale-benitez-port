from django.contrib import admin
from .models import Link


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ('label', 'url', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    search_fields = ('label', 'url')
    ordering = ('order',)
