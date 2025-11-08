from django.db import models
from django.utils import timezone
from django.core.mail import send_mail
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.conf import settings
import uuid
from datetime import datetime

class ServicioAdicional(models.Model):
    """Catálogo simple de servicios adicionales"""
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Servicios Adicionales"

    def __str__(self):
        return f"{self.nombre} - ${self.precio}"


class HorarioDisponible(models.Model):
    """
    Define horarios disponibles por día de semana.

    DISCRETO: El cliente debe reservar el slot completo (ej: 9:00-10:00)
    CONTINUO: El cliente puede elegir cualquier horario dentro del rango (ej: 9:00-18:00)
    """
    DIAS_SEMANA = [
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]

    TIPOS = [
        ('DISCRETO', 'Discreto - Slot completo'),
        ('CONTINUO', 'Continuo - Cliente elige horario'),
    ]

    tipo = models.CharField(
        max_length=10,
        choices=TIPOS,
        default='DISCRETO',
        help_text='DISCRETO: cliente reserva el slot completo. CONTINUO: cliente elige horario dentro del rango.'
    )
    dia_semana = models.IntegerField(choices=DIAS_SEMANA)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    duracion_minima_minutos = models.PositiveIntegerField(
        default=60,
        help_text='Duración mínima en minutos (solo aplica a CONTINUO)',
        verbose_name='Duración mínima (minutos)'
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Horarios Disponibles"
        ordering = ['dia_semana', 'hora_inicio']

    def __str__(self):
        tipo_emoji = "📦" if self.tipo == 'DISCRETO' else "🔄"
        return f"{tipo_emoji} {self.get_dia_semana_display()} {self.hora_inicio.strftime('%H:%M')}-{self.hora_fin.strftime('%H:%M')}"

    def clean(self):
        if self.hora_inicio >= self.hora_fin:
            raise ValidationError('La hora de inicio debe ser menor que la hora de fin')
        if self.tipo == 'CONTINUO' and self.duracion_minima_minutos <= 0:
            raise ValidationError('La duración mínima debe ser mayor a 0 minutos')

    def duracion_minutos(self):
        """Retorna la duración del slot en minutos"""
        inicio = datetime.combine(datetime.today(), self.hora_inicio)
        fin = datetime.combine(datetime.today(), self.hora_fin)
        return int((fin - inicio).total_seconds() / 60)


class Reserva(models.Model):
    """
    Reserva con fecha y horario específicos.
    """

    # Superset de estados (se filtran dinámicamente en formularios/admin)
    ESTADOS = [
        ('PENDIENTE_VERIFICACION', 'Pendiente de Verificación de Email'),
        ('PENDIENTE_CONFIRMACION', 'Pendiente de Confirmación'),
        ('CONFIRMADA', 'Confirmada'),
        ('CANCELADA', 'Cancelada'),
    ]

    # Identificación
    codigo = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # Datos del cliente
    nombre_cliente = models.CharField(max_length=200, verbose_name='Nombre completo')
    cedula = models.CharField(
        max_length=20,
        verbose_name='Cédula de Identidad',
        help_text='Número de cédula de identidad'
    )
    ruc = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='RUC',
        help_text='Registro Único del Contribuyente (opcional)'
    )
    email_cliente = models.EmailField(verbose_name='Email')
    telefono_cliente = models.CharField(max_length=20, verbose_name='Teléfono')

    # Fecha y horario específico de la reserva
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    # Servicios adicionales
    servicios_adicionales = models.ManyToManyField(
        ServicioAdicional,
        blank=True,
        related_name='reservas'
    )

    # Estado
    estado = models.CharField(
        max_length=30,
        choices=ESTADOS,
        default='PENDIENTE_VERIFICACION'
    )

    # Verificación
    token_verificacion = models.UUIDField(default=uuid.uuid4, editable=False)
    email_verificado_en = models.DateTimeField(null=True, blank=True)

    # Notas
    notas_cliente = models.TextField(blank=True, verbose_name='Comentarios del cliente')
    notas_internas = models.TextField(blank=True, verbose_name='Notas internas del asistente')

    # Fechas de seguimiento
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)
    confirmada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Reservas"
        ordering = ['-creada_en']
        indexes = [
            models.Index(fields=['cedula']),
            models.Index(fields=['ruc']),
            models.Index(fields=['email_cliente']),
            models.Index(fields=['fecha', 'estado']),
        ]

    def __str__(self):
        return f"{self.codigo} - {self.nombre_cliente} - {self.fecha}"

    # -------- utilidades de configuración --------
    @staticmethod
    def _requiere_verificacion() -> bool:
        return getattr(settings, "RESERVAS_REQUIRE_EMAIL_VERIFICATION", True)

    @classmethod
    def estados_permitidos(cls):
        """Estados visibles/permitidos en formularios según flag."""
        if cls._requiere_verificacion():
            permitidos = {'PENDIENTE_VERIFICACION', 'PENDIENTE_CONFIRMACION', 'CONFIRMADA', 'CANCELADA'}
        else:
            permitidos = {'PENDIENTE_CONFIRMACION', 'CONFIRMADA', 'CANCELADA'}
        return [c for c in cls.ESTADOS if c[0] in permitidos]

    def get_dia_semana_display(self):
        dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        return dias[self.fecha.weekday()]

    def total(self):
        """Total de servicios adicionales"""
        return sum(s.precio for s in self.servicios_adicionales.all())

    # -------- validaciones y reglas de negocio --------
    def clean(self):
        """Validación completa de la reserva (incluye estados vs flag)."""
        # Horario válido
        if self.hora_inicio >= self.hora_fin:
            raise ValidationError('La hora de inicio debe ser menor que la hora de fin')

        dia_semana = self.fecha.weekday()
        horarios_disponibles = HorarioDisponible.objects.filter(
            dia_semana=dia_semana,
            activo=True
        )
        if not horarios_disponibles.exists():
            raise ValidationError(f'No hay horarios disponibles para {self.get_dia_semana_display()}')

        slot_valido = False
        for horario in horarios_disponibles:
            if horario.tipo == 'DISCRETO':
                if (self.hora_inicio == horario.hora_inicio and self.hora_fin == horario.hora_fin):
                    slot_valido = True
                    break
            elif horario.tipo == 'CONTINUO':
                if (self.hora_inicio >= horario.hora_inicio and self.hora_fin <= horario.hora_fin):
                    duracion_reserva = (
                        datetime.combine(datetime.today(), self.hora_fin) -
                        datetime.combine(datetime.today(), self.hora_inicio)
                    ).total_seconds() / 60
                    if duracion_reserva >= horario.duracion_minima_minutos:
                        slot_valido = True
                        break
                    else:
                        raise ValidationError(
                            f'La duración mínima para este horario es {horario.duracion_minima_minutos} minutos'
                        )

        if not slot_valido:
            raise ValidationError(
                f'El horario {self.hora_inicio}-{self.hora_fin} no está disponible para {self.get_dia_semana_display()}'
            )

        # Restricción de estados según configuración
        if not self._requiere_verificacion() and self.estado == 'PENDIENTE_VERIFICACION':
            raise ValidationError('El estado "Pendiente de Verificación de Email" no está habilitado por configuración.')

        # Solapes: solo se bloquea contra CONFIRMADAS
        if self.estado in ['CONFIRMADA', 'PENDIENTE_CONFIRMACION'] or not self.pk:
            solapadas = Reserva.objects.filter(
                fecha=self.fecha,
                estado='CONFIRMADA'
            ).exclude(pk=self.pk if self.pk else None)

            for reserva in solapadas:
                if (self.hora_inicio < reserva.hora_fin and self.hora_fin > reserva.hora_inicio):
                    raise ValidationError(
                        f'Ya existe una reserva confirmada que solapa: {reserva.hora_inicio}-{reserva.hora_fin}'
                    )

    def save(self, *args, **kwargs):
        """Ajusta estado inicial según flag, solo al crear."""
        if self._state.adding:
            if not self._requiere_verificacion() and self.estado == 'PENDIENTE_VERIFICACION':
                self.estado = 'PENDIENTE_CONFIRMACION'
        super().save(*args, **kwargs)

    # -------- emails y flujo --------
    def enviar_email_verificacion(self, request=None):
        """Envía email con link de verificación (si aplica usar en tu flujo público)."""
        url_verificacion = reverse('verificar_reserva', kwargs={'token': self.token_verificacion})
        url_completa = request.build_absolute_uri(url_verificacion) if request else url_verificacion

        servicios = self.servicios_adicionales.all()
        mensaje = f"""
Hola {self.nombre_cliente},

Gracias por tu solicitud de reserva en nuestro estudio fotográfico.

Para confirmar tu correo electrónico, haz clic en el siguiente enlace:
{url_completa}

DETALLES DE TU SOLICITUD:
========================
Código: {self.codigo}
Cliente: {self.nombre_cliente}
Cédula: {self.cedula}
{f'RUC: {self.ruc}' if self.ruc else ''}

Fecha: {self.fecha.strftime('%d/%m/%Y')} ({self.get_dia_semana_display()})
Horario: {self.hora_inicio.strftime('%H:%M')} - {self.hora_fin.strftime('%H:%M')}

Servicios adicionales:
{chr(10).join([f'- {s.nombre}: ${s.precio}' for s in servicios]) if servicios.exists() else '- Ninguno'}

Total servicios: ${self.total()}

{f'Tus comentarios: {self.notas_cliente}' if self.notas_cliente else ''}

Una vez verifiques tu email, nuestro equipo te contactará al {self.telefono_cliente}
para coordinar el pago y confirmar tu reserva.

Saludos,
Estudio Fotográfico
        """

        send_mail(
            subject='Verifica tu reserva - Estudio Fotográfico',
            message=mensaje,
            from_email='noreply@estudiofotografico.com',
            recipient_list=[self.email_cliente],
            fail_silently=False,
        )

    def verificar_email(self):
        """Marca el email como verificado y pasa a pendiente de confirmación (si aplica)."""
        if not self._requiere_verificacion():
            # Si no se requiere, no hay nada que verificar
            return False
        if self.estado == 'PENDIENTE_VERIFICACION':
            self.estado = 'PENDIENTE_CONFIRMACION'
            self.email_verificado_en = timezone.now()
            self.save()
            return True
        return False

    def confirmar_reserva(self):
        """Confirma la reserva (solo asistente)"""
        if self.estado == 'PENDIENTE_CONFIRMACION':
            try:
                estado_anterior = self.estado
                self.estado = 'CONFIRMADA'
                self.full_clean()
                self.confirmada_en = timezone.now()
                self.save()
                self.enviar_email_confirmacion()
                return True, "Reserva confirmada exitosamente"
            except ValidationError as e:
                self.estado = estado_anterior
                return False, str(e)
        return False, "La reserva no está en estado pendiente de confirmación"

    def cancelar_confirmacion(self):
        """Revierte una confirmación (cancelar reserva)"""
        if self.estado == 'CONFIRMADA':
            self.estado = 'CANCELADA'
            self.confirmada_en = None
            self.save()
            return True
        return False

    def enviar_email_confirmacion(self):
        """Email de confirmación al cliente"""
        servicios = self.servicios_adicionales.all()
        mensaje = f"""
¡Hola {self.nombre_cliente}!

¡Tu reserva ha sido CONFIRMADA! ✓

DETALLES DE TU RESERVA:
========================
Código: {self.codigo}
Cliente: {self.nombre_cliente}
Cédula: {self.cedula}
{f'RUC: {self.ruc}' if self.ruc else ''}

Fecha: {self.fecha.strftime('%d/%m/%Y')} ({self.get_dia_semana_display()})
Horario: {self.hora_inicio.strftime('%H:%M')} - {self.hora_fin.strftime('%H:%M')}

SERVICIOS CONTRATADOS:
{chr(10).join([f'- {s.nombre}: ${s.precio}' for s in servicios]) if servicios.exists() else '- Sesión estándar'}

Total servicios adicionales: ${self.total()}

{f'Notas: {self.notas_cliente}' if self.notas_cliente else ''}

Te esperamos en la fecha y hora indicada.
No olvides traer tu cédula de identidad.

¡Gracias por confiar en nosotros!

Estudio Fotográfico
Contacto: {self.telefono_cliente}
        """

        send_mail(
            subject=f'✓ Reserva Confirmada - {self.fecha.strftime("%d/%m/%Y")}',
            message=mensaje,
            from_email='noreply@estudiofotografico.com',
            recipient_list=[self.email_cliente],
            fail_silently=False,
        )

