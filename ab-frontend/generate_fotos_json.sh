#!/usr/bin/env bash
set -e

# Nos movemos a assets
cd "public/assets"

PHOTO_DIR="photos"
OUTPUT="photos.json"

if [ ! -d "$PHOTO_DIR" ]; then
  echo "ERROR: No existe la carpeta $PHOTO_DIR"
  exit 1
fi

# Inicia el JSON
echo "{" > "$OUTPUT"
echo '  "photos": [' >> "$OUTPUT"

first=true
# Recorre todas las imágenes
while IFS= read -r file; do
  # Drop leading "./"
  clean="${file#./}"
  if $first; then
    first=false
  else
    echo "    ," >> "$OUTPUT"
  fi
  echo "    \"${clean}\"" >> "$OUTPUT"
done < <(find "$PHOTO_DIR" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) | sort)

# Cierra el JSON
echo "  ]" >> "$OUTPUT"
echo "}" >> "$OUTPUT"

echo "✅ Generado assets/photos.json con $PHOTO_DIR"
