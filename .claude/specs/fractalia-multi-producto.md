# Especificación: Fractalia — Calendario Multi-Producto

**Fecha**: 2026-03-26
**Estado**: Listo para implementación
**Rondas de descubrimiento**: 4 + validación contra código

---

## Problema

El sistema actual modela un solo tipo de reserva con reglas hardcodeadas (2/4/6/8h).
No distingue productos. Esto genera:
- Clientes que llegan al WhatsApp del asistente con pedidos mal formados
- El asistente rehace manualmente cada reserva
- Sin soporte para sesiones del fotógrafo (flujo completamente manual)

**Causa raíz**: ausencia de abstracción de "producto" con reglas propias en el modelo y en la UI.

---

## Los 3 Productos sobre un Espacio Físico

| Producto | Visible | Regla de duración | Bloqueo | Flujo |
|----------|---------|-------------------|---------|-------|
| Alquiler de Estudio | Público | 2, 4, 6 u 8 slots de 1h contiguos | = slots elegidos | PendingBooking → asistente confirma |
| Fractabox | Público | Paquetes configurables desde admin | = slots_to_block del paquete | PendingBooking → asistente confirma |
| Sesión Fotográfica (Ale) | Solo is_staff | Libre, sin restricción | = slots elegidos | Booking directo CONFIRMED, sin PendingBooking |

**Invariante**: el espacio físico es uno solo. Un slot ocupado por cualquier producto
bloquea ese slot para todos los demás. La lógica cross-resource de `_get_slots_for_date`
en views.py se mantiene y se extiende a `Booking.clean()`.

---

## Cambios de Modelo de Datos

### NUEVO: `Product`
```python
resource       FK → Resource
name           CharField         "Alquiler de Estudio" / "Fractabox" / "Sesión Fotográfica"
product_type   CharField choices ALQUILER | FRACTABOX | FOTO
is_public      BooleanField      True = visible en web pública sin login
is_active      BooleanField
```

### NUEVO: `FractaboxPackage`
```python
product        FK → Product  (solo para product_type=FRACTABOX)
label          CharField     "45 minutos" — texto que ve el cliente
slots_to_block PositiveIntegerField  1 | 2 | 3 (unidades de 1h)
order          PositiveIntegerField  para ordenar en UI
is_active      BooleanField
```

### MODIFICAR: `Booking`
```python
+ product             FK → Product (null=True, blank=True)
+ fractabox_package   FK → FractaboxPackage (null=True, blank=True)
```

Corrección en `Booking.clean()`:
- El filtro de solapamiento actualmente usa `resource=self.resource` (solo mismo recurso).
  Debe cambiar a cross-resource (sin filtro de resource), igual que `_get_slots_for_date`.
- Para product_type FOTO: saltear la validación de `WeeklyAvailability`.
  Implementar via `save(skip_availability_check=True)` o campo en el modelo.

### MODIFICAR: `PendingBooking`
```python
+ product   FK → Product (null=True, blank=True)
```

### SIN CAMBIOS
`Resource`, `WeeklyAvailability` — sin modificaciones estructurales.

---

## Migración de Datos (crítica)

La migración 0007 ya creó "FractaBox" como un segundo `Resource` (ID 2).
Debe consolidarse antes de crear los Products:

1. Reasignar `PendingBooking` y `Booking` con `resource_id=2` → `resource_id=1`
2. Eliminar WeeklyAvailability del Resource ID 2
3. Eliminar Resource "FractaBox" (ID 2)
4. Crear los 3 Products apuntando al Resource ID 1:
   - Alquiler de Estudio (is_public=True, product_type=ALQUILER)
   - Fractabox (is_public=True, product_type=FRACTABOX)
   - Sesión Fotográfica (is_public=False, product_type=FOTO)
5. Crear los 3 FractaboxPackages iniciales:
   - "45 minutos" → slots_to_block=1
   - "1:30 horas" → slots_to_block=2
   - "3 horas"    → slots_to_block=3

---

## Cambios de Vistas y API

### Vista: `/fractalia/calendario/`

**Lógica de visibilidad:**
```python
if request.user.is_staff:
    products = Product.objects.filter(is_active=True)
else:
    products = Product.objects.filter(is_active=True, is_public=True)
```

**Selector de producto** aparece ANTES del calendario.
La UI adapta su modo según el producto seleccionado.

---

### Modo ALQUILER (sin cambio funcional)
- Slots de 1h seleccionables manualmente
- Validación: total slots en [2, 4, 6, 8] y contiguos
- Sin cambio respecto al comportamiento actual

---

### Modo FRACTABOX (nuevo)
- Paso 1: Mostrar paquetes activos como opciones (radio buttons con `label`)
- Paso 2: Mostrar el calendario del día
- Cada hora de inicio (HH:00) es válida si hay `slots_to_block` slots
  consecutivos disponibles desde esa hora
- Al elegir hora de inicio: el sistema resalta visualmente los slots que
  quedarán bloqueados

---

### Modo FOTO — solo is_staff (nuevo)
- Selección libre de slots (sin restricción de cantidad)
- Booking se crea directamente CONFIRMED (sin PendingBooking)
- No genera código de reserva ni flujo WhatsApp
- `save(skip_availability_check=True)` para ignorar WeeklyAvailability

---

### API: `GET /fractalia/api/disponibilidad/`
Agregar parámetros opcionales:
- `product_type` — para adaptar lógica de validación
- `slots_needed` — para FRACTABOX: N slots consecutivos requeridos

Respuesta para FRACTABOX incluye por slot:
- `available_as_start` (bool) = True solo si los próximos `slots_needed` slots
  están todos libres

---

### API NUEVA: `POST /fractalia/api/reserva-directa/`
- Solo accesible con `is_staff=True` → 403 si no
- Body: `{ product_id, fecha, start_time, end_time }`
- Crea `Booking` directamente con `status=CONFIRMED`
- Sin `PendingBooking`, sin código de reserva
- Usa `save(skip_availability_check=True)` si product_type=FOTO

---

## Cambios en Admin de Django

### NUEVO: `ProductAdmin`
- CRUD de productos
- Inline de `FractaboxPackage` dentro de `ProductAdmin`

### NUEVO: `FractaboxPackageAdmin` (inline)
- Editable: `label`, `slots_to_block`, `order`, `is_active`

### MODIFICAR: `BookingAdmin` y `PendingBookingAdmin`
- Agregar columna `product` en `list_display`
- Sin cambios funcionales

---

## Orden de Implementación Sugerido

1. Modelos + corrección de `Booking.clean()` (cross-resource)
2. Migración de datos (consolidar FractaBox Resource → Product)
3. Actualizar `views.py`: disponibilidad_api con slots_needed, nueva reserva-directa
4. Actualizar `calendario.html`: selector de producto, modos FRACTABOX y FOTO
5. Admin: ProductAdmin + FractaboxPackageAdmin

---

## Criterios de Éxito

- [ ] Cliente público ve solo Fractabox y Alquiler (no Sesión Fotográfica)
- [ ] Asistente (is_staff) ve los 3 productos
- [ ] Cliente Fractabox: elige paquete → elige hora de inicio → N slots bloqueados automáticamente
- [ ] Cliente Alquiler: funciona igual que hoy
- [ ] Asistente crea sesión de Ale directamente (sin WhatsApp ni código)
- [ ] Ningún producto puede solaparse con otro en el calendario
- [ ] Solapamiento validado tanto en view como en `Booking.clean()`
- [ ] Paquetes de Fractabox editables desde admin sin tocar código
