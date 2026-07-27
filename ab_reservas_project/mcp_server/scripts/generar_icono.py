"""
Genera `mcp_server/icono.py`: la F de Fractalia, negra sobre el amarillo de marca.

El ícono queda embebido en el código como data URI, así que este script es el
único lugar donde se lo edita. Cambiás el SVG de acá abajo, corrés:

    python ab_reservas_project/mcp_server/scripts/generar_icono.py

y `icono.py` se reescribe solo. Nunca edites el base64 a mano.

Necesita `rsvg-convert` (paquete librsvg2-bin) o `inkscape` para el PNG.
"""
import base64
import pathlib
import shutil
import subprocess
import tempfile

AQUI = pathlib.Path(__file__).resolve().parent
DESTINO = AQUI.parent / "icono.py"

AMARILLO = "#ffe927"   # el amarillo de marca de Fractalia

# La F va como path, no como texto: así no depende de que Bebas Neue esté
# instalada en quien renderice el ícono. Proporción condensada y alta, en la
# línea del logotipo.
SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <rect width="64" height="64" rx="13" fill="{AMARILLO}"/>
  <path d="M21.5 14 H42.5 V23.5 H31.5 V28.5 H39.5 V38 H31.5 V50 H21.5 Z" fill="#0a0a0a"/>
</svg>
"""


def _a_png(svg_path: pathlib.Path, png_path: pathlib.Path, lado: int = 128) -> None:
    """Rasteriza el SVG con lo que haya instalado."""
    if shutil.which("rsvg-convert"):
        cmd = ["rsvg-convert", "-w", str(lado), "-h", str(lado),
               "-o", str(png_path), str(svg_path)]
    elif shutil.which("inkscape"):
        cmd = ["inkscape", str(svg_path), "--export-type=png",
               f"--export-width={lado}", f"--export-height={lado}",
               f"--export-filename={png_path}"]
    else:
        raise SystemExit("Falta rsvg-convert o inkscape para rasterizar el SVG.")
    subprocess.run(cmd, check=True, capture_output=True)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        svg_path = pathlib.Path(tmp) / "fractalia.svg"
        png_path = pathlib.Path(tmp) / "fractalia.png"
        svg_path.write_text(SVG, encoding="utf-8")
        _a_png(svg_path, png_path)
        png_b64 = base64.b64encode(png_path.read_bytes()).decode()

    svg_b64 = base64.b64encode(SVG.encode()).decode()

    DESTINO.write_text(f'''"""
Ícono del conector: la F de Fractalia, negra sobre el amarillo de marca.

GENERADO — no editar a mano. Sale de scripts/generar_icono.py.

Va embebido como data URI porque el ícono viaja dentro del protocolo, no como
una URL que el cliente tenga que ir a buscar: funciona igual en una sesión web
que en un cliente de escritorio, y no depende de que el sitio esté arriba.
"""
from mcp.types import Icon

AMARILLO_MARCA = "{AMARILLO}"

_PNG_128 = (
    "{png_b64}"
)

_SVG = (
    "{svg_b64}"
)

# El PNG va primero: es el que entienden todos los clientes. El SVG queda de
# respaldo para los que escalan sin pixelar.
ICONOS = [
    Icon(src="data:image/png;base64," + _PNG_128,
         mimeType="image/png", sizes=["128x128"]),
    Icon(src="data:image/svg+xml;base64," + _SVG,
         mimeType="image/svg+xml", sizes=["any"]),
]
''', encoding="utf-8")

    print(f"PNG 128x128 -> base64 {len(png_b64)} chars")
    print(f"SVG         -> base64 {len(svg_b64)} chars")
    print(f"escrito: {DESTINO}")


if __name__ == "__main__":
    main()
