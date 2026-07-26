#!/usr/bin/env bash
#
# Clona los datos de producción al entorno local usando manage.py dumpdata/loaddata.
#
#   1. Dump en producción (JSON portable, vía manage.py dumpdata)
#   2. Descarga al directorio .dumps/ (gitignoreado — contiene datos personales)
#   3. Restaura en el Postgres local: migrate → flush → loaddata
#   4. Resincroniza las secuencias de Postgres (si no, el próximo INSERT choca)
#   5. Crea/resetea un superusuario admin/admin para pruebas
#
# Uso:
#   ./sync_prod_to_local.sh                 # ciclo completo
#   ./sync_prod_to_local.sh --skip-dump     # reutiliza el último dump descargado
#   ./sync_prod_to_local.sh --yes           # sin confirmación interactiva
#
set -euo pipefail

# ─── Configuración ────────────────────────────────────────────────────────────
REMOTE_HOST="ab-webpage"
REMOTE_CONTAINER="ab-django"

COMPOSE_FILE="2-docker-compose.reservas.yml"
LOCAL_WEB="ab-reservas-web"
LOCAL_DB="ab-reservas-db"

ADMIN_USER="admin"
ADMIN_PASS="admin"
ADMIN_EMAIL="admin@localhost"

# Se excluyen del dump:
#   contenttypes / auth.permission → los recrea Django en cada migrate; incluirlos rompe loaddata
#   sessions.session               → son tokens de sesión vivos, no sirven local y es PII
#   admin.logentry                 → historial del admin, referencia contenttypes, puro ruido
EXCLUDES=(contenttypes auth.permission sessions.session admin.logentry)

DUMP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.dumps"
STAMP="$(date +%Y%m%d_%H%M%S)"
DUMP_FILE="${DUMP_DIR}/prod_${STAMP}.json"

SKIP_DUMP=0
ASSUME_YES=0
for arg in "$@"; do
  case "$arg" in
    --skip-dump) SKIP_DUMP=1 ;;
    --yes|-y)    ASSUME_YES=1 ;;
    -h|--help)   sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "Opción desconocida: $arg" >&2; exit 2 ;;
  esac
done

# ─── Helpers ──────────────────────────────────────────────────────────────────
c_ok()   { printf '\033[32m✓\033[0m %s\n' "$*"; }
c_info() { printf '\033[36m→\033[0m %s\n' "$*"; }
c_warn() { printf '\033[33m!\033[0m %s\n' "$*"; }
c_err()  { printf '\033[31m✗\033[0m %s\n' "$*" >&2; }

die() { c_err "$*"; exit 1; }

# manage.py local. El compose dev arranca con `poetry run`, pero según la imagen
# `python` puede estar ya en el PATH — probamos las dos formas una sola vez.
# Se guarda como array: si fuese un string, los argumentos con espacios o
# saltos de línea se romperían al expandirse.
LOCAL_MANAGE=()
detect_local_manage() {
  if docker exec "$LOCAL_WEB" sh -c 'cd /app && python manage.py --version' >/dev/null 2>&1; then
    LOCAL_MANAGE=(python manage.py)
  elif docker exec "$LOCAL_WEB" sh -c 'cd /app && poetry run python manage.py --version' >/dev/null 2>&1; then
    LOCAL_MANAGE=(poetry run python manage.py)
  else
    die "No pude ejecutar manage.py dentro de $LOCAL_WEB"
  fi
  c_ok "manage.py local: ${LOCAL_MANAGE[*]}"
}

# `sh -c 'exec "$@"' _ cmd args...` preserva cada argumento intacto,
# a diferencia de interpolarlos dentro del string del comando.
lmanage() {
  docker exec -i "$LOCAL_WEB" sh -c 'cd /app && exec "$@"' _ "${LOCAL_MANAGE[@]}" "$@"
}

# Código Python por stdin en vez de `shell -c`: evita todo problema de
# quoting con punto y coma, comillas y saltos de línea.
# --no-imports: Django 5.2 auto-importa todos los modelos e imprime
# "N objects imported automatically", que contamina la salida.
lshell() {
  docker exec -i "$LOCAL_WEB" sh -c 'cd /app && exec "$@"' _ "${LOCAL_MANAGE[@]}" shell --no-imports
}

# ─── 1. Preflight ─────────────────────────────────────────────────────────────
c_info "Verificando entorno..."

command -v docker >/dev/null || die "docker no está instalado"
docker info >/dev/null 2>&1 || die "El daemon de Docker no responde. Levantalo y reintentá."

if [[ $SKIP_DUMP -eq 0 ]]; then
  ssh -o BatchMode=yes -o ConnectTimeout=10 "$REMOTE_HOST" true 2>/dev/null \
    || die "No hay acceso SSH a '$REMOTE_HOST' (revisá ~/.ssh/config)"
  c_ok "SSH a $REMOTE_HOST"
fi

# Levantar el stack local si hace falta
if ! docker ps --format '{{.Names}}' | grep -qx "$LOCAL_WEB"; then
  c_warn "$LOCAL_WEB no está corriendo — levantando el stack local..."
  docker compose -f "$COMPOSE_FILE" up -d
  c_info "Esperando a que Postgres local acepte conexiones..."
  for i in $(seq 1 30); do
    if docker exec "$LOCAL_DB" pg_isready -q 2>/dev/null; then break; fi
    [[ $i -eq 30 ]] && die "$LOCAL_DB no respondió tras 30s"
    sleep 1
  done
fi
c_ok "Stack local arriba"

detect_local_manage

# Guarda de seguridad: nunca correr el flush contra algo que no sea local.
DB_HOST="$(lshell <<'PY' 2>/dev/null | tr -d '\r' | tail -1
from django.conf import settings
print(settings.DATABASES['default'].get('HOST'))
PY
)" || die "No pude leer la configuración de base de datos del Django local"

[[ "$DB_HOST" == "db" || "$DB_HOST" == "localhost" || "$DB_HOST" == "127.0.0.1" ]] \
  || die "El Django local apunta a HOST='$DB_HOST', que no parece local. Abortando por seguridad."
c_ok "Destino verificado como local (HOST=$DB_HOST)"

# ─── 2. Dump en producción ────────────────────────────────────────────────────
mkdir -p "$DUMP_DIR"
chmod 700 "$DUMP_DIR"

if [[ $SKIP_DUMP -eq 1 ]]; then
  DUMP_FILE="$(ls -1t "$DUMP_DIR"/prod_*.json 2>/dev/null | head -1 || true)"
  [[ -n "$DUMP_FILE" ]] || die "--skip-dump pero no hay ningún dump previo en $DUMP_DIR"
  c_ok "Reutilizando $(basename "$DUMP_FILE")"
else
  EXCLUDE_ARGS=""
  for e in "${EXCLUDES[@]}"; do EXCLUDE_ARGS+=" --exclude $e"; done

  c_info "Generando dump en producción (manage.py dumpdata)..."
  # --natural-foreign/--natural-primary: referencias por clave natural en vez de PK,
  # así los FK a contenttypes/permission resuelven aunque los hayamos excluido.
  # stdout = JSON puro; stderr va aparte para no contaminar el archivo.
  ssh -o BatchMode=yes "$REMOTE_HOST" \
    "docker exec $REMOTE_CONTAINER sh -c 'cd /app && python manage.py dumpdata \
       --natural-foreign --natural-primary $EXCLUDE_ARGS --indent 2'" \
    > "$DUMP_FILE" 2>"${DUMP_FILE}.err" \
    || { c_err "Falló el dumpdata remoto:"; cat "${DUMP_FILE}.err" >&2; exit 1; }

  chmod 600 "$DUMP_FILE"
  [[ -s "$DUMP_FILE" ]] || die "El dump salió vacío"

  # Validar que sea JSON bien formado antes de tocar la base local
  python3 -c "
import json,sys
d=json.load(open('$DUMP_FILE'))
print(f'{len(d)} objetos')
" >/dev/null 2>&1 || die "El dump no es JSON válido — revisá ${DUMP_FILE}.err"

  rm -f "${DUMP_FILE}.err"
  c_ok "Dump descargado: $(basename "$DUMP_FILE") ($(du -h "$DUMP_FILE" | cut -f1))"
fi

# Resumen de contenido
python3 - "$DUMP_FILE" <<'PY'
import json, sys, collections
data = json.load(open(sys.argv[1]))
counts = collections.Counter(o["model"] for o in data)
print(f"   {len(data)} objetos en total:")
for model, n in sorted(counts.items(), key=lambda kv: -kv[1]):
    print(f"     {n:>6}  {model}")
PY

# ─── 3. Confirmación ──────────────────────────────────────────────────────────
if [[ $ASSUME_YES -eq 0 ]]; then
  echo
  c_warn "Esto BORRA todos los datos de la base local ($LOCAL_DB) y los reemplaza."
  read -r -p "   ¿Continuar? [s/N] " reply
  [[ "$reply" =~ ^[sSyY]$ ]] || { echo "Cancelado."; exit 0; }
fi

# ─── 4. Restaurar local ───────────────────────────────────────────────────────
c_info "Aplicando migraciones..."
lmanage migrate --noinput >/dev/null

c_info "Vaciando la base local..."
# flush emite post_migrate, que recrea contenttypes y permissions —
# justo lo que excluimos del dump.
lmanage flush --noinput

c_info "Cargando el dump..."
docker cp "$DUMP_FILE" "$LOCAL_WEB":/tmp/prod_dump.json
lmanage loaddata /tmp/prod_dump.json
docker exec "$LOCAL_WEB" rm -f /tmp/prod_dump.json

# ─── 5. Resincronizar secuencias ──────────────────────────────────────────────
# loaddata inserta PKs explícitas sin mover los sequences de Postgres. Sin este
# paso, el primer INSERT nuevo (crear una reserva) revienta con duplicate key.
c_info "Resincronizando secuencias de Postgres..."
lshell <<'PY'
from django.apps import apps
from django.core.management.color import no_style
from django.db import connection
stmts = connection.ops.sequence_reset_sql(no_style(), apps.get_models())
with connection.cursor() as cur:
    for s in stmts:
        cur.execute(s)
print(f'   {len(stmts)} secuencias reajustadas')
PY

# ─── 6. Superusuario de pruebas ───────────────────────────────────────────────
c_info "Creando superusuario de pruebas..."
ADMIN_USER="$ADMIN_USER" ADMIN_PASS="$ADMIN_PASS" ADMIN_EMAIL="$ADMIN_EMAIL" \
docker exec -i \
  -e ADMIN_USER -e ADMIN_PASS -e ADMIN_EMAIL \
  "$LOCAL_WEB" sh -c 'cd /app && exec "$@"' _ "${LOCAL_MANAGE[@]}" shell --no-imports <<'PY'
import os
from django.contrib.auth import get_user_model
U = get_user_model()
u, created = U.objects.get_or_create(
    username=os.environ["ADMIN_USER"],
    defaults={"email": os.environ["ADMIN_EMAIL"]},
)
u.set_password(os.environ["ADMIN_PASS"])
u.is_staff = u.is_superuser = u.is_active = True
u.save()
print(f"   {'creado' if created else 'actualizado'}: {u.username}")
PY

# ─── 7. Resumen ───────────────────────────────────────────────────────────────
echo
lshell <<'PY'
from app_fractalia.models import Booking, PendingBooking, Resource, Product
from app_analytics.models import PageView
from app_portfolio.models import Photo
from django.contrib.auth import get_user_model
print('  Recursos     :', Resource.objects.count())
print('  Productos    :', Product.objects.count())
print('  Reservas     :', Booking.objects.count())
print('  Pre-reservas :', PendingBooking.objects.count())
print('    - PENDING  :', PendingBooking.objects.filter(status='PENDING').count())
print('  Pageviews    :', PageView.objects.count())
print('  Fotos        :', Photo.objects.count())
print('  Usuarios     :', get_user_model().objects.count())
PY

echo
c_ok "Listo."
echo "   Admin local : http://localhost:8000/admin/  (${ADMIN_USER} / ${ADMIN_PASS})"
echo "   Calendario  : http://localhost:8000/fractalia/calendario/"
echo
c_warn "El dump en .dumps/ tiene datos personales reales (nombres y teléfonos de"
c_warn "clientes, hashes de contraseña). Está gitignoreado — no lo saques de ahí."
