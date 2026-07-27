"""
Servidor MCP de Fractalia.

Asiste al encargado que confirma pre-reservas. Toda la lógica replica el ciclo
que ya existe en el admin de Django (app_fractalia/admin.py):

  PENDING ──confirmar──> CONFIRMED  (+ crea Booking, bloquea el calendario)
     │                      │
     │                      └──deshacer──> PENDING  (borra Booking)
     └──rechazar──> RESPONDED ──deshacer──> PENDING

No hay migraciones: usa la ORM y el LogEntry integrado de Django.
"""
import os
from datetime import timedelta

from fastmcp import FastMCP

from .auth import construir_auth
from .bootstrap import (
    ahora, hoy, dt_de, fecha_larga, parse_fecha, parse_hora,
    cliente_str, whatsapp, telefono_internacional, con_db, registrar,
)

from app_fractalia.models import (  # noqa: E402
    Booking, PendingBooking, Product, Resource,
    generate_reservation_code, get_fractabox_package_for_hours,
)

mcp = FastMCP(
    name="fractalia",
    # Fail-closed: con transporte HTTP fuera de debug, sin clave pública el
    # servicio no arranca. Ver auth.py.
    auth=construir_auth(
        transporte=os.environ.get("MCP_TRANSPORT", "stdio").lower(),
        debug=os.environ.get("DEBUG", "0") == "1",
    ),
    instructions=(
        "Asistente de reservas del estudio Fractalia. Sirve para revisar y cerrar "
        "pre-reservas pendientes. Nombrá siempre a las personas como "
        "'Nombre (teléfono, código)'. El criterio de si una reserva pasa o no lo "
        "decide la persona encargada por fuera del sistema (transferencia recibida, "
        "cliente excepcional); vos solo ejecutás lo que te indique."
    ),
)


# ─────────────────────────── helpers de dominio ────────────────────────────

def _vencida(pb) -> bool:
    """Misma definición que el filtro 'Vencidas sin respuesta' del admin."""
    n = ahora()
    return pb.date < n.date() or (pb.date == n.date() and pb.start_time < n.time())


def _duracion_horas(pb) -> int:
    return int((dt_de(pb.date, pb.end_time) - dt_de(pb.date, pb.start_time)).total_seconds() / 3600)


def _choca_con_confirmada(pb) -> bool:
    """La pre-reserva solapa con una Booking ya confirmada."""
    return Booking.objects.filter(
        status="CONFIRMED",
        start_datetime__lt=dt_de(pb.date, pb.end_time),
        end_datetime__gt=dt_de(pb.date, pb.start_time),
    ).exists()


def _compiten(pb):
    """Otras pre-reservas PENDING del mismo recurso que pisan el mismo horario."""
    return [
        o for o in PendingBooking.objects.filter(
            status="PENDING", resource_id=pb.resource_id, date=pb.date,
        ).exclude(pk=pb.pk)
        if pb.start_time < o.end_time and pb.end_time > o.start_time
    ]


def _nombre_producto(pb) -> str:
    """Para Fractabox agrega la etiqueta del paquete, igual que el admin."""
    if not pb.product:
        return pb.resource.name if pb.resource_id else "Sin producto"
    if pb.product.product_type == "FRACTABOX":
        paq = get_fractabox_package_for_hours(pb.product, _duracion_horas(pb))
        if paq:
            return f"{pb.product.name} ({paq.label})"
    return pb.product.name


def _resumen(pb, con_conflictos=True) -> dict:
    d = {
        "cliente": cliente_str(pb),
        "codigo": pb.reservation_code,
        "producto": _nombre_producto(pb),
        "fecha": pb.date.isoformat(),
        "fecha_legible": fecha_larga(pb.date),
        "horario": f"{pb.start_time.strftime('%H:%M')}–{pb.end_time.strftime('%H:%M')}",
        "estado": pb.get_status_display(),
        "solicitada_hace_dias": (hoy() - pb.created_at.astimezone(ahora().tzinfo).date()).days,
    }
    if pb.status == "PENDING":
        d["vencida"] = _vencida(pb)
    if con_conflictos:
        d["horario_ya_confirmado_a_otro"] = _choca_con_confirmada(pb)
        otros = _compiten(pb)
        if otros:
            d["compite_con"] = [cliente_str(o) for o in otros]
    return d


def _mensaje_confirmacion(pb) -> str:
    nombre = (pb.client_name or "").split(" ")[0] or "Hola"
    return (
        f"Hola {nombre}, te confirmo tu reserva de {_nombre_producto(pb)} "
        f"para el {fecha_larga(pb.date)} de {pb.start_time.strftime('%H:%M')} "
        f"a {pb.end_time.strftime('%H:%M')}. Código: {pb.reservation_code}. "
        f"¡Te esperamos!"
    )


def _buscar(codigo: str):
    return PendingBooking.objects.select_related("product", "resource").filter(
        reservation_code__iexact=(codigo or "").strip()
    ).first()


def _booking_de(pb):
    """El admin busca por notes; acá cubrimos ambos campos."""
    from django.db.models import Q
    return Booking.objects.filter(
        Q(reservation_code=pb.reservation_code) | Q(notes__contains=pb.reservation_code)
    ).first()


def _no_encontrada(codigo):
    return {"ok": False, "error": f"No existe ninguna pre-reserva con código {codigo}."}


def _reglas_de_negocio(prod, f, hi, hf) -> list:
    """
    Reglas que el formulario público impone y que un alta directa podría saltear
    sin querer. Se devuelven como advertencias: el staff puede forzarlas —igual
    que reserva_directa en las vistas— pero nunca en silencio.
    """
    avisos = []

    if f < hoy():
        avisos.append(f"La fecha ({fecha_larga(f)}) ya pasó. El calendario público "
                      f"solo ofrece fechas de hoy en adelante.")

    if hi.minute or hf.minute:
        avisos.append("El calendario trabaja en bloques de una hora en punto. "
                      "Un horario partido no se va a ver bien en la grilla.")

    if prod and not prod.resource.active:
        avisos.append(f"El recurso '{prod.resource.name}' está marcado como inactivo.")

    horas = int((dt_de(f, hf) - dt_de(f, hi)).total_seconds() / 3600)

    if prod and prod.product_type == "FRACTABOX":
        if not get_fractabox_package_for_hours(prod, horas):
            activos = ", ".join(f"{p.label} ({p.slots_to_block}h)"
                                for p in prod.packages.filter(is_active=True)) or "ninguno"
            avisos.append(f"No hay paquete Fractabox activo de {horas}h. "
                          f"El formulario público rechazaría esta duración. "
                          f"Paquetes disponibles: {activos}.")

    # Regla dura del calendario: el alquiler de estudio se vende en bloques de
    # 2, 4, 6 u 8 horas (calendario.html -> VALID_DURATIONS). Fotografía no tiene
    # tope y Fractabox se rige por su paquete, así que la regla es solo de ALQUILER.
    if prod and prod.product_type == "ALQUILER" and horas not in (2, 4, 6, 8):
        avisos.append(f"El alquiler de estudio se reserva en bloques de 2, 4, 6 u 8 "
                      f"horas. Estás cargando {horas}h, que el calendario público "
                      f"no permitiría.")

    from app_fractalia.models import WeeklyAvailability
    disp = WeeklyAvailability.objects.filter(
        resource=prod.resource if prod else None, weekday=f.weekday()).first()
    if not disp:
        avisos.append(f"No hay horario configurado para los "
                      f"{['lunes','martes','miércoles','jueves','viernes','sábados','domingos'][f.weekday()]}.")
    elif not (disp.start_time <= hi and hf <= disp.end_time):
        avisos.append(f"Queda fuera del horario de atención "
                      f"({disp.start_time.strftime('%H:%M')}–{disp.end_time.strftime('%H:%M')}).")

    return avisos


# ────────────────────────────── revisión ───────────────────────────────────

@mcp.tool
@con_db
def bandeja(incluir_vencidas: bool = True, limite: int = 50) -> dict:
    """
    Cola de pre-reservas sin resolver, priorizada: primero las vencidas
    (fecha ya pasada), después las más próximas a ocurrir.

    Es el punto de partida del repaso diario.
    """
    qs = PendingBooking.objects.select_related("product", "resource").filter(status="PENDING")
    items = sorted(qs, key=lambda p: (p.date, p.start_time))
    vencidas = [p for p in items if _vencida(p)]
    activas = [p for p in items if not _vencida(p)]

    orden = (vencidas if incluir_vencidas else []) + activas
    return {
        "total_pendientes": len(items),
        "vencidas": len(vencidas),
        "activas": len(activas),
        "items": [_resumen(p) for p in orden[:limite]],
    }


@mcp.tool
@con_db
def siguiente() -> dict:
    """
    Devuelve UNA sola pre-reserva para revisar, la más urgente sin resolver.
    Pensado para el repaso de a uno: mostrás esta, se decide, y volvés a llamar.
    """
    qs = PendingBooking.objects.select_related("product", "resource").filter(status="PENDING")
    items = sorted(qs, key=lambda p: (not _vencida(p), p.date, p.start_time))
    if not items:
        return {"ok": True, "quedan": 0, "mensaje": "No queda ninguna pre-reserva pendiente."}
    pb = items[0]
    d = _resumen(pb)
    d["quedan"] = len(items)
    d["ok"] = True
    return d


@mcp.tool
@con_db
def buscar(texto: str, limite: int = 15) -> dict:
    """
    Busca por nombre, teléfono o código, en cualquier estado.
    Usalo cuando te nombren a alguien y no tengas el código a mano.
    """
    from django.db.models import Q
    t = (texto or "").strip()
    if len(t) < 2:
        return {"ok": False, "error": "Escribí al menos 2 caracteres."}

    qs = (PendingBooking.objects.select_related("product", "resource").filter(
        Q(client_name__icontains=t) | Q(client_phone__icontains=t)
        | Q(reservation_code__icontains=t)
    ).order_by("-created_at")[:max(1, min(limite, 50))])

    resultados = [_resumen(p, con_conflictos=False) for p in qs]
    return {"ok": True, "encontrados": len(resultados), "resultados": resultados}


@mcp.tool
@con_db
def ver(codigo: str) -> dict:
    """Ficha completa de una pre-reserva, con conflictos y el historial del cliente."""
    pb = _buscar(codigo)
    if not pb:
        return _no_encontrada(codigo)

    d = _resumen(pb)
    d["ok"] = True
    d["notas"] = pb.notes or ""
    if pb.client_phone:
        previas = PendingBooking.objects.filter(client_phone=pb.client_phone).exclude(pk=pb.pk)
        d["historial_cliente"] = {
            "solicitudes_previas": previas.count(),
            "estados": sorted({p.get_status_display() for p in previas}),
        }
    b = _booking_de(pb)
    if b:
        d["reserva_asociada"] = {"id": b.id, "estado": b.get_status_display()}
    return d


# ─────────────────────────── cierre del ciclo ──────────────────────────────

@mcp.tool
@con_db
def confirmar(codigo: str) -> dict:
    """
    Confirma la pre-reserva: crea la reserva y bloquea el horario en el calendario
    público. Devuelve el mensaje de WhatsApp listo para enviarle al cliente.

    Usalo cuando la persona encargada te diga que esta pasa.
    """
    pb = _buscar(codigo)
    if not pb:
        return _no_encontrada(codigo)
    if pb.status != "PENDING":
        return {"ok": False, "error": f"{cliente_str(pb)} ya está en estado "
                                      f"'{pb.get_status_display()}', no se puede confirmar."}

    if _choca_con_confirmada(pb):
        otras = Booking.objects.filter(
            status="CONFIRMED",
            start_datetime__lt=dt_de(pb.date, pb.end_time),
            end_datetime__gt=dt_de(pb.date, pb.start_time),
        )
        return {
            "ok": False,
            "error": "Ese horario ya está confirmado para otra persona.",
            "ocupado_por": [cliente_str(b) for b in otras],
            "sugerencia": f"Podés usar rechazar('{pb.reservation_code}') con el motivo, "
                          f"o agenda('{pb.date.isoformat()}') para ofrecer otro horario.",
        }

    paquete = None
    if pb.product and pb.product.product_type == "FRACTABOX":
        paquete = get_fractabox_package_for_hours(pb.product, _duracion_horas(pb))
        if not paquete:
            return {"ok": False, "error": "La duración no coincide con ningún paquete "
                                          "Fractabox activo. Revisalo en el admin."}

    try:
        booking = Booking.objects.create(
            resource=pb.resource,
            product=pb.product,
            fractabox_package=paquete,
            reservation_code=pb.reservation_code,
            client_name=pb.client_name,
            client_phone=pb.client_phone,
            start_datetime=dt_de(pb.date, pb.start_time),
            end_datetime=dt_de(pb.date, pb.end_time),
            status="CONFIRMED",
            notes=f"Código de reserva: {pb.reservation_code}",
        )
    except Exception as e:
        limpio = str(e).replace('["__all__"]', "").strip("[]{}'\" ")
        return {"ok": False, "error": f"No se pudo confirmar: {limpio}"}

    pb.status = "CONFIRMED"
    pb.save()
    registrar(pb, "cambio", f"Confirmada por MCP -> Booking #{booking.id}")

    compiten = _compiten(pb)
    return {
        "ok": True,
        "confirmada": cliente_str(pb),
        "producto": _nombre_producto(pb),
        "cuando": f"{fecha_larga(pb.date)}, {pb.start_time.strftime('%H:%M')}–"
                  f"{pb.end_time.strftime('%H:%M')}",
        "whatsapp": whatsapp(pb.client_phone, _mensaje_confirmacion(pb)),
        "calendario": "El horario quedó bloqueado en el calendario público.",
        "quedaron_sin_horario": [cliente_str(o) for o in compiten] or None,
        "deshacer": f"deshacer('{pb.reservation_code}') mientras la fecha no haya pasado.",
    }


@mcp.tool
@con_db
def rechazar(codigo: str, motivo: str = "") -> dict:
    """
    Marca la pre-reserva como respondida sin confirmar el turno: el cliente fue
    contactado pero no se le reserva el horario. Devuelve horarios libres cercanos
    para poder ofrecerle una alternativa.

    Usalo cuando la persona encargada te diga que esta no pasa.
    """
    pb = _buscar(codigo)
    if not pb:
        return _no_encontrada(codigo)
    if pb.status != "PENDING":
        return {"ok": False, "error": f"{cliente_str(pb)} ya está en estado "
                                      f"'{pb.get_status_display()}'."}

    pb.status = "RESPONDED"
    if motivo:
        pb.notes = f"{pb.notes}\n[MCP] Motivo: {motivo}".strip()
    pb.save()
    registrar(pb, "cambio", f"Rechazada por MCP. Motivo: {motivo or 'sin especificar'}")

    return {
        "ok": True,
        "rechazada": cliente_str(pb),
        "motivo": motivo or "sin especificar",
        "alternativas_cercanas": _libres_cerca(pb),
        "deshacer": f"deshacer('{pb.reservation_code}') mientras la fecha no haya pasado.",
    }


def _libres_cerca(pb, dias: int = 7) -> list:
    """Huecos libres alrededor de lo que el cliente pidió."""
    from app_fractalia.views import _get_slots_for_date
    out = []
    for i in range(dias):
        f = pb.date + timedelta(days=i)
        if f < hoy():
            continue
        slots = _get_slots_for_date(pb.resource, f)
        if not slots:
            continue
        libres = [s["time"] for s in slots if s["available"]]
        if libres:
            out.append({"fecha": f.isoformat(), "fecha_legible": fecha_larga(f),
                        "horarios_libres": libres})
        if len(out) >= 3:
            break
    return out


# ──────────────────────────── alta y agenda ────────────────────────────────

@mcp.tool
@con_db
def productos() -> dict:
    """Lista los productos activos, para saber qué se puede reservar."""
    return {"productos": [
        {"nombre": p.name, "tipo": p.get_product_type_display(),
         "recurso": p.resource.name,
         "paquetes": [f"{q.label} ({q.slots_to_block}h)"
                      for q in p.packages.filter(is_active=True)] or None}
        for p in Product.objects.select_related("resource").filter(is_active=True)
    ]}


@mcp.tool
@con_db
def crear_reserva(cliente: str, telefono: str, producto: str, fecha: str,
                  hora_inicio: str, hora_fin: str, forzar: bool = False) -> dict:
    """
    Crea una reserva confirmada desde cero, sin pasar por el calendario público.
    Para cuando el cliente arregló por WhatsApp o en persona.

    `forzar=True` saltea la restricción de horario semanal (igual que un admin).
    """
    try:
        f = parse_fecha(fecha)
        hi, hf = parse_hora(hora_inicio), parse_hora(hora_fin)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    if not (cliente or "").strip():
        return {"ok": False, "error": "El nombre del cliente es obligatorio."}

    import re
    tel = (telefono or "").strip()
    if tel and not re.match(r"^09\d{8}$", tel):
        return {"ok": False, "error": "Teléfono inválido. Debe ser 09XXXXXXXX."}

    prod = (Product.objects.select_related("resource")
            .filter(is_active=True, name__icontains=producto.strip()).first())
    if not prod:
        return {"ok": False, "error": f"No encontré un producto activo que coincida con "
                                      f"'{producto}'. Usá productos() para ver la lista."}

    inicio, fin = dt_de(f, hi), dt_de(f, hf)
    if fin <= inicio:
        return {"ok": False, "error": "La hora de fin debe ser posterior a la de inicio."}

    choque = Booking.objects.filter(status="CONFIRMED",
                                    start_datetime__lt=fin, end_datetime__gt=inicio)
    if choque.exists():
        return {"ok": False, "error": "Ese horario ya está ocupado.",
                "ocupado_por": [cliente_str(b) for b in choque]}

    # Reglas del formulario público. Sin forzar=True no se saltean en silencio.
    avisos = _reglas_de_negocio(prod, f, hi, hf)
    if avisos and not forzar:
        return {"ok": False,
                "error": "La reserva no cumple las reglas del calendario público.",
                "reglas_incumplidas": avisos,
                "sugerencia": "Corregí los datos, o repetí con forzar=True si "
                              "querés hacerlo igual como excepción de staff."}

    horas = int((fin - inicio).total_seconds() / 3600)
    paquete = (get_fractabox_package_for_hours(prod, horas)
               if prod.product_type == "FRACTABOX" else None)
    codigo = generate_reservation_code()

    # Se crea también la PendingBooking como registro de origen, igual que
    # hace reserva_directa en las vistas.
    pb = PendingBooking.objects.create(
        resource=prod.resource, product=prod, date=f,
        start_time=hi, end_time=hf, reservation_code=codigo,
        client_name=cliente.strip(), client_phone=tel, status="CONFIRMED",
        notes=f"Alta directa desde MCP. Código: {codigo}",
    )
    booking = Booking(
        resource=prod.resource, product=prod, fractabox_package=paquete,
        reservation_code=codigo, client_name=cliente.strip(), client_phone=tel,
        start_datetime=inicio, end_datetime=fin, status="CONFIRMED",
        notes=f"Alta directa desde MCP. Código: {codigo}",
    )
    try:
        booking.save(skip_availability_check=forzar)
    except Exception as e:
        pb.delete()
        limpio = str(e).replace('["__all__"]', "").strip("[]{}'\" ")
        return {"ok": False, "error": f"No se pudo crear: {limpio}",
                "sugerencia": "Si es fuera del horario habitual, probá con forzar=True."}

    registrar(booking, "alta",
              f"Reserva creada desde MCP para {cliente_str(booking, link=False)}")
    return {
        "ok": True,
        "creada": cliente_str(booking),
        "producto": prod.name,
        "cuando": f"{fecha_larga(f)}, {hi.strftime('%H:%M')}–{hf.strftime('%H:%M')}",
        "codigo": codigo,
        "reglas_salteadas": avisos or None,
        "whatsapp": whatsapp(tel, _mensaje_confirmacion(pb)),
        "deshacer": f"deshacer('{codigo}') mientras la fecha no haya pasado.",
    }


@mcp.tool
@con_db
def bloquear(fecha: str, hora_inicio: str, hora_fin: str, motivo: str = "Bloqueado") -> dict:
    """
    Tapa un horario sin cliente: uso propio, mantenimiento, etc.
    Queda ocupado en el calendario público.
    """
    try:
        f = parse_fecha(fecha)
        hi, hf = parse_hora(hora_inicio), parse_hora(hora_fin)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    recurso = Resource.objects.filter(active=True).first()
    if not recurso:
        return {"ok": False, "error": "No hay ningún recurso activo configurado."}

    inicio, fin = dt_de(f, hi), dt_de(f, hf)
    if fin <= inicio:
        return {"ok": False, "error": "La hora de fin debe ser posterior a la de inicio."}
    if Booking.objects.filter(status="CONFIRMED",
                              start_datetime__lt=fin, end_datetime__gt=inicio).exists():
        return {"ok": False, "error": "Ese horario ya está ocupado."}

    codigo = generate_reservation_code()
    b = Booking(resource=recurso, reservation_code=codigo,
                client_name=f"[BLOQUEO] {motivo}", start_datetime=inicio, end_datetime=fin,
                status="CONFIRMED", notes=f"Bloqueo desde MCP. Código: {codigo}")
    try:
        b.save(skip_availability_check=True)
    except Exception as e:
        return {"ok": False, "error": f"No se pudo bloquear: {str(e).strip('[]{}')}"}

    registrar(b, "alta", f"Bloqueo desde MCP: {motivo}")
    return {"ok": True, "bloqueado": f"{fecha_larga(f)}, {hi.strftime('%H:%M')}–"
                                     f"{hf.strftime('%H:%M')}",
            "motivo": motivo, "codigo": codigo,
            "deshacer": f"deshacer('{codigo}') mientras la fecha no haya pasado."}


@mcp.tool
@con_db
def agenda(fecha: str, dias: int = 1) -> dict:
    """
    Qué hay confirmado y qué está libre. Además muestra las pre-reservas sin
    confirmar que pisan cada horario — eso el calendario público NO lo muestra,
    porque solo bloquea con reservas ya confirmadas.
    """
    from app_fractalia.views import _get_slots_for_date
    try:
        f0 = parse_fecha(fecha)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    recurso = Resource.objects.filter(active=True).first()
    if not recurso:
        return {"ok": False, "error": "No hay ningún recurso activo configurado."}

    dias_out = []
    for i in range(max(1, min(dias, 31))):
        f = f0 + timedelta(days=i)
        slots = _get_slots_for_date(recurso, f)
        if slots is None:
            dias_out.append({"fecha": f.isoformat(), "fecha_legible": fecha_larga(f),
                             "sin_horario_configurado": True})
            continue
        pendientes = list(PendingBooking.objects.filter(status="PENDING", date=f))
        detalle = []
        for s in slots:
            h = parse_hora(s["time"])
            pisan = [p for p in pendientes if p.start_time <= h < p.end_time]
            ocupada = Booking.objects.filter(
                status="CONFIRMED",
                start_datetime__lt=dt_de(f, h) + timedelta(hours=1),
                end_datetime__gt=dt_de(f, h),
            ).first()
            detalle.append({
                "hora": s["time"],
                "estado": "ocupado" if not s["available"] else "libre",
                "reservado_por": cliente_str(ocupada) if ocupada else None,
                "pre_reservas_sin_confirmar": [cliente_str(p) for p in pisan] or None,
            })
        dias_out.append({"fecha": f.isoformat(), "fecha_legible": fecha_larga(f),
                         "slots": detalle})
    return {"ok": True, "recurso": recurso.name, "dias": dias_out}


# ───────────────────────────── informes ────────────────────────────────────

@mcp.tool
@con_db
def estado_del_dia() -> dict:
    """
    Foto del día con comparaciones contra ayer y la semana pasada.
    Los deltas son el material para narrar el informe, no solo el número suelto.
    """
    h = hoy()
    ayer, semana = h - timedelta(days=1), h - timedelta(days=7)

    def nuevas(d):
        return PendingBooking.objects.filter(created_at__date=d).count()

    def confirmadas_el(d):
        return PendingBooking.objects.filter(status="CONFIRMED", created_at__date=d).count()

    pendientes = list(PendingBooking.objects.filter(status="PENDING"))
    vencidas = [p for p in pendientes if _vencida(p)]
    hoy_reservas = Booking.objects.filter(status="CONFIRMED", start_datetime__date=h)

    return {
        "fecha": fecha_larga(h),
        "reservas_de_hoy": [
            {"cliente": cliente_str(b),
             "horario": f"{b.start_datetime.astimezone(ahora().tzinfo).strftime('%H:%M')}",
             "producto": b.product.name if b.product else "—"}
            for b in hoy_reservas.order_by("start_datetime")
        ],
        "cola": {
            "pendientes_total": len(pendientes),
            "vencidas": len(vencidas),
            "activas": len(pendientes) - len(vencidas),
            "mas_antigua_dias": max(
                ((h - p.created_at.astimezone(ahora().tzinfo).date()).days for p in pendientes),
                default=0),
        },
        "solicitudes_nuevas": {
            "hoy": nuevas(h), "ayer": nuevas(ayer),
            "mismo_dia_semana_pasada": nuevas(semana),
        },
        "confirmaciones": {"hoy": confirmadas_el(h), "ayer": confirmadas_el(ayer)},
        "alerta": (f"Hay {len(vencidas)} pre-reservas cuya fecha ya pasó y nunca se "
                   f"respondieron." if vencidas else None),
    }


@mcp.tool
@con_db
def tabla_pendientes(agrupar_por: str = "fecha") -> dict:
    """
    Tabla de lo que falta confirmar. `agrupar_por`: 'fecha', 'producto' o 'antiguedad'.
    """
    pendientes = list(PendingBooking.objects.select_related("product", "resource")
                      .filter(status="PENDING"))
    if not pendientes:
        return {"filas": [], "mensaje": "No queda nada por confirmar."}

    grupos = {}
    for p in pendientes:
        if agrupar_por == "producto":
            k = _nombre_producto(p)
        elif agrupar_por == "antiguedad":
            d = (hoy() - p.created_at.astimezone(ahora().tzinfo).date()).days
            k = ("más de 30 días" if d > 30 else "8 a 30 días" if d > 7
                 else "2 a 7 días" if d > 1 else "hoy o ayer")
        else:
            k = fecha_larga(p.date)
        grupos.setdefault(k, []).append(p)

    return {
        "agrupado_por": agrupar_por,
        "grupos": [
            {"grupo": k, "cantidad": len(v),
             "filas": [{"cliente": cliente_str(p), "producto": _nombre_producto(p),
                        "fecha": p.date.isoformat(),
                        "horario": f"{p.start_time.strftime('%H:%M')}–"
                                   f"{p.end_time.strftime('%H:%M')}",
                        "vencida": _vencida(p)}
                       for p in sorted(v, key=lambda x: (x.date, x.start_time))]}
            for k, v in sorted(grupos.items(), key=lambda kv: -len(kv[1]))
        ],
    }


# ───────────────────────── conflictos y análisis ───────────────────────────

@mcp.tool
@con_db
def conflictos() -> dict:
    """
    Pre-reservas activas que necesitan una decisión porque se pisan entre sí o
    con una reserva ya confirmada. Cada una viene con alternativas libres para
    poder ofrecer una salida.
    """
    activas = [p for p in PendingBooking.objects.select_related("product", "resource")
               .filter(status="PENDING") if not _vencida(p)]

    con_confirmada, entre_si, vistos = [], [], set()
    for p in activas:
        if _choca_con_confirmada(p):
            ocupa = Booking.objects.filter(
                status="CONFIRMED",
                start_datetime__lt=dt_de(p.date, p.end_time),
                end_datetime__gt=dt_de(p.date, p.start_time)).first()
            con_confirmada.append({
                "cliente": cliente_str(p), "codigo": p.reservation_code,
                "producto": _nombre_producto(p),
                "cuando": f"{fecha_larga(p.date)}, {p.start_time.strftime('%H:%M')}",
                "ocupado_por": cliente_str(ocupa) if ocupa else None,
                "alternativas": _libres_cerca(p),
            })
            continue
        rivales = _compiten(p)
        if rivales and p.pk not in vistos:
            grupo = [p] + rivales
            vistos.update(x.pk for x in grupo)
            entre_si.append({
                "cuando": f"{fecha_larga(p.date)}, {p.start_time.strftime('%H:%M')}–"
                          f"{p.end_time.strftime('%H:%M')}",
                "compiten": [
                    {"cliente": cliente_str(x), "codigo": x.reservation_code,
                     "producto": _nombre_producto(x),
                     "pidio_hace_dias": (hoy() - x.created_at.astimezone(
                         ahora().tzinfo).date()).days}
                    for x in sorted(grupo, key=lambda x: x.created_at)],
                "sugerencia": "El primero en pedir suele tener prioridad. "
                              "Al confirmar a uno, los demás quedan sin horario.",
                "alternativas": _libres_cerca(p),
            })

    total = len(con_confirmada) + sum(len(g["compiten"]) for g in entre_si)
    return {
        "hay_conflictos": total > 0,
        "total_afectadas": total,
        "chocan_con_reserva_confirmada": con_confirmada,
        "compiten_entre_si": entre_si,
    }


def _rango(desde: str, hasta: str):
    d = parse_fecha(desde) if desde else (hoy() - timedelta(days=180))
    h = parse_fecha(hasta) if hasta else hoy()
    return d, h


@mcp.tool
@con_db
def conversion(desde: str = "", hasta: str = "", agrupar_por: str = "mes") -> dict:
    """
    Embudo de conversión: visitas al calendario -> solicitudes -> respondidas ->
    confirmadas, con la tasa de cada paso.

    `agrupar_por`: mes, semana, producto, dia_semana u hora.
    Sin fechas, toma los últimos 180 días.
    """
    from app_analytics.models import PageView
    try:
        d, h = _rango(desde, hasta)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    tz = ahora().tzinfo
    pedidos = [p for p in PendingBooking.objects.select_related("product")
               if d <= p.created_at.astimezone(tz).date() <= h]

    def clave(p):
        f = p.created_at.astimezone(tz).date()
        if agrupar_por == "semana":
            return (f - timedelta(days=f.weekday())).isoformat()
        if agrupar_por == "producto":
            return _nombre_producto(p)
        if agrupar_por == "dia_semana":
            return ["lunes", "martes", "miércoles", "jueves", "viernes",
                    "sábado", "domingo"][p.date.weekday()]
        if agrupar_por == "hora":
            return p.start_time.strftime("%H:00")
        return f.strftime("%Y-%m")

    grupos = {}
    for p in pedidos:
        g = grupos.setdefault(clave(p), {"solicitudes": 0, "confirmadas": 0,
                                         "respondidas": 0, "pendientes": 0})
        g["solicitudes"] += 1
        g[{"CONFIRMED": "confirmadas", "RESPONDED": "respondidas",
           "PENDING": "pendientes"}.get(p.status, "respondidas")] += 1

    # Visitantes únicos al calendario, solo tiene sentido en cortes temporales
    if agrupar_por in ("mes", "semana"):
        for v in PageView.objects.filter(page="fractalia_calendar"):
            f = v.timestamp.astimezone(tz).date()
            if not (d <= f <= h):
                continue
            k = (f.strftime("%Y-%m") if agrupar_por == "mes"
                 else (f - timedelta(days=f.weekday())).isoformat())
            grupos.setdefault(k, {"solicitudes": 0, "confirmadas": 0,
                                  "respondidas": 0, "pendientes": 0})
            grupos[k].setdefault("_ips", set()).add(v.ip_hash)

    filas = []
    for k in sorted(grupos):
        g = grupos[k]
        visit = len(g.pop("_ips", ()) or ())
        fila = {"grupo": k, **g}
        if visit:
            fila["visitantes_calendario"] = visit
            fila["tasa_visita_a_solicitud"] = f"{g['solicitudes'] / visit * 100:.1f}%"
        if g["solicitudes"]:
            fila["tasa_solicitud_a_confirmada"] = \
                f"{g['confirmadas'] / g['solicitudes'] * 100:.1f}%"
        filas.append(fila)

    tot = sum(g["solicitudes"] for g in grupos.values())
    conf = sum(g["confirmadas"] for g in grupos.values())
    return {
        "ok": True, "desde": d.isoformat(), "hasta": h.isoformat(),
        "agrupado_por": agrupar_por,
        "total": {"solicitudes": tot, "confirmadas": conf,
                  "tasa": f"{conf / tot * 100:.1f}%" if tot else "—"},
        "filas": filas,
    }


@mcp.tool
@con_db
def trafico(desde: str = "", hasta: str = "", agrupar_por: str = "mes") -> dict:
    """
    Visitas al sitio. `agrupar_por`: mes, semana, pagina u origen.
    Sirve para separar un problema de demanda de uno de conversión.
    """
    from app_analytics.models import PageView
    try:
        d, h = _rango(desde, hasta)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    tz = ahora().tzinfo
    grupos = {}
    for v in PageView.objects.all():
        f = v.timestamp.astimezone(tz).date()
        if not (d <= f <= h):
            continue
        if agrupar_por == "pagina":
            k = v.page
        elif agrupar_por == "origen":
            k = v.referrer or "(directo)"
        elif agrupar_por == "semana":
            k = (f - timedelta(days=f.weekday())).isoformat()
        else:
            k = f.strftime("%Y-%m")
        g = grupos.setdefault(k, {"visitas": 0, "_ips": set()})
        g["visitas"] += 1
        g["_ips"].add(v.ip_hash)

    filas = [{"grupo": k, "visitas": g["visitas"], "visitantes_unicos": len(g["_ips"])}
             for k, g in grupos.items()]
    orden = (lambda x: x["grupo"]) if agrupar_por in ("mes", "semana") \
        else (lambda x: -x["visitas"])
    return {"ok": True, "desde": d.isoformat(), "hasta": h.isoformat(),
            "agrupado_por": agrupar_por, "filas": sorted(filas, key=orden)}


@mcp.tool
@con_db
def demanda(desde: str = "", hasta: str = "") -> dict:
    """
    Qué días y horas piden los clientes, cruzado con el horario configurado.
    Sirve para detectar demanda que hoy no se puede atender.
    """
    from app_fractalia.models import WeeklyAvailability
    try:
        d, h = _rango(desde, hasta)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    tz = ahora().tzinfo
    pedidos = [p for p in PendingBooking.objects.all()
               if d <= p.created_at.astimezone(tz).date() <= h]

    dias_nombre = ["lunes", "martes", "miércoles", "jueves", "viernes",
                   "sábado", "domingo"]
    config = {a.weekday: (a.start_time.strftime("%H:%M"), a.end_time.strftime("%H:%M"))
              for a in WeeklyAvailability.objects.all()}

    por_dia, por_hora = {}, {}
    for p in pedidos:
        por_dia[p.date.weekday()] = por_dia.get(p.date.weekday(), 0) + 1
        k = p.start_time.strftime("%H:00")
        por_hora[k] = por_hora.get(k, 0) + 1

    return {
        "ok": True, "desde": d.isoformat(), "hasta": h.isoformat(),
        "total_solicitudes": len(pedidos),
        "por_dia": [
            {"dia": dias_nombre[i], "solicitudes": por_dia.get(i, 0),
             "horario_configurado": (f"{config[i][0]}–{config[i][1]}"
                                     if i in config else "cerrado")}
            for i in range(7)],
        "por_hora": [{"hora": k, "solicitudes": por_hora[k]}
                     for k in sorted(por_hora)],
        "nota": "Solo se puede pedir dentro del horario configurado, así que la "
                "ausencia de pedidos fuera de él no prueba falta de demanda.",
    }


@mcp.tool
@con_db
def clientes(minimo_solicitudes: int = 2) -> dict:
    """Clientes que pidieron más de una vez, con el resultado de cada pedido."""
    porte = {}
    for p in PendingBooking.objects.exclude(client_phone="").order_by("created_at"):
        porte.setdefault(p.client_phone, []).append(p)

    repet = [{"cliente": cliente_str(v[-1]), "solicitudes": len(v),
              "estados": [x.get_status_display() for x in v],
              "primera": v[0].created_at.astimezone(ahora().tzinfo).date().isoformat(),
              "ultima": v[-1].created_at.astimezone(ahora().tzinfo).date().isoformat()}
             for v in porte.values() if len(v) >= max(1, minimo_solicitudes)]

    return {"ok": True, "telefonos_unicos": len(porte),
            "clientes_con_varias_solicitudes": len(repet),
            "detalle": sorted(repet, key=lambda x: -x["solicitudes"])}


# ─────────────────────────── datos crudos ──────────────────────────────────
#
# Para análisis que no anticipamos. La consulta libre es potente y por eso va
# con barandas: transacción de solo lectura (Postgres rechaza cualquier
# escritura aunque se cuele la palabra), timeout, límite de filas, y tablas de
# credenciales/sesiones fuera de alcance.

_TABLAS = {
    "pre_reservas": "app_fractalia_pendingbooking",
    "reservas": "app_fractalia_booking",
    "productos": "app_fractalia_product",
    "paquetes": "app_fractalia_fractaboxpackage",
    "recursos": "app_fractalia_resource",
    "disponibilidad": "app_fractalia_weeklyavailability",
    "visitas": "app_analytics_pageview",
    "visitas_mensuales": "app_analytics_pageviewmonthly",
    "links": "app_links_link",
    "fotos": "app_portfolio_photo",
    "acciones_admin": "django_admin_log",
}

# Credenciales y sesiones: nunca, por más que la consulta sea de solo lectura.
# Ojo: esto es una lista negra sobre texto, o sea que vale lo que valga la
# imaginación de quien la escribió. La defensa que de verdad sostiene el
# invariante es el rol de Postgres (ver _conexion_lectura): si la tabla no está
# concedida al rol, no se lee aunque el filtro falle.
_PROHIBIDAS = ("auth_user", "django_session", "auth_permission",
               "auth_group", "pg_", "information_schema")

_ESCRITURA = ("insert", "update", "delete", "drop", "alter", "create", "truncate",
              "grant", "revoke", "copy", "vacuum", "reindex", "call", "do ")

# consulta_sql permite extraer datos personales en volumen, así que viene
# apagado y se habilita a propósito con MCP_SQL_LIBRE=1.
_SQL_LIBRE = os.environ.get("MCP_SQL_LIBRE", "0") == "1"


def _conexion_lectura():
    """
    Conexión con el rol restringido `mcp_lectura`, que solo tiene SELECT sobre
    las tablas de negocio. Es una conexión aparte de la de Django a propósito:
    la de Django usa el rol dueño de la base y podría leer y escribir todo.
    """
    import psycopg

    usuario = os.environ.get("MCP_SQL_USER", "")
    clave = os.environ.get("MCP_SQL_PASSWORD", "")
    if not usuario or not clave:
        raise RuntimeError(
            "Faltan MCP_SQL_USER / MCP_SQL_PASSWORD: no hay rol restringido "
            "configurado. Sin eso la consulta libre no se habilita."
        )
    return psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "db"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "ab_reservas"),
        user=usuario,
        password=clave,
        connect_timeout=5,
    )


@mcp.tool
@con_db
def esquema() -> dict:
    """
    Tablas y columnas disponibles para consulta_sql(), con sus tipos.
    Llamalo antes de escribir una consulta para no adivinar nombres.
    """
    from django.apps import apps as django_apps
    salida = {}
    inverso = {v: k for k, v in _TABLAS.items()}
    for modelo in django_apps.get_models():
        tabla = modelo._meta.db_table
        if tabla not in inverso:
            continue
        salida[inverso[tabla]] = {
            "tabla_sql": tabla,
            "filas": modelo.objects.count(),
            "columnas": [f"{f.column} ({f.get_internal_type()})"
                         for f in modelo._meta.fields],
        }
    return {"tablas": salida,
            "nota": "Fechas guardadas en UTC; convertí con "
                    "AT TIME ZONE 'America/Asuncion' para agrupar por día local."}


@mcp.tool
@con_db
def datos(tabla: str, desde: str = "", hasta: str = "", limite: int = 500) -> dict:
    """
    Filas crudas de una tabla, sin agregación, para analizar a gusto.
    `tabla`: pre_reservas, reservas, productos, visitas, etc. — ver esquema().
    """
    from django.apps import apps as django_apps
    if tabla not in _TABLAS:
        return {"ok": False, "error": f"Tabla desconocida '{tabla}'.",
                "disponibles": sorted(_TABLAS)}

    modelo = next((m for m in django_apps.get_models()
                   if m._meta.db_table == _TABLAS[tabla]), None)
    if not modelo:
        return {"ok": False, "error": f"No pude resolver el modelo de '{tabla}'."}

    qs = modelo.objects.all()
    campo_fecha = next((c for c in ("created_at", "timestamp", "date", "start_datetime")
                        if c in {f.name for f in modelo._meta.fields}), None)
    if campo_fecha and (desde or hasta):
        try:
            d, h = _rango(desde, hasta)
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        qs = qs.filter(**{f"{campo_fecha}__gte": d, f"{campo_fecha}__lte": h + timedelta(days=1)})

    total = qs.count()
    filas = list(qs.values()[:max(1, min(limite, 5000))])
    return {"ok": True, "tabla": tabla, "total_en_base": total,
            "devueltas": len(filas),
            "truncado": total > len(filas),
            "filtrado_por": campo_fecha if (desde or hasta) else None,
            "filas": filas}


@mcp.tool
@con_db
def consulta_sql(sql: str, limite: int = 500) -> dict:
    """
    Consulta SQL libre de SOLO LECTURA sobre la base. Para cualquier análisis que
    los otros tools no cubran: joins, agregaciones, ventanas, lo que necesites.

    Solo SELECT o WITH, con un rol de Postgres que únicamente tiene permiso de
    lectura sobre las tablas de negocio. Las de usuarios y sesiones están fuera
    de alcance. Usá esquema() para ver nombres de tablas y columnas.

    Puede devolver datos personales de clientes en volumen, así que viene
    deshabilitado salvo que se active a propósito.
    """
    import logging
    import re as _re

    log = logging.getLogger("mcp.sql")

    if not _SQL_LIBRE:
        return {"ok": False,
                "error": "La consulta SQL libre está deshabilitada en este entorno.",
                "motivo": "Permite extraer datos personales de clientes en volumen.",
                "alternativa": "Usá conversion(), trafico(), demanda(), clientes() "
                               "o datos(tabla), que cubren los análisis habituales.",
                "habilitar": "Se activa con MCP_SQL_LIBRE=1 en el entorno del servicio."}

    limpio = _re.sub(r"--[^\n]*|/\*.*?\*/", " ", sql or "", flags=_re.S).strip().rstrip(";")
    if not limpio:
        return {"ok": False, "error": "Consulta vacía."}
    bajo = limpio.lower()

    if ";" in limpio:
        return {"ok": False, "error": "Una sola sentencia por consulta."}
    if not bajo.startswith(("select", "with")):
        return {"ok": False, "error": "Solo se permiten consultas SELECT o WITH."}
    encontrada = next((p for p in _ESCRITURA if _re.search(rf"\b{p.strip()}\b", bajo)), None)
    if encontrada:
        return {"ok": False, "error": f"La consulta contiene '{encontrada.strip()}'. "
                                      f"Solo lectura."}
    tabla_prohibida = next((t for t in _PROHIBIDAS if t in bajo), None)
    if tabla_prohibida:
        return {"ok": False,
                "error": f"'{tabla_prohibida}' está fuera de alcance (credenciales "
                         f"o sesiones). Usá esquema() para ver qué sí podés consultar."}

    tope = max(1, min(limite, 5000))
    # Queda rastro de toda consulta ejecutada, antes de ejecutarla.
    log.warning("[consulta_sql] %s", " ".join(limpio.split())[:500])
    try:
        # Dos defensas independientes: el rol solo tiene SELECT sobre las tablas
        # de negocio, y la transacción READ ONLY impide cualquier escritura.
        with _conexion_lectura() as conexion:
            with conexion.cursor() as cur:
                cur.execute("SET TRANSACTION READ ONLY")
                cur.execute("SET statement_timeout = '15s'")
                cur.execute(f"SELECT * FROM ({limpio}) AS _q LIMIT {tope + 1}")
                columnas = [c.name for c in cur.description]
                filas = cur.fetchall()
            conexion.rollback()
    except RuntimeError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        log.warning("[consulta_sql] falló: %s", str(e)[:200])
        return {"ok": False, "error": f"Error al ejecutar: {str(e).strip()[:400]}"}

    truncado = len(filas) > tope
    filas = filas[:tope]
    return {"ok": True, "columnas": columnas, "filas_devueltas": len(filas),
            "truncado": truncado,
            "filas": [dict(zip(columnas, [str(v) if hasattr(v, "isoformat") else v
                                          for v in f])) for f in filas]}


# ─────────────────── relevamiento de lo que falta ──────────────────────────

@mcp.tool
@con_db
def registrar_necesidad(descripcion: str, categoria: str = "falta_tool",
                        contexto: str = "", tool_relacionada: str = "") -> dict:
    """
    Anota algo que el encargado quiso hacer y el MCP no permitió.

    Usalo cada vez que tengas que responder "eso no lo puedo hacer", o cuando
    para resolver algo haya que salir a otra herramienta. Escribí la necesidad
    en palabras del encargado, no en términos técnicos.

    `categoria`: falta_tool, falta_dato, friccion, error, otro.
    Si la misma necesidad ya estaba registrada, suma una aparición en vez de
    duplicarla.
    """
    from app_mcp.models import Necesidad
    from .bootstrap import usuario_actual

    texto = (descripcion or "").strip()
    if len(texto) < 20 or len(texto.split()) < 4:
        return {"ok": False,
                "error": "Describí la necesidad con más detalle: lo que se lee "
                         "dentro de un año tiene que alcanzar para entender qué "
                         "hacía falta.",
                "ejemplo": "Poder ver si el cliente ya transfirió antes de "
                           "confirmarle el turno."}

    validas = [c for c, _ in Necesidad.CATEGORIAS]
    if categoria not in validas:
        return {"ok": False, "error": f"Categoría inválida.", "opciones": validas}

    obj, nueva = Necesidad.registrar(
        descripcion=texto, categoria=categoria, contexto=contexto,
        tool_relacionada=tool_relacionada, usuario=usuario_actual(),
    )
    return {
        "ok": True,
        "registrada": obj.descripcion[:100],
        "es_nueva": nueva,
        "veces_que_apareció": obj.veces,
        "categoria": obj.get_categoria_display(),
        "mensaje": ("Anotado." if nueva else
                    f"Ya estaba registrada; van {obj.veces} veces. "
                    f"Vale mencionárselo: es algo que le pasa seguido."),
    }


@mcp.tool
@con_db
def necesidades(estado: str = "", limite: int = 30) -> dict:
    """
    Lo que el MCP todavía no cubre, ordenado por cuántas veces apareció.
    `estado`: nueva, en_analisis, planificada, implementada, descartada.
    """
    from app_mcp.models import Necesidad

    qs = Necesidad.objects.all()
    if estado:
        validos = [e for e, _ in Necesidad.ESTADOS]
        if estado not in validos:
            return {"ok": False, "error": "Estado inválido.", "opciones": validos}
        qs = qs.filter(estado=estado)

    items = list(qs[:max(1, min(limite, 100))])
    return {
        "ok": True,
        "total": qs.count(),
        "items": [{
            "necesidad": n.descripcion,
            "veces": n.veces,
            "tipo": n.get_categoria_display(),
            "estado": n.get_estado_display(),
            "herramienta": n.tool_relacionada or None,
            "desde": n.primera_vez.astimezone(ahora().tzinfo).date().isoformat(),
        } for n in items],
        "nota": "Se administran desde el admin de Django, en 'MCP — uso y "
                "necesidades'.",
    }


@mcp.tool
@con_db
def uso(dias: int = 30) -> dict:
    """
    Qué herramientas se usan de verdad y cuáles fallan. Sirve para saber qué
    conviene pulir y qué no está aportando nada.
    """
    from django.db.models import Avg, Count, Q

    from app_mcp.models import UsoTool

    desde = ahora() - timedelta(days=max(1, min(dias, 365)))
    qs = UsoTool.objects.filter(momento__gte=desde)
    resumen = (qs.values("tool")
               .annotate(llamadas=Count("id"),
                         fallas=Count("id", filter=Q(exito=False)),
                         ms_promedio=Avg("duracion_ms"))
               .order_by("-llamadas"))

    filas = [{
        "herramienta": r["tool"],
        "llamadas": r["llamadas"],
        "fallas": r["fallas"],
        "ms_promedio": int(r["ms_promedio"]) if r["ms_promedio"] else None,
    } for r in resumen]

    usadas = {f["herramienta"] for f in filas}
    todas = {t.name for t in mcp._tool_manager._tools.values()} \
        if hasattr(mcp, "_tool_manager") else set()

    return {
        "ok": True,
        "desde": desde.date().isoformat(),
        "total_llamadas": sum(f["llamadas"] for f in filas),
        "por_herramienta": filas,
        "nunca_usadas": sorted(todas - usadas) or None,
    }


# ──────────────────────────── retroceso ────────────────────────────────────

@mcp.tool
@con_db
def deshacer(codigo: str) -> dict:
    """
    Revierte la última acción sobre una reserva:
      confirmada -> vuelve a pendiente y se libera el horario
      rechazada  -> vuelve a pendiente
      creada de cero / bloqueo -> se elimina

    No se puede deshacer si la fecha ya pasó.
    """
    pb = _buscar(codigo)
    booking = _booking_de(pb) if pb else Booking.objects.filter(
        reservation_code__iexact=(codigo or "").strip()).first()

    if not pb and not booking:
        return _no_encontrada(codigo)

    f = pb.date if pb else booking.start_datetime.astimezone(ahora().tzinfo).date()
    if f < hoy():
        return {"ok": False,
                "error": f"No se puede deshacer: la fecha ({fecha_larga(f)}) ya pasó."}

    # Bloqueo o alta directa sin pre-reserva previa
    if booking and (not pb or pb.notes.startswith(("Bloqueo desde MCP", "Alta directa"))
                    or "[BLOQUEO]" in (booking.client_name or "")):
        etiqueta = cliente_str(booking)
        booking.delete()
        if pb:
            pb.delete()
        return {"ok": True, "deshecho": etiqueta,
                "resultado": "Se eliminó la reserva y el horario quedó libre."}

    if pb.status == "CONFIRMED":
        if booking:
            booking.delete()
        pb.status = "PENDING"
        pb.save()
        registrar(pb, "cambio", "Confirmación deshecha desde MCP")
        return {"ok": True, "deshecho": cliente_str(pb),
                "resultado": "Volvió a Pendiente y el horario quedó libre de nuevo."}

    if pb.status == "RESPONDED":
        pb.status = "PENDING"
        pb.save()
        registrar(pb, "cambio", "Rechazo deshecho desde MCP")
        return {"ok": True, "deshecho": cliente_str(pb),
                "resultado": "Volvió a Pendiente."}

    return {"ok": False, "error": f"{cliente_str(pb)} está en estado "
                                  f"'{pb.get_status_display()}'; no hay nada que deshacer."}


def _plantillas(pb) -> dict:
    """Mensajes armados con los datos reales de la pre-reserva."""
    nombre = (pb.client_name or "").split(" ")[0] or "Hola"
    prod = _nombre_producto(pb)
    cuando = (f"el {fecha_larga(pb.date)} de {pb.start_time.strftime('%H:%M')} "
              f"a {pb.end_time.strftime('%H:%M')}")
    return {
        "confirmacion": _mensaje_confirmacion(pb),
        "ocupado": (f"Hola {nombre}, gracias por escribirnos. El horario que pediste "
                    f"({cuando}) ya quedó tomado. ¿Te sirve alguno de estos otros? "
                    f"Avisame y te lo reservo."),
        "seguimiento": (f"Hola {nombre}, te escribo por tu pedido de {prod} {cuando}. "
                        f"¿Seguís interesado/a? Si querés lo confirmamos."),
        "pedir_datos": (f"Hola {nombre}, para confirmar tu {prod} {cuando} me falta un "
                        f"dato. ¿Me lo podés pasar así te lo dejo reservado?"),
        "recordatorio": (f"Hola {nombre}, te recuerdo tu reserva de {prod} {cuando}. "
                         f"Código: {pb.reservation_code}. ¡Nos vemos!"),
        "cancelacion": (f"Hola {nombre}, te confirmo que cancelamos tu reserva de {prod} "
                        f"{cuando}. Cualquier cosa escribinos y la reprogramamos."),
    }


@mcp.tool
@con_db
def link_mensaje(codigo: str, plantilla: str = "", mensaje: str = "") -> dict:
    """
    Arma un link de WhatsApp hacia el cliente con el mensaje ya escrito, para que
    solo haya que tocarlo y enviar.

    Pasá `mensaje` con tu propio texto, o `plantilla` con uno de los prearmados:
    confirmacion, ocupado, seguimiento, pedir_datos, recordatorio, cancelacion.
    Sin ninguno de los dos, devuelve las plantillas disponibles para elegir.
    """
    pb = _buscar(codigo)
    if not pb:
        return _no_encontrada(codigo)
    if not pb.client_phone:
        return {"ok": False,
                "error": f"{cliente_str(pb)} no tiene teléfono registrado."}

    disponibles = _plantillas(pb)

    if mensaje.strip():
        texto = mensaje.strip()
    elif plantilla.strip():
        clave = plantilla.strip().lower()
        if clave not in disponibles:
            return {"ok": False,
                    "error": f"No existe la plantilla '{plantilla}'.",
                    "disponibles": list(disponibles)}
        texto = disponibles[clave]
    else:
        return {
            "ok": True,
            "para": cliente_str(pb),
            "elegir_una": {k: v for k, v in disponibles.items()},
            "nota": "Llamá de nuevo con plantilla='...' o con mensaje='tu texto'.",
        }

    return {"ok": True, "para": cliente_str(pb),
            "llamar": f"tel:+{telefono_internacional(pb.client_phone)}",
            **(whatsapp(pb.client_phone, texto) or {})}


@mcp.tool
@con_db
def cancelar(codigo: str, motivo: str = "") -> dict:
    """
    Cancela una reserva YA confirmada y libera el horario.

    Distinto de deshacer(): deshacer revierte un error tuyo y devuelve la
    pre-reserva a pendiente. Cancelar es una baja real —el cliente avisó que no
    viene— y deja la pre-reserva como cancelada, no pendiente.
    """
    pb = _buscar(codigo)
    booking = _booking_de(pb) if pb else Booking.objects.filter(
        reservation_code__iexact=(codigo or "").strip()).first()

    if not booking:
        if pb:
            return {"ok": False, "error": f"{cliente_str(pb)} no tiene una reserva "
                                          f"confirmada para cancelar (está en "
                                          f"'{pb.get_status_display()}')."}
        return _no_encontrada(codigo)
    if booking.status == "CANCELLED":
        return {"ok": False, "error": f"{cliente_str(booking)} ya estaba cancelada."}

    etiqueta = cliente_str(booking)
    cuando = (f"{fecha_larga(booking.start_datetime.astimezone(ahora().tzinfo).date())}, "
              f"{booking.start_datetime.astimezone(ahora().tzinfo).strftime('%H:%M')}")
    booking.status = "CANCELLED"
    if motivo:
        booking.notes = f"{booking.notes}\n[MCP] Cancelada: {motivo}".strip()
    booking.save()

    if pb:
        pb.status = "CANCELLED"
        if motivo:
            pb.notes = f"{pb.notes}\n[MCP] Cancelada: {motivo}".strip()
        pb.save()

    registrar(booking, "cambio", f"Cancelada desde MCP. Motivo: {motivo or 'sin especificar'}")
    return {"ok": True, "cancelada": etiqueta, "cuando": cuando,
            "motivo": motivo or "sin especificar",
            "calendario": "El horario volvió a quedar libre."}


@mcp.tool
@con_db
def historial(limite: int = 20) -> dict:
    """Últimas acciones registradas sobre reservas, incluidas las hechas por el MCP."""
    from django.contrib.admin.models import LogEntry
    entradas = (LogEntry.objects.select_related("user", "content_type")
                .filter(content_type__app_label="app_fractalia")
                .order_by("-action_time")[:max(1, min(limite, 100))])
    return {"acciones": [
        {"cuando": e.action_time.astimezone(ahora().tzinfo).strftime("%Y-%m-%d %H:%M"),
         "quien": e.user.username if e.user else "—",
         "objeto": e.object_repr,
         "detalle": e.change_message or e.get_action_flag_display()}
        for e in entradas
    ]}
