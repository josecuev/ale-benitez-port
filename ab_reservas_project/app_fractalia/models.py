from django.db import models
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
import random
import string


class Resource(models.Model):
    name = models.CharField(max_length=200)
    active = models.BooleanField(default=True)
    whatsapp_number = models.CharField(max_length=30, help_text='Incluir código de país, e.g. 595981123456')

    class Meta:
        verbose_name = 'Recurso'
        verbose_name_plural = 'Recursos'

    def __str__(self):
        return self.name


class WeeklyAvailability(models.Model):
    WEEKDAY_CHOICES = [
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]

    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='availability')
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        verbose_name = 'Disponibilidad semanal'
        verbose_name_plural = 'Disponibilidades semanales'
        unique_together = ('resource', 'weekday')

    def __str__(self):
        return f'{self.resource.name} - {self.get_weekday_display()} ({self.start_time}-{self.end_time})'


class Booking(models.Model):
    STATUS_CHOICES = [
        ('CONFIRMED', 'Confirmada'),
        ('CANCELLED', 'Cancelada'),
    ]

    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='bookings')
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CONFIRMED')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        indexes = [
            models.Index(fields=['resource', 'start_datetime', 'status']),
        ]

    def __str__(self):
        return f'{self.resource.name} - {self.start_datetime} ({self.status})'

    def clean(self):
        # Validar que end_datetime sea después de start_datetime
        if self.end_datetime <= self.start_datetime:
            raise ValidationError('La hora de fin debe ser posterior a la hora de inicio.')

        # Si es una reserva confirmada, validar contra otras reservas confirmadas
        if self.status == 'CONFIRMED':
            # Validar que no haya solapamiento con otras reservas confirmadas
            overlapping = Booking.objects.filter(
                resource=self.resource,
                status='CONFIRMED',
                start_datetime__lt=self.end_datetime,
                end_datetime__gt=self.start_datetime
            )

            # Si esta reserva ya existe (tiene id), excluirla de la búsqueda
            if self.id:
                overlapping = overlapping.exclude(id=self.id)

            if overlapping.exists():
                raise ValidationError(
                    f'Ya existe una reserva confirmada que se superpone con este horario.'
                )

            # Validar que esté dentro de los horarios disponibles semanales
            weekday = self.start_datetime.weekday()
            availability = WeeklyAvailability.objects.filter(
                resource=self.resource,
                weekday=weekday
            ).first()

            if availability:
                booking_start_time = self.start_datetime.time()
                booking_end_time = self.end_datetime.time()

                if not (availability.start_time <= booking_start_time and booking_end_time <= availability.end_time):
                    raise ValidationError(
                        f'El horario de la reserva está fuera del horario disponible '
                        f'({availability.start_time} - {availability.end_time}).'
                    )
            else:
                day_name = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'][weekday]
                raise ValidationError(
                    f'No hay horario disponible definido para {day_name}.'
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


def generate_reservation_code():
    """Generate a unique 4-character alphanumeric code (uppercase)"""
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=4))
        if not PendingBooking.objects.filter(reservation_code=code).exists():
            return code


class PendingBooking(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('CONFIRMED', 'Confirmada'),
        ('REJECTED', 'Rechazada'),
    ]

    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='pending_bookings')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    reservation_code = models.CharField(max_length=4, unique=True)
    client_name = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Reserva pendiente'
        verbose_name_plural = 'Reservas pendientes'
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.reservation_code} - {self.resource.name} ({self.status})'
