"""
Seed de datos ilustrativos para desarrollo.
Ejecutar: docker exec ab-reservas-web python seed_dev.py
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ab_reservas_project.settings')
django.setup()

import random
from datetime import time, timedelta, datetime as dt
from django.utils import timezone
from app_fractalia.models import Resource, PendingBooking, Booking, generate_reservation_code
from app_analytics.models import PageView

now   = timezone.now()
today = timezone.localdate()
res   = Resource.objects.get(id=1)

NAMES = [
    'Lucía Ramírez', 'Martín González', 'Valentina Pérez', 'Diego Fernández',
    'Camila Torres', 'Sebastián López', 'Ana Benítez', 'Rodrigo Sánchez',
    'Florencia Ortiz', 'Mateo Herrera', 'Isabella Morales', 'Santiago Ruiz',
    'Emilia Castro', 'Nicolás Vargas', 'Sofía Medina', 'Tomás Jiménez',
    'Renata Guerrero', 'Agustín Romero', 'Catalina Navarro', 'Franco Silva',
]
PHONES = [f'09{random.randint(10000000, 99999999)}' for _ in range(20)]

# ── Limpiar todo ───────────────────────────────────────────────────────────
PendingBooking.objects.all().delete()
Booking.objects.all().delete()
PageView.objects.all().delete()
print('Datos anteriores eliminados.')

# ── Pasado: Pre-reservas con sus respectivas Bookings ─────────────────────
# La confirmación de una PendingBooking → crea Booking con codigo en notes.
# Para seed: solo un slot por día para evitar conflictos de validación.

pb_stats = {'CONFIRMED': 0, 'CANCELLED': 0, 'PENDING_expired': 0}

for days_back in range(1, 45):
    day = today - timedelta(days=days_back)
    if day.weekday() >= 5:
        continue

    # Slots disponibles del día
    available_slots = list(range(9, 17))
    confirmed_slots = set()

    n_requests = random.randint(2, 5)
    random.shuffle(available_slots)
    slots_for_day = available_slots[:n_requests]

    for h in slots_for_day:
        code = generate_reservation_code()
        name = random.choice(NAMES)
        phone = random.choice(PHONES)
        # La pre-reserva llegó 1-3 días antes del turno
        days_before = random.randint(0, min(3, days_back))
        created_at = timezone.make_aware(
            dt.combine(day - timedelta(days=days_before),
                       time(random.randint(8, 21), random.randint(0, 59)))
        )

        roll = random.random()

        if roll < 0.60 and h not in confirmed_slots:
            # CONFIRMED: crear PendingBooking + Booking (respetando la lógica real)
            try:
                start_dt = timezone.make_aware(dt.combine(day, time(h, 0)))
                end_dt   = timezone.make_aware(dt.combine(day, time(h+1, 0)))
                # Booking con código en notes
                booking = Booking.objects.create(
                    resource=res,
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                    status='CONFIRMED',
                    client_phone=phone,
                    notes=f'Código de reserva: {code}',
                )
                # Tiempo de respuesta: entre 1h y 48h después de recibida
                response_hours = random.randint(1, 48)
                booking_created = created_at + timedelta(hours=response_hours)
                Booking.objects.filter(pk=booking.pk).update(created_at=min(booking_created, now))

                pb = PendingBooking.objects.create(
                    resource=res, date=day,
                    start_time=time(h, 0), end_time=time(h+1, 0),
                    reservation_code=code,
                    client_name=name, client_phone=phone,
                    status='CONFIRMED',
                )
                PendingBooking.objects.filter(pk=pb.pk).update(created_at=created_at)
                confirmed_slots.add(h)
                pb_stats['CONFIRMED'] += 1
            except Exception:
                pass

        elif roll < 0.80:
            # CANCELLED
            try:
                pb = PendingBooking.objects.create(
                    resource=res, date=day,
                    start_time=time(h, 0), end_time=time(h+1, 0),
                    reservation_code=code,
                    client_name=name, client_phone=phone,
                    status='CANCELLED',
                )
                PendingBooking.objects.filter(pk=pb.pk).update(created_at=created_at)
                pb_stats['CANCELLED'] += 1
            except Exception:
                pass

        else:
            # PENDING vencida (nunca gestionada)
            try:
                pb = PendingBooking.objects.create(
                    resource=res, date=day,
                    start_time=time(h, 0), end_time=time(h+1, 0),
                    reservation_code=code,
                    client_name=name, client_phone=phone,
                    status='PENDING',
                )
                PendingBooking.objects.filter(pk=pb.pk).update(created_at=created_at)
                pb_stats['PENDING_expired'] += 1
            except Exception:
                pass

print(f'Pre-reservas pasadas → {pb_stats}')

# ── Futuro: pre-reservas pendientes de gestionar ───────────────────────────
future_booked_slots = {}  # {day: [hora, ...]}
future_pb = 0

# Primero, algunas Bookings ya confirmadas para el futuro
for days_ahead in [2, 3, 4, 6, 7, 8, 10]:
    day = today + timedelta(days=days_ahead)
    if day.weekday() >= 5:
        continue
    for h in random.sample(range(9, 17), k=random.randint(1, 2)):
        code = generate_reservation_code()
        phone = random.choice(PHONES)
        try:
            pb = PendingBooking.objects.create(
                resource=res, date=day,
                start_time=time(h, 0), end_time=time(h+1, 0),
                reservation_code=code,
                client_name=random.choice(NAMES), client_phone=phone,
                status='CONFIRMED',
            )
            start_dt = timezone.make_aware(dt.combine(day, time(h, 0)))
            end_dt   = timezone.make_aware(dt.combine(day, time(h+1, 0)))
            Booking.objects.create(
                resource=res, start_datetime=start_dt, end_datetime=end_dt,
                status='CONFIRMED', client_phone=phone,
                notes=f'Código de reserva: {code}',
            )
            future_booked_slots.setdefault(day, []).append(h)
        except Exception:
            pass

# Pre-reservas PENDING futuras, algunas solapadas con las Bookings anteriores
for days_ahead in range(1, 16):
    day = today + timedelta(days=days_ahead)
    if day.weekday() >= 5:
        continue
    n = random.randint(1, 3)
    for _ in range(n):
        h = random.choice(range(9, 17))
        try:
            pb = PendingBooking.objects.create(
                resource=res, date=day,
                start_time=time(h, 0), end_time=time(h+1, 0),
                reservation_code=generate_reservation_code(),
                client_name=random.choice(NAMES), client_phone=random.choice(PHONES),
                status='PENDING',
            )
            future_pb += 1
        except Exception:
            pass

print(f'Pre-reservas futuras PENDING: {future_pb}')
booked = sum(len(v) for v in future_booked_slots.values())
print(f'Reservas futuras confirmadas (algunas generan solapamientos): {booked}')

# ── PageViews realistas ────────────────────────────────────────────────────
pages_w = ['portfolio'] * 5 + ['links'] * 3 + ['fractalia_calendar'] * 2
referrers = ['instagram.com'] * 4 + ['google.com'] * 2 + [''] * 4
pv_count = 0
for days_back in range(30):
    day = today - timedelta(days=days_back)
    n = random.randint(6, 30) if day.weekday() < 5 else random.randint(2, 12)
    for _ in range(n):
        ts = timezone.make_aware(
            dt.combine(day, time(random.randint(8, 23), random.randint(0, 59)))
        )
        PageView.objects.create(
            page=random.choice(pages_w),
            timestamp=ts,
            ip_hash=PageView.hash_ip(f'192.168.1.{random.randint(1, 80)}'),
            referrer=random.choice(referrers),
        )
        pv_count += 1

print(f'PageViews: {pv_count}')

# ── Resumen final ──────────────────────────────────────────────────────────
from django.utils import timezone as tz
print()
print('── Resumen ───────────────────────────────────────')
print(f'PendingBookings  : {PendingBooking.objects.count()}')
print(f'  PENDING        : {PendingBooking.objects.filter(status="PENDING").count()}')
print(f'  CONFIRMED      : {PendingBooking.objects.filter(status="CONFIRMED").count()}')
print(f'  CANCELLED      : {PendingBooking.objects.filter(status="CANCELLED").count()}')
print(f'Bookings         : {Booking.objects.filter(status="CONFIRMED").count()}')
print(f'PageViews        : {PageView.objects.count()}')
