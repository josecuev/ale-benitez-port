from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta, time
from .models import Resource, WeeklyAvailability, Booking


def calendario(request):
    resources = Resource.objects.filter(active=True)
    context = {
        'resources': resources,
    }
    return render(request, 'app_fractalia/calendario.html', context)


@require_http_methods(['GET'])
def disponibilidad_api(request):
    fecha_str = request.GET.get('fecha')
    resource_id = request.GET.get('resource_id')

    if not fecha_str or not resource_id:
        return JsonResponse({'error': 'Parámetros fecha y resource_id requeridos'}, status=400)

    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha inválido (use YYYY-MM-DD)'}, status=400)

    try:
        resource = Resource.objects.get(id=resource_id, active=True)
    except Resource.DoesNotExist:
        return JsonResponse({'error': 'Recurso no encontrado'}, status=404)

    # Obtener disponibilidad semanal para ese día
    weekday = fecha.weekday()
    availability = WeeklyAvailability.objects.filter(
        resource=resource,
        weekday=weekday
    ).first()

    if not availability:
        return JsonResponse({
            'slots': [],
            'message': 'No hay horario disponible para este día'
        })

    # Generar slots de 1 hora dentro del rango disponible
    start_hour = availability.start_time.hour
    end_hour = availability.end_time.hour

    # Si end_time tiene minutos, incluir esa hora también
    if availability.end_time.minute > 0:
        end_hour += 1

    slots = []
    current_hour = start_hour

    while current_hour < end_hour:
        slot_start_time = time(hour=current_hour, minute=0)
        slot_end_time = time(hour=current_hour + 1, minute=0) if current_hour + 1 <= 23 else time(23, 59)

        # Crear datetime completo
        slot_start_datetime = datetime.combine(fecha, slot_start_time)
        slot_end_datetime = datetime.combine(fecha, slot_end_time)

        # Verificar si hay alguna reserva confirmada que se solape
        overlapping_booking = Booking.objects.filter(
            resource=resource,
            status='CONFIRMED',
            start_datetime__lt=slot_end_datetime,
            end_datetime__gt=slot_start_datetime
        ).exists()

        is_available = not overlapping_booking

        slots.append({
            'time': slot_start_time.strftime('%H:%M'),
            'available': is_available,
            'display': slot_start_time.strftime('%H:%M'),
        })

        current_hour += 1

    return JsonResponse({
        'slots': slots,
        'fecha': fecha.strftime('%Y-%m-%d'),
        'resource_id': resource.id,
        'resource_name': resource.name,
    })
