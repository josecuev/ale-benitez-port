from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpRequest, HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods, require_GET
from django.views.decorators.csrf import ensure_csrf_cookie
from django.conf import settings
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_date
from datetime import datetime, time as dtime

from .models import Reserva, ServicioAdicional, HorarioDisponible


# ============================================================================
# Vista de verificación de email
# ============================================================================
def verificar_reserva(request: HttpRequest, token) -> HttpResponse:
    """
    Verifica el email de una reserva mediante el token enviado por correo.
    """
    reserva = get_object_or_404(Reserva, token_verificacion=token)
    requiere = getattr(settings, "RESERVAS_REQUIRE_EMAIL_VERIFICATION", True)
    
    contexto = {
        "reserva": reserva, 
        "requiere_verificacion": requiere, 
        "estado": "desconocido"
    }

    # Si no se requiere verificación
    if not requiere:
        contexto["estado"] = "no_requerida"
        return render(request, "app_reservas/verificacion_resultado.html", contexto)

    # Si ya está verificada
    if reserva.email_verificado_en or reserva.estado != "PENDIENTE_VERIFICACION":
        contexto["estado"] = "ya_verificada"
        return render(request, "app_reservas/verificacion_resultado.html", contexto)

    # Verificar email
    exito = reserva.verificar_email()
    contexto["estado"] = "ok" if exito else "error"
    
    return render(request, "app_reservas/verificacion_resultado.html", contexto)


# ============================================================================
# API de servicios (autocomplete)
# ============================================================================
@require_http_methods(["GET"])
def servicios_api(request: HttpRequest) -> JsonResponse:
    """
    API para autocomplete de servicios adicionales.
    Parámetros:
        - q: texto de búsqueda (opcional)
    
    Retorna: {results: [{id, nombre, precio}]}
    """
    q = (request.GET.get("q") or "").strip()
    
    # Filtrar servicios activos
    qs = ServicioAdicional.objects.filter(activo=True)
    
    # Búsqueda por texto
    if q:
        qs = qs.filter(nombre__icontains=q)
    
    # Ordenar y limitar resultados
    qs = qs.order_by("nombre")[:20]
    
    # Serializar
    results = [
        {
            "id": s.id, 
            "nombre": s.nombre, 
            "precio": float(s.precio)
        } 
        for s in qs
    ]
    
    return JsonResponse({"results": results})


# ============================================================================
# Vista principal: nueva reserva
# ============================================================================
@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def nueva_reserva(request: HttpRequest) -> HttpResponse:
    """
    Single Page Application para crear reservas.
    
    GET: Renderiza el formulario
    POST (JSON): Crea la reserva y retorna resultado en JSON
    """
    # GET: Mostrar formulario
    if request.method == "GET":
        return render(request, "app_reservas/nueva_reserva.html", {
            "requiere_verificacion": getattr(settings, "RESERVAS_REQUIRE_EMAIL_VERIFICATION", True),
        })

    # POST: Procesar reserva
    # Validar content-type
    if request.content_type != "application/json":
        return HttpResponseBadRequest("Content-Type debe ser application/json")

    # Parsear JSON
    try:
        import json
        payload = json.loads(request.body.decode("utf-8"))
    except Exception as e:
        return JsonResponse({
            "ok": False, 
            "error": f"JSON inválido: {str(e)}"
        }, status=400)

    # Extraer campos
    nombre = (payload.get("nombre_cliente") or "").strip()
    email = (payload.get("email_cliente") or "").strip()
    telefono = (payload.get("telefono_cliente") or "").strip()
    cedula = (payload.get("cedula") or "").strip()
    ruc = (payload.get("ruc") or "").strip()
    fecha_str = (payload.get("fecha") or "").strip()
    hi_str = (payload.get("hora_inicio") or "").strip()
    hf_str = (payload.get("hora_fin") or "").strip()
    servicios_ids = payload.get("servicios_ids") or []
    notas = (payload.get("notas_cliente") or "").strip()

    # Validar campos requeridos
    if not all([nombre, email, telefono, cedula, fecha_str, hi_str, hf_str]):
        return JsonResponse({
            "ok": False, 
            "error": "Faltan campos requeridos. Por favor completá todos los campos obligatorios."
        }, status=400)

    # Parsear fecha
    fecha = parse_date(fecha_str)
    if not fecha:
        return JsonResponse({
            "ok": False, 
            "error": "Formato de fecha inválido. Usa YYYY-MM-DD."
        }, status=400)

    # Parsear horas
    try:
        hi_parts = [int(x) for x in hi_str.split(":")]
        hf_parts = [int(x) for x in hf_str.split(":")]
        hora_inicio = dtime(hi_parts[0], hi_parts[1])
        hora_fin = dtime(hf_parts[0], hf_parts[1])
    except Exception:
        return JsonResponse({
            "ok": False, 
            "error": "Formato de hora inválido. Usa HH:MM."
        }, status=400)

    # Crear reserva
    try:
        with transaction.atomic():
            # ✅ Determinar estado inicial según configuración
            requiere_verificacion = getattr(settings, "RESERVAS_REQUIRE_EMAIL_VERIFICATION", True)
            estado_inicial = "PENDIENTE_VERIFICACION" if requiere_verificacion else "PENDIENTE_CONFIRMACION"
            
            # Crear instancia
            reserva = Reserva(
                nombre_cliente=nombre,
                email_cliente=email,
                telefono_cliente=telefono,
                cedula=cedula,
                ruc=ruc,
                fecha=fecha,
                hora_inicio=hora_inicio,
                hora_fin=hora_fin,
                notas_cliente=notas,
                estado=estado_inicial,  # ✅ Estado correcto desde el inicio
            )
            
            # Validar y guardar
            reserva.full_clean()
            reserva.save()

            # Agregar servicios adicionales
            if servicios_ids:
                servicios = ServicioAdicional.objects.filter(
                    id__in=servicios_ids, 
                    activo=True
                )
                if servicios.exists():
                    reserva.servicios_adicionales.add(*servicios)

            # Enviar email de verificación si corresponde
            if requiere_verificacion:
                try:
                    reserva.enviar_email_verificacion(request=request)
                    siguiente = "verificar_email"
                except Exception as e:
                    # No fallar si el email falla - la reserva ya está creada
                    print(f"Error al enviar email: {e}")
                    siguiente = "verificar_email_pendiente"
            else:
                siguiente = "pendiente_confirmacion"

    except ValidationError as e:
        # Errores de validación del modelo
        errores = []
        if hasattr(e, 'message_dict'):
            for field, messages in e.message_dict.items():
                errores.extend(messages)
        else:
            errores = [str(e)]
        
        return JsonResponse({
            "ok": False, 
            "error": "; ".join(errores)
        }, status=400)
    
    except Exception as e:
        # Otros errores
        return JsonResponse({
            "ok": False, 
            "error": f"Error al crear la reserva: {str(e)}"
        }, status=500)

    # Respuesta exitosa
    total = float(reserva.total())
    
    return JsonResponse({
        "ok": True,
        "siguiente": siguiente,
        "resumen": {
            "codigo": str(reserva.codigo),
            "nombre_cliente": reserva.nombre_cliente,
            "email_cliente": reserva.email_cliente,
            "telefono_cliente": reserva.telefono_cliente,
            "cedula": reserva.cedula,
            "fecha": str(reserva.fecha),
            "hora_inicio": reserva.hora_inicio.strftime("%H:%M"),
            "hora_fin": reserva.hora_fin.strftime("%H:%M"),
            "servicios": [
                {
                    "id": s.id, 
                    "nombre": s.nombre, 
                    "precio": float(s.precio)
                } 
                for s in reserva.servicios_adicionales.all()
            ],
            "total_servicios": total,
            "estado": reserva.get_estado_display(),
        }
    })


# ============================================================================
# API de disponibilidad
# ============================================================================

def _overlap(a_start, a_end, b_start, b_end):
    """Determina si dos rangos de tiempo se solapan"""
    return (a_start < b_end) and (a_end > b_start)


def _substraer_intervalos(rango, ocupados):
    """
    Resta intervalos ocupados de un rango disponible.
    
    Args:
        rango: tupla (inicio, fin) del horario disponible
        ocupados: lista de tuplas [(inicio, fin), ...] de horarios ocupados
    
    Returns:
        lista de tuplas [(inicio, fin), ...] de rangos libres
    """
    libres = [rango]
    
    for (oi, of) in sorted(ocupados):
        nuevos = []
        for (li, lf) in libres:
            # Si no se solapan, mantener el rango libre
            if of <= li or oi >= lf:
                nuevos.append((li, lf))
            else:
                # Si se solapan, partir el rango
                if oi > li:
                    nuevos.append((li, oi))
                if of < lf:
                    nuevos.append((of, lf))
        
        # Filtrar rangos vacíos
        libres = [(i, f) for (i, f) in nuevos if i < f]
    
    return libres


@require_GET
def disponibilidad_api(request):
    """
    API para consultar disponibilidad de horarios en una fecha.
    
    Parámetros:
        - fecha: string en formato YYYY-MM-DD
    
    Retorna:
        {
            ok: bool,
            fecha: string,
            discreto: [{inicio, fin}, ...],
            continuo: [{inicio, fin, min}, ...]
        }
    """
    # Obtener y validar fecha
    fecha_str = request.GET.get("fecha")
    if not fecha_str:
        return JsonResponse({
            "ok": False, 
            "error": "Parámetro 'fecha' requerido (formato: YYYY-MM-DD)"
        }, status=400)
    
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({
            "ok": False, 
            "error": "Formato de fecha inválido. Usa YYYY-MM-DD."
        }, status=400)

    # Obtener día de la semana (0=lunes, 6=domingo)
    dia = fecha.weekday()
    
    # Obtener horarios disponibles para ese día
    horarios = HorarioDisponible.objects.filter(
        dia_semana=dia, 
        activo=True
    ).order_by("hora_inicio")
    
    # Obtener reservas CONFIRMADAS para esa fecha
    confirmadas = list(
        Reserva.objects.filter(
            fecha=fecha, 
            estado="CONFIRMADA"
        ).values_list("hora_inicio", "hora_fin")
    )

    # Preparar respuesta
    resp = {
        "ok": True, 
        "fecha": fecha_str, 
        "discreto": [], 
        "continuo": []
    }

    # Procesar cada horario disponible
    for h in horarios:
        if h.tipo == "DISCRETO":
            # Slots discretos: mostrar solo si NO están ocupados
            ocupado = any(
                _overlap(h.hora_inicio, h.hora_fin, c[0], c[1]) 
                for c in confirmadas
            )
            
            if not ocupado:
                resp["discreto"].append({
                    "inicio": h.hora_inicio.strftime("%H:%M"),
                    "fin": h.hora_fin.strftime("%H:%M"),
                })
        
        else:  # CONTINUO
            # Slots continuos: restar rangos ocupados
            rango = (h.hora_inicio, h.hora_fin)
            libres = _substraer_intervalos(rango, confirmadas)
            
            # Función auxiliar para calcular minutos entre dos tiempos
            def _mins(t1, t2):
                d1 = datetime.combine(fecha, t1)
                d2 = datetime.combine(fecha, t2)
                return int((d2 - d1).total_seconds() // 60)
            
            # Filtrar por duración mínima
            libres_validos = [
                (i, f) 
                for (i, f) in libres 
                if _mins(i, f) >= h.duracion_minima_minutos
            ]
            
            # Agregar a respuesta
            for (i, f) in libres_validos:
                resp["continuo"].append({
                    "inicio": i.strftime("%H:%M"),
                    "fin": f.strftime("%H:%M"),
                    "min": h.duracion_minima_minutos,
                })

    return JsonResponse(resp)