from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime, timedelta, time
import json
import re
from .models import Resource, WeeklyAvailability, Booking, PendingBooking, generate_reservation_code


def calendario(request):
    resources = Resource.objects.filter(active=True)
    context = {
        'resources': resources,
    }
    return render(request, 'app_fractalia/calendario.html', context)


def _get_slots_for_date(resource, fecha):
    """Helper function to get slots for a specific date"""
    weekday = fecha.weekday()
    availability = WeeklyAvailability.objects.filter(
        resource=resource,
        weekday=weekday
    ).first()

    if not availability:
        return None

    start_hour = availability.start_time.hour
    end_hour = availability.end_time.hour

    if availability.end_time.minute > 0:
        end_hour += 1

    slots = []
    current_hour = start_hour

    while current_hour < end_hour:
        slot_start_time = time(hour=current_hour, minute=0)
        slot_end_time = time(hour=current_hour + 1, minute=0) if current_hour + 1 <= 23 else time(23, 59)

        slot_start_datetime = datetime.combine(fecha, slot_start_time)
        slot_end_datetime = datetime.combine(fecha, slot_end_time)

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

    return slots


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

    slots = _get_slots_for_date(resource, fecha)

    if slots is None:
        return JsonResponse({
            'slots': [],
            'message': 'No hay horario disponible para este día'
        })

    return JsonResponse({
        'slots': slots,
        'fecha': fecha.strftime('%Y-%m-%d'),
        'resource_id': resource.id,
        'resource_name': resource.name,
        'has_availability': any(s['available'] for s in slots),
    })


@require_http_methods(['GET'])
def dias_disponibilidad_api(request):
    """Get availability status for multiple days (for day indicators)"""
    resource_id = request.GET.get('resource_id')
    from_date_str = request.GET.get('from_date')
    days = request.GET.get('days', '30')

    if not resource_id:
        return JsonResponse({'error': 'Parámetro resource_id requerido'}, status=400)

    try:
        resource = Resource.objects.get(id=resource_id, active=True)
        days = int(days)
    except Resource.DoesNotExist:
        return JsonResponse({'error': 'Recurso no encontrado'}, status=404)
    except ValueError:
        return JsonResponse({'error': 'Parámetro days debe ser un número'}, status=400)

    if from_date_str:
        try:
            today = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Formato from_date inválido (use YYYY-MM-DD)'}, status=400)
    else:
        today = datetime.now().date()

    days_info = []
    for i in range(days):
        fecha = today + timedelta(days=i)
        slots = _get_slots_for_date(resource, fecha)
        has_any_available = False

        if slots:
            has_any_available = any(s['available'] for s in slots)

        days_info.append({
            'fecha': fecha.strftime('%Y-%m-%d'),
            'weekday': fecha.weekday(),
            'has_availability': bool(slots) and has_any_available,
            'has_schedule': bool(slots),
        })

    return JsonResponse({'days': days_info})


@require_http_methods(['POST'])
@csrf_exempt
def create_pending_booking(request):
    """Create a pending booking and return a reservation code"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    resource_id = data.get('resource_id')
    fecha_str = data.get('fecha')
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')
    client_name = data.get('client_name', '').strip()
    client_phone = data.get('client_phone', '').strip()

    if not all([resource_id, fecha_str, start_time_str, end_time_str]):
        return JsonResponse(
            {'error': 'Parámetros requeridos: resource_id, fecha, start_time, end_time'},
            status=400
        )

    # Validar formato de teléfono si se proporciona
    if client_phone and not re.match(r'^09\d{8}$', client_phone):
        return JsonResponse(
            {'error': 'Formato de teléfono inválido. Debe ser 09XXXXXXXX'},
            status=400
        )

    try:
        resource = Resource.objects.get(id=resource_id, active=True)
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
    except Resource.DoesNotExist:
        return JsonResponse({'error': 'Recurso no encontrado'}, status=404)
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha/hora inválido'}, status=400)

    try:
        code = generate_reservation_code()
        pending = PendingBooking.objects.create(
            resource=resource,
            date=fecha,
            start_time=start_time,
            end_time=end_time,
            reservation_code=code,
            client_name=client_name,
            client_phone=client_phone,
            status='PENDING'
        )

        return JsonResponse({
            'code': pending.reservation_code,
            'id': pending.id,
        }, status=201)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
