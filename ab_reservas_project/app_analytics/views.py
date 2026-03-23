import hashlib
import json

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import PageView, VALID_PAGE_KEYS

# Dominios permitidos para el endpoint de tracking del frontend React.
# Cualquier request desde otro origen será rechazada.
ALLOWED_ORIGINS = {
    'alejandrobenitez.com',
    'www.alejandrobenitez.com',
    'links.alejandrobenitez.com',
    'localhost',
    '127.0.0.1',
}

# Rate limit: máximo 10 requests por IP por minuto.
# Nota: con múltiples workers en producción, el límite se aplica por proceso
# (Django usa LocMemCache por defecto). Si se configura Redis como cache backend,
# el rate limit será global entre todos los procesos.
RATE_LIMIT = 10
RATE_WINDOW_SECONDS = 60


def _get_ip(request) -> str:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def _is_rate_limited(ip: str) -> bool:
    key = f'analytics_rl_{hashlib.md5(ip.encode()).hexdigest()}'
    count = cache.get(key, 0)
    if count >= RATE_LIMIT:
        return True
    cache.set(key, count + 1, RATE_WINDOW_SECONDS)
    return False


def _origin_allowed(request) -> bool:
    for header in ('HTTP_ORIGIN', 'HTTP_REFERER'):
        value = request.META.get(header, '')
        if any(domain in value for domain in ALLOWED_ORIGINS):
            return True
    return False


@csrf_exempt
@require_POST
def track_pageview(request):
    """
    POST /api/analytics/track/
    Body JSON: { "page": "portfolio", "referrer": "https://instagram.com/..." }

    Registra una visita desde el frontend React.
    Rate limit: 10 req/min por IP.
    Origin check: solo dominios conocidos.
    """
    ip = _get_ip(request)

    if _is_rate_limited(ip):
        return JsonResponse({'ok': False, 'error': 'rate_limited'}, status=429)

    if not _origin_allowed(request):
        return JsonResponse({'ok': False, 'error': 'forbidden'}, status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'invalid_json'}, status=400)

    page = str(data.get('page', '')).strip()
    if page not in VALID_PAGE_KEYS:
        return JsonResponse({'ok': False, 'error': 'invalid_page'}, status=400)

    referrer_url = str(data.get('referrer', ''))[:200]
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    PageView.objects.create(
        page=page,
        ip_hash=PageView.hash_ip(ip),
        referrer=PageView.extract_referrer_domain(referrer_url),
        user_agent_hash=hashlib.sha256(user_agent.encode()).hexdigest() if user_agent else '',
    )

    return JsonResponse({'ok': True})
