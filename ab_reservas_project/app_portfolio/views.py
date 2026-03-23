from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Photo


@require_http_methods(['GET'])
def fotos_api(request):
    photos = Photo.objects.filter(active=True).order_by('order')
    data = [
        {
            'id': p.id,
            'title': p.title,
            'url': request.build_absolute_uri(p.image.url),
            'order': p.order,
        }
        for p in photos
    ]
    response = JsonResponse({'fotos': data})
    response['Access-Control-Allow-Origin'] = '*'
    return response
