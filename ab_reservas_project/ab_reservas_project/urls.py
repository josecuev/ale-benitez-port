# ab_reservas_project/urls.py
from django.contrib import admin
from django.urls import path, include
from oauth2_provider.views import OAuthServerMetadataView
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

# ✅ Branding del admin
admin.site.site_header = "Fractalia — Gestor de Reservas"
admin.site.site_title = "Admin Fractalia"
admin.site.index_title = "Administración del estudio"

urlpatterns = [
    # RFC 8414: cuando el issuer tiene path (acá /o), el metadata se publica en
    # la RAÍZ del host — /.well-known/oauth-authorization-server/o — y no bajo
    # el prefijo. El propio urls.py de DOT lo aclara ("Mount this at the server
    # root"), así que incluir el módulo entero bajo /o/ deja estas dos rutas en
    # el lugar equivocado y ningún cliente conforme al spec las encuentra.
    path(".well-known/oauth-authorization-server",
         OAuthServerMetadataView.as_view(), name="oauth-server-metadata-raiz"),
    path(".well-known/oauth-authorization-server/<path:issuer_path>",
         OAuthServerMetadataView.as_view(), name="oauth-server-metadata-issuer-raiz"),

    # OAuth 2.1 — authorization server del servicio MCP.
    # Expone /o/authorize/, /o/token/, /o/revoke_token/, /o/introspect/
    # y /o/register/ (registro dinámico de clientes)
    path("o/", include("oauth2_provider.urls", namespace="oauth2_provider")),

    path("", include("app_links.urls")),
    path("fractalia/", include("app_fractalia.urls")),
    path("", include("app_portfolio.urls")),
    path("", include("app_analytics.urls")),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    # ✅ solo media en dev
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
