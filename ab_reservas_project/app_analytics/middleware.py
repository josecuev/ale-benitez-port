from .models import PageView, VALID_PAGE_KEYS

# Mapeo de paths Django → identificador de página
PAGE_MAP = {
    '/': 'links',
    '/fractalia/calendario/': 'fractalia_calendar',
}

# Paths que nunca se trackean
SKIP_PREFIXES = ('/admin/', '/static/', '/media/', '/api/')


class PageViewMiddleware:
    """
    Registra automáticamente visitas a páginas Django renderizadas por el servidor.
    Las páginas React se trackean mediante el endpoint /api/analytics/track/.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Solo GET exitosos
        if request.method != 'GET' or response.status_code >= 400:
            return response

        path = request.path_info
        if any(path.startswith(p) for p in SKIP_PREFIXES):
            return response

        page = PAGE_MAP.get(path)
        if not page:
            return response

        try:
            ip = self._get_ip(request)
            referrer_url = request.META.get('HTTP_REFERER', '')
            PageView.objects.create(
                page=page,
                ip_hash=PageView.hash_ip(ip),
                referrer=PageView.extract_referrer_domain(referrer_url),
            )
        except Exception:
            pass  # analytics nunca rompe la request

        return response

    @staticmethod
    def _get_ip(request) -> str:
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')
