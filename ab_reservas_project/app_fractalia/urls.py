from django.urls import path
from . import views

urlpatterns = [
    path('calendario/', views.calendario, name='fractalia_calendario'),
    path('api/disponibilidad/', views.disponibilidad_api, name='fractalia_disponibilidad_api'),
]
