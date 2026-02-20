from django.urls import path
from . import views

urlpatterns = [
    path('', views.links_page, name='links'),
]
