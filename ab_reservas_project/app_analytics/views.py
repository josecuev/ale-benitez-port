import hashlib
import json

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

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


def _get_allowed_origin(request) -> str | None:
    """Retorna el origin si está en la lista de permitidos, None si no."""
    origin = request.META.get('HTTP_ORIGIN', '')
    if origin and any(domain in origin for domain in ALLOWED_ORIGINS):
        return origin
    referrer = request.META.get('HTTP_REFERER', '')
    if referrer and any(domain in referrer for domain in ALLOWED_ORIGINS):
        return referrer.split('/')[0] + '//' + referrer.split('/')[2]
    return None


def _add_cors(response, origin: str) -> None:
    response['Access-Control-Allow-Origin'] = origin
    response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type'


@csrf_exempt
def track_pageview(request):
    """
    POST /api/analytics/track/
    Body JSON: { "page": "portfolio", "referrer": "https://instagram.com/..." }

    Registra una visita desde el frontend React.
    Rate limit: 10 req/min por IP.
    Origin check: solo dominios conocidos.
    """
    allowed_origin = _get_allowed_origin(request)

    # Preflight CORS
    if request.method == 'OPTIONS':
        if not allowed_origin:
            return JsonResponse({'ok': False}, status=403)
        resp = JsonResponse({})
        _add_cors(resp, allowed_origin)
        return resp

    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)

    if not allowed_origin:
        return JsonResponse({'ok': False, 'error': 'forbidden'}, status=403)

    ip = _get_ip(request)
    if _is_rate_limited(ip):
        resp = JsonResponse({'ok': False, 'error': 'rate_limited'}, status=429)
        _add_cors(resp, allowed_origin)
        return resp

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        resp = JsonResponse({'ok': False, 'error': 'invalid_json'}, status=400)
        _add_cors(resp, allowed_origin)
        return resp

    page = str(data.get('page', '')).strip()
    if page not in VALID_PAGE_KEYS:
        resp = JsonResponse({'ok': False, 'error': 'invalid_page'}, status=400)
        _add_cors(resp, allowed_origin)
        return resp

    referrer_url = str(data.get('referrer', ''))[:200]
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    PageView.objects.create(
        page=page,
        ip_hash=PageView.hash_ip(ip),
        referrer=PageView.extract_referrer_domain(referrer_url),
        user_agent_hash=hashlib.sha256(user_agent.encode()).hexdigest() if user_agent else '',
    )

    resp = JsonResponse({'ok': True})
    _add_cors(resp, allowed_origin)
    return resp
