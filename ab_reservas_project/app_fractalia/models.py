from django.db import models
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
import random
import string


class Resource(models.Model):
    name = models.CharField(max_length=200, verbose_name='Nombre')
    active = models.BooleanField(default=True, verbose_name='Activo')
    whatsapp_number = models.CharField(max_length=30, verbose_name='WhatsApp', help_text='Incluir código de país, e.g. 595981123456')

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

    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='availability', verbose_name='Recurso')
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES, verbose_name='Día')
    start_time = models.TimeField(verbose_name='Hora inicio')
    end_time = models.TimeField(verbose_name='Hora fin')

    class Meta:
        verbose_name = 'Disponibilidad semanal'
        verbose_name_plural = 'Disponibilidades semanales'
        unique_together = ('resource', 'weekday')

    def __str__(self):
        return f'{self.resource.name} - {self.get_weekday_display()} ({self.start_time}-{self.end_time})'


class Product(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ('ALQUILER', 'Alquiler de Estudio'),
        ('FRACTABOX', 'Fractabox'),
        ('FOTO', 'Sesión Fotográfica'),
    ]

    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='products', verbose_name='Recurso')
    name = models.CharField(max_length=200, verbose_name='Nombre')
    description = models.TextField(blank=True, default='', verbose_name='Descripción')
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, verbose_name='Tipo')
    is_public = models.BooleanField(default=True, verbose_name='Visible al público')
    is_active = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'

    def __str__(self):
        return self.name


class FractaboxPackage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='packages', verbose_name='Producto')
    label = models.CharField(max_length=100, verbose_name='Etiqueta')
    slots_to_block = models.PositiveIntegerField(verbose_name='Slots a bloquear')
    order = models.PositiveIntegerField(default=0, verbose_name='Orden')
    is_active = models.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        verbose_name = 'Paquete Fractabox'
        verbose_name_plural = 'Paquetes Fractabox'
        ordering = ['order']

    def __str__(self):
        return f'{self.product.name} - {self.label}'


class Booking(models.Model):
    STATUS_CHOICES = [
        ('CONFIRMED', 'Confirmada'),
        ('CANCELLED', 'Cancelada'),
    ]

    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='bookings', verbose_name='Recurso')
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='bookings', verbose_name='Producto'
    )
    fractabox_package = models.ForeignKey(
        FractaboxPackage, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='bookings', verbose_name='Paquete Fractabox'
    )
    reservation_code = models.CharField(max_length=4, unique=True, null=True, blank=True, verbose_name='Código')
    client_name = models.CharField(max_length=100, blank=True, verbose_name='Cliente')
    start_datetime = models.DateTimeField(verbose_name='Inicio')
    end_datetime = models.DateTimeField(verbose_name='Fin')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='CONFIRMED', verbose_name='Estado')
    notes = models.TextField(blank=True, verbose_name='Notas')
    client_phone = models.CharField(max_length=20, blank=True, default='', verbose_name='Teléfono del cliente')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creada')

    class Meta:
        verbose_name = 'Reserva'
        verbose_name_plural = 'Reservas'
        indexes = [
            models.Index(fields=['resource', 'start_datetime', 'status']),
        ]

    def __str__(self):
        return f'{self.resource.name} - {self.start_datetime} ({self.status})'

    def clean(self):
        if self.end_datetime <= self.start_datetime:
            raise ValidationError('La hora final debe ser más tarde que la hora de inicio.')

        if self.status == 'CONFIRMED':
            # Cross-resource: el espacio físico es uno solo
            overlapping = Booking.objects.filter(
                status='CONFIRMED',
                start_datetime__lt=self.end_datetime,
                end_datetime__gt=self.start_datetime
            )
            if self.id:
                overlapping = overlapping.exclude(id=self.id)

            if overlapping.exists():
                raise ValidationError('Este horario ya está ocupado por otra reserva.')

            if not self.id and not getattr(self, '_skip_availability_check', False):
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
                            f'Este horario está fuera del horario disponible. '
                            f'Disponible de {availability.start_time} a {availability.end_time}.'
                        )
                else:
                    day_name = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'][weekday]
                    raise ValidationError(
                        f'No hay horario disponible configurado para {day_name}.'
                    )

    def save(self, *args, skip_availability_check=False, **kwargs):
        self._skip_availability_check = skip_availability_check
        self.full_clean()
        super().save(*args, **kwargs)


def generate_reservation_code():
    """Generate a unique 4-character alphanumeric code (uppercase)"""
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=4))
        if (
            not PendingBooking.objects.filter(reservation_code=code).exists()
            and not Booking.objects.filter(reservation_code=code).exists()
        ):
            return code


def get_fractabox_package_for_hours(product, hours):
    """Return the active Fractabox package matching a slot duration."""
    if not product or product.product_type != 'FRACTABOX':
        return None
    return product.packages.filter(is_active=True, slots_to_block=hours).first()


class PendingBooking(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('CONFIRMED', 'Confirmada'),
        ('RESPONDED', 'Respondida'),
        ('CANCELLED', 'Cancelada'),
    ]

    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='pending_bookings', verbose_name='Recurso')
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pending_bookings', verbose_name='Producto'
    )
    date = models.DateField(verbose_name='Fecha')
    start_time = models.TimeField(verbose_name='Hora inicio')
    end_time = models.TimeField(verbose_name='Hora fin')
    reservation_code = models.CharField(max_length=4, unique=True, verbose_name='Código')
    client_name = models.CharField(max_length=100, blank=True, verbose_name='Cliente')
    client_phone = models.CharField(max_length=20, blank=True, default='', verbose_name='Teléfono del cliente')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name='Estado')
    notes = models.TextField(blank=True, verbose_name='Notas')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Recibida')

    class Meta:
        verbose_name = 'Reserva pendiente'
        verbose_name_plural = 'Reservas pendientes'
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.reservation_code} - {self.resource.name} ({self.status})'
