from django.urls import path
from . import views

# urlpatterns = [
#     # Single page de nueva reserva
#     path("nueva/", views.nueva_reserva, name="nueva_reserva"),

#     # Verificación de email (ya creada antes)
#     path("verificar/<uuid:token>/", views.verificar_reserva, name="verificar_reserva"),

#     # API mínima para autocomplete de servicios
#     path("api/servicios", views.servicios_api, name="servicios_api"),
# ]



urlpatterns = [
    path("nueva/", views.nueva_reserva, name="nueva_reserva"),
    path("api/servicios/", views.servicios_api, name="servicios_api"),
    path("api/disponibilidad/", views.disponibilidad_api, name="disponibilidad_api"),  # 👈 NUEVO
    path("verificar/<uuid:token>/", views.verificar_reserva, name="verificar_reserva"),
]
