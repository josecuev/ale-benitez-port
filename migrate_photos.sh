#!/usr/bin/env bash
# migrate_photos.sh
# Copia fotos existentes al directorio media/portfolio/ del backend Django.
#
# Uso local (dev):
#   ./migrate_photos.sh /ruta/a/tus/fotos
#
# Uso en producción (dentro del servidor):
#   ./migrate_photos.sh /ruta/a/tus/fotos [nombre-del-volumen-docker]
#
# Si se pasa un nombre de volumen Docker, copia las fotos directamente
# al volumen usando un contenedor temporal.
#
# Ejemplos:
#   ./migrate_photos.sh ~/fotos_portfolio
#   ./migrate_photos.sh ~/fotos_portfolio media_data

set -e

SOURCE_DIR="${1:-}"
DOCKER_VOLUME="${2:-}"
DEST_LOCAL="./ab_reservas_project/media/portfolio"

# ── Validaciones ────────────────────────────────────────────────────────────
if [[ -z "$SOURCE_DIR" ]]; then
  echo "❌  Uso: $0 <directorio_origen> [nombre_volumen_docker]"
  exit 1
fi

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "❌  El directorio '$SOURCE_DIR' no existe."
  exit 1
fi

EXTENSIONS="jpg jpeg png gif webp JPG JPEG PNG GIF WEBP"

# ── Función: listar imágenes ─────────────────────────────────────────────────
count_images() {
  local dir="$1"
  local total=0
  for ext in $EXTENSIONS; do
    count=$(find "$dir" -maxdepth 1 -name "*.${ext}" | wc -l)
    total=$((total + count))
  done
  echo "$total"
}

TOTAL=$(count_images "$SOURCE_DIR")
if [[ "$TOTAL" -eq 0 ]]; then
  echo "⚠️   No se encontraron imágenes en '$SOURCE_DIR'."
  exit 0
fi

echo "📷  $TOTAL imagen(es) encontrada(s) en '$SOURCE_DIR'"

# ── Modo: volumen Docker ─────────────────────────────────────────────────────
if [[ -n "$DOCKER_VOLUME" ]]; then
  echo "🐳  Copiando al volumen Docker '$DOCKER_VOLUME'..."

  docker run --rm \
    -v "${DOCKER_VOLUME}:/dest" \
    -v "$(realpath "$SOURCE_DIR"):/src:ro" \
    alpine sh -c "
      mkdir -p /dest/portfolio
      cp /src/*.jpg /dest/portfolio/ 2>/dev/null || true
      cp /src/*.jpeg /dest/portfolio/ 2>/dev/null || true
      cp /src/*.png /dest/portfolio/ 2>/dev/null || true
      cp /src/*.gif /dest/portfolio/ 2>/dev/null || true
      cp /src/*.webp /dest/portfolio/ 2>/dev/null || true
      cp /src/*.JPG /dest/portfolio/ 2>/dev/null || true
      cp /src/*.JPEG /dest/portfolio/ 2>/dev/null || true
      cp /src/*.PNG /dest/portfolio/ 2>/dev/null || true
      echo '✅  Fotos copiadas al volumen.'
      ls /dest/portfolio/
    "

# ── Modo: directorio local ───────────────────────────────────────────────────
else
  echo "📁  Copiando a '$DEST_LOCAL'..."
  mkdir -p "$DEST_LOCAL"

  COPIED=0
  for ext in $EXTENSIONS; do
    for file in "$SOURCE_DIR"/*."$ext"; do
      [[ -f "$file" ]] || continue
      cp "$file" "$DEST_LOCAL/"
      echo "   → $(basename "$file")"
      COPIED=$((COPIED + 1))
    done
  done

  echo ""
  echo "✅  $COPIED foto(s) copiada(s) a '$DEST_LOCAL'."
  echo ""
  echo "💡  Próximos pasos:"
  echo "    1. Abre el admin en /admin/app_portfolio/photo/"
  echo "    2. Crea las entradas de Photo apuntando a cada archivo"
  echo "    3. O usa el shell: docker exec ab-reservas-web python manage.py shell"
fi
