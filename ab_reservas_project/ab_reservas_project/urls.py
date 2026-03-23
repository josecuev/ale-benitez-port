# ab_reservas_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

# ✅ Branding del admin
admin.site.site_header = "Fractalia — Gestor de Reservas"
admin.site.site_title = "Admin Fractalia"
admin.site.index_title = "Administración del estudio"

urlpatterns = [
    path("", include("app_links.urls")),
    path("fractalia/", include("app_fractalia.urls")),
    path("", include("app_portfolio.urls")),
    path("", include("app_analytics.urls")),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    # ✅ solo media en dev
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
