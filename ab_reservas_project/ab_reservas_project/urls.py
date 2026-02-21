# ab_reservas_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("", include("app_links.urls")),
    path("fractalia/", include("app_fractalia.urls")),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    # ✅ solo media en dev
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
