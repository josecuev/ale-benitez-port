"""
Arranque de Django y helpers compartidos por los tools del MCP.

El servicio corre en la misma imagen que Django y usa la ORM directamente,
así que hereda toda la validación de los modelos (incluido el chequeo de
solapamiento de Booking.clean()).
"""
import os
import zoneinfo
from datetime import date as _date, datetime, time as _time
from functools import wraps

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ab_reservas_project.settings")
django.setup()

from django.db import close_old_connections  # noqa: E402

ASUNCION = zoneinfo.ZoneInfo("America/Asuncion")

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def ahora():
    """Ahora en hora de Asunción. Nunca usar timezone.now() pelado."""
    from django.utils import timezone
    return timezone.now().astimezone(ASUNCION)


def hoy():
    return ahora().date()


def aware(naive: datetime) -> datetime:
    return naive.replace(tzinfo=ASUNCION)


def dt_de(fecha: _date, hora: _time) -> datetime:
    return aware(datetime.combine(fecha, hora))


def fecha_larga(d: _date) -> str:
    """'jueves, 17 de julio de 2026'"""
    return f"{DIAS[d.weekday()]}, {d.day} de {MESES[d.month - 1]} de {d.year}"


def parse_fecha(s: str) -> _date:
    """Acepta ISO (2026-07-17) o d/m/YYYY."""
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Fecha inválida: '{s}'. Usá AAAA-MM-DD.")


def parse_hora(s: str) -> _time:
    """Acepta 15:00, 15, 15hs."""
    s = (s or "").strip().lower().replace("hs", "").replace("h", "").strip()
    for fmt in ("%H:%M", "%H"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Hora inválida: '{s}'. Usá HH:MM.")


def cliente_str(obj, link: bool = True) -> str:
    """
    Formato fijo de todo output: 'María González (0981234567, A7K2)'.

    Con link=True el teléfono sale como markdown `tel:` para poder llamar de un
    toque. Se usa link=False para textos que se guardan en base (LogEntry, notas),
    donde el markdown sería ruido.
    """
    nombre = (getattr(obj, "client_name", "") or "").strip() or "Sin nombre"
    datos = []
    tel = (getattr(obj, "client_phone", "") or "").strip()
    if tel:
        intl = telefono_internacional(tel)
        datos.append(f"[{tel}](tel:+{intl})" if link and intl else tel)
    codigo = getattr(obj, "reservation_code", "") or ""
    if codigo:
        datos.append(codigo)
    return f"{nombre} ({', '.join(datos)})" if datos else nombre


def telefono_internacional(tel: str) -> str | None:
    """09XXXXXXXX (Paraguay) -> 5959XXXXXXXX, listo para wa.me."""
    tel = (tel or "").strip()
    if not tel:
        return None
    if tel.startswith("0"):
        return "595" + tel[1:]
    if tel.startswith("595"):
        return tel
    return tel


def whatsapp(tel: str, mensaje: str) -> dict | None:
    """
    Link de WhatsApp hacia EL CLIENTE.

    Ojo: el admin arma este link contra resource.whatsapp_number, o sea el número
    del propio estudio — abre un chat con uno mismo. Acá va al cliente, que es
    la intención del botón.
    """
    from urllib.parse import quote
    destino = telefono_internacional(tel)
    if not destino:
        return None
    return {"url": f"https://wa.me/{destino}?text={quote(mensaje)}", "mensaje": mensaje}


def con_db(fn):
    """
    FastMCP corre los tools sync en un pool de hilos; Django abre una conexión
    por hilo. Sin esto quedan conexiones colgadas.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        close_old_connections()
        try:
            return fn(*args, **kwargs)
        finally:
            close_old_connections()
    return wrapper


def registrar(objeto, accion: str, detalle: str):
    """
    Deja rastro en django_admin_log (LogEntry), el modelo integrado de Django.
    Sin migraciones: la tabla ya existe y el admin la usa.
    """
    from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
    from django.contrib.auth import get_user_model
    from django.contrib.contenttypes.models import ContentType

    flags = {"alta": ADDITION, "cambio": CHANGE, "baja": DELETION}
    User = get_user_model()
    usuario = (User.objects.filter(username=os.environ.get("MCP_USER", "")).first()
               or User.objects.filter(is_superuser=True).order_by("id").first())
    if not usuario:
        return
    try:
        LogEntry.objects.log_action(
            user_id=usuario.pk,
            content_type_id=ContentType.objects.get_for_model(objeto).pk,
            object_id=objeto.pk,
            object_repr=str(objeto)[:200],
            action_flag=flags.get(accion, CHANGE),
            change_message=f"[MCP] {detalle}",
        )
    except Exception:
        # El rastro es deseable, no crítico: nunca debe tumbar la operación.
        pass
