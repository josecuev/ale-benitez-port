from django.urls import path
from . import views

urlpatterns = [
    path('api/portfolio/fotos/', views.fotos_api, name='portfolio_fotos'),
]
