from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Prefetch
from datetime import datetime, timedelta, time
import json
import re
from .models import (
    Resource, WeeklyAvailability, Booking, PendingBooking, Product, FractaboxPackage,
    generate_reservation_code, get_fractabox_package_for_hours,
)


def calendario(request):
    if request.user.is_staff:
        products_qs = Product.objects.filter(is_active=True)
    else:
        products_qs = Product.objects.filter(is_active=True, is_public=True)

    products_qs = products_qs.prefetch_related(
        Prefetch('packages', queryset=FractaboxPackage.objects.filter(is_active=True).order_by('order'))
    ).select_related('resource')

    products_list = list(products_qs)
    products_json = json.dumps([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'product_type': p.product_type,
        'resource_id': p.resource_id,
        'whatsapp_number': p.resource.whatsapp_number,
        'packages': [
            {
                'id': pkg.id,
                'label': pkg.label,
                'slots_to_block': pkg.slots_to_block,
                'order': pkg.order,
            }
            for pkg in p.packages.all()
        ],
    } for p in products_list])

    context = {
        'products': products_list,
        'products_json': products_json,
        'is_staff': request.user.is_staff,
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

        # Check across ALL resources — only one resource can be booked at a time
        overlapping_booking = Booking.objects.filter(
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
    product_type = request.GET.get('product_type', '')
    slots_needed_str = request.GET.get('slots_needed', '')

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

    # Para FRACTABOX: calcular available_as_start
    if product_type == 'FRACTABOX' and slots_needed_str:
        try:
            slots_needed = int(slots_needed_str)
        except ValueError:
            slots_needed = 1
        for i, slot in enumerate(slots):
            if slot['available'] and i + slots_needed <= len(slots):
                slot['available_as_start'] = all(slots[i + j]['available'] for j in range(slots_needed))
            else:
                slot['available_as_start'] = False

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

    product_id = data.get('product_id')
    fecha_str = data.get('fecha')
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')
    client_name = data.get('client_name', '').strip()
    client_phone = data.get('client_phone', '').strip()

    if not all([product_id, fecha_str, start_time_str, end_time_str]):
        return JsonResponse(
            {'error': 'Parámetros requeridos: product_id, fecha, start_time, end_time'},
            status=400
        )

    if not client_name:
        return JsonResponse({'error': 'El nombre del cliente es requerido'}, status=400)

    if client_phone and not re.match(r'^09\d{8}$', client_phone):
        return JsonResponse(
            {'error': 'Formato de teléfono inválido. Debe ser 09XXXXXXXX'},
            status=400
        )

    try:
        product = Product.objects.select_related('resource').get(id=product_id, is_active=True)
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha/hora inválido'}, status=400)

    try:
        duration_hours = int(
            (datetime.combine(fecha, end_time) - datetime.combine(fecha, start_time)).total_seconds() / 3600
        )
        if product.product_type == 'FRACTABOX':
            package = get_fractabox_package_for_hours(product, duration_hours)
            if not package:
                return JsonResponse({'error': 'Duración inválida para Fractabox'}, status=400)
        code = generate_reservation_code()
        pending = PendingBooking.objects.create(
            resource=product.resource,
            product=product,
            date=fecha,
            start_time=start_time,
            end_time=end_time,
            reservation_code=code,
            client_name=client_name,
            client_phone=client_phone,
            status='PENDING'
        )
        return JsonResponse({'code': pending.reservation_code, 'id': pending.id}, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(['POST'])
@csrf_exempt
def reserva_directa(request):
    """Crea una Booking confirmada directamente (solo is_staff). Usado para Sesión Fotográfica."""
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({'error': 'No autorizado'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    product_id = data.get('product_id')
    fecha_str = data.get('fecha')
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')
    client_name = data.get('client_name', '').strip()
    client_phone = data.get('client_phone', '').strip()

    if not all([product_id, fecha_str, start_time_str, end_time_str]):
        return JsonResponse(
            {'error': 'Parámetros requeridos: product_id, fecha, start_time, end_time'},
            status=400
        )

    if not client_name:
        return JsonResponse({'error': 'El nombre del cliente es requerido'}, status=400)

    if client_phone and not re.match(r'^09\d{8}$', client_phone):
        return JsonResponse(
            {'error': 'Formato de teléfono inválido. Debe ser 09XXXXXXXX'},
            status=400
        )

    try:
        product = Product.objects.select_related('resource').get(id=product_id, is_active=True)
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        start_dt = datetime.combine(fecha, datetime.strptime(start_time_str, '%H:%M').time())
        end_dt = datetime.combine(fecha, datetime.strptime(end_time_str, '%H:%M').time())
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha/hora inválido'}, status=400)

    try:
        duration_hours = int((end_dt - start_dt).total_seconds() / 3600)
        if product.product_type == 'FRACTABOX':
            package = get_fractabox_package_for_hours(product, duration_hours)
            if not package:
                return JsonResponse({'error': 'Duración inválida para Fractabox'}, status=400)
        booking_code = generate_reservation_code()
        pending = None

        if product.product_type == 'FOTO':
            pending = PendingBooking.objects.create(
                resource=product.resource,
                product=product,
                date=fecha,
                start_time=start_dt.time(),
                end_time=end_dt.time(),
                reservation_code=booking_code,
                client_name=client_name,
                client_phone=client_phone,
                status='CONFIRMED',
                notes=f'Código de reserva: {booking_code}',
            )

        booking = Booking(
            resource=product.resource,
            product=product,
            fractabox_package=package if product.product_type == 'FRACTABOX' else None,
            reservation_code=booking_code,
            client_name=client_name,
            client_phone=client_phone,
            start_datetime=start_dt,
            end_datetime=end_dt,
            status='CONFIRMED',
            notes=f'Código de reserva: {booking_code}',
        )
        skip = (product.product_type == 'FOTO')
        booking.save(skip_availability_check=skip)
        return JsonResponse({
            'id': booking.id,
            'code': booking.reservation_code,
            'pending_id': pending.id if pending else None,
        }, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
