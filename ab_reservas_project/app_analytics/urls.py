from django.urls import path
from . import views

urlpatterns = [
    path('api/analytics/track/', views.track_pageview, name='analytics_track'),
]
