from django.shortcuts import render
from .models import Link


def links_page(request):
    links = Link.objects.filter(is_active=True)
    return render(request, 'app_links/links.html', {'links': links})
