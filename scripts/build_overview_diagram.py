"""Genera el SVG de portada, sin dependencias ni llamadas a proveedores.

PNG de distribución: convert -background white -density 144 <svg> <png>
"""
from html import escape
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
DESTINATION = ROOT / "docs/diagramas/cemec-plataforma-flujo.svg"


def build():
    parts = ['''<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="1060" viewBox="0 0 1500 1060" role="img" aria-labelledby="title desc">
<title id="title">CEMEC: de la observación satelital al análisis territorial</title>
<desc id="desc">INAB, FIRMS y EUMETSAT alimentan un catálogo de detecciones. Copernicus aporta imágenes de contexto por una ruta independiente. El visor permite filtrar por territorio, fecha, fuente y sensor, comparar observaciones y exportar resultados.</desc>
<defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0 0L8 4.5L0 9" fill="none" stroke="#477461" stroke-width="1.6"/></marker>
<pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse"><path d="M30 0H0V30" fill="none" stroke="#e4ece7" stroke-width="1"/></pattern></defs>
<style>text{font-family:"DejaVu Sans",Arial,sans-serif;fill:#183d30} .heading{font-weight:700;font-size:27px} .body{font-size:21px;fill:#415b50} .small{font-size:18px;fill:#52695f} .line{fill:none;stroke:#477461;stroke-width:2.4;marker-end:url(#arrow)} .context{stroke:#476f94} </style>
<rect width="1500" height="1060" fill="#fff"/>
<rect x="0" y="0" width="1500" height="186" fill="#edf4ef"/>
<rect x="1130" y="0" width="370" height="186" fill="url(#grid)"/>
<path d="M1210 0C1160 60 1300 80 1240 186M1290 0C1240 60 1380 80 1320 186M1370 0C1320 60 1460 80 1400 186" fill="none" stroke="#c3d8ca" stroke-width="2"/>
<rect x="52" y="43" width="7" height="96" fill="#277450"/>
<text x="80" y="84" font-size="43" font-weight="700">CEMEC</text>
<text x="80" y="126" font-size="27">De la observación satelital al análisis territorial</text>
<text x="80" y="158" class="small">Plataforma de monitoreo de incendios · Petén, Guatemala</text>
''']

    def text(x, y, value, cls="body", **attrs):
        if "font_size" in attrs:
            attrs["style"] = attrs.get("style", "") + f';font-size:{attrs.pop("font_size")}px'
        extra = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
        parts.append(f'<text x="{x}" y="{y}" class="{cls}" {extra}>{escape(value)}</text>')

    def rect(x, y, w, h, fill="#f6f9f7", stroke="#d6e2da", radius=10):
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}"/>')

    def line(path, context=False, arrow=True):
        color = "#476f94" if context else "#477461"
        parts.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.4"/>')
        if arrow:
            # Explicit arrowheads also render reliably in static PNG exporters.
            commands = re.findall(r"([MHV])([0-9 ]+)", path)
            x, y = map(int, commands[0][1].split())
            for command, coordinates in commands[1:]:
                if command == "H":
                    x = int(coordinates)
                else:
                    y = int(coordinates)
            points = f"{x},{y} {x-11},{y-6} {x-11},{y+6}" if commands[-1][0] == "H" else f"{x},{y} {x-6},{y-11} {x+6},{y-11}"
            parts.append(f'<polygon points="{points}" fill="{color}"/>')

    for x, number, name in [(52, "1", "Fuentes de información"), (510, "2", "Gestión en CEMEC"), (1010, "3", "Consulta y resultados")]:
        parts.append(f'<circle cx="{x+15}" cy="230" r="15" fill="#277450"/>')
        parts.append(f'<text x="{x+15}" y="236" text-anchor="middle" style="fill:white;font-size:18px;font-weight:700">{number}</text>')
        text(x+42, 239, name, "heading", font_size="25")

    # Los tres orígenes de detecciones convergen en el catálogo térmico.
    for y, title, subtitle, foot in [
        (275, "Histórico INAB", "Observaciones ya incorporadas", "Conjunto inicial de referencia"),
        (405, "NASA FIRMS", "Detecciones VIIRS y MODIS", "Consulta por API · hasta 30 días"),
        (535, "EUMETSAT", "Sentinel-3 SLSTR · FRP", "Consulta por API · datos térmicos"),
    ]:
        rect(52, y, 365, 112)
        text(73, y+33, title, "heading")
        text(73, y+63, subtitle)
        text(73, y+91, foot, "small")
    line("M417 331H450V496H510")
    line("M417 461H450", arrow=False)
    line("M417 591H450V496", arrow=False)

    rect(510, 275, 420, 372, "#edf4ef", "#b6cfc0")
    text(535, 315, "Catálogo de detecciones", "heading")
    text(535, 353, "Descarga y validación")
    text(535, 385, "Normalización de observaciones")
    text(535, 417, "Control de duplicados")
    parts.append('<path d="M535 441H905" stroke="#b6cfc0"/>')
    text(535, 479, "Histórico + actualizaciones", "heading", font_size="24")
    text(535, 517, "Origen, fechas y trazabilidad")
    text(535, 563, "Sincronización iniciada", "small")
    text(535, 590, "por el operador de la plataforma", "small")
    line("M930 460H1010")

    rect(1010, 275, 438, 372, "#fff", "#adc6b7")
    text(1035, 315, "Visor territorial", "heading")
    text(1035, 354, "Región · municipio")
    text(1035, 386, "Área protegida · zona de manejo")
    text(1035, 426, "Fechas · fuente · sensor")
    parts.append('<path d="M1035 450H1423" stroke="#d6e2da"/>')
    text(1035, 490, "Mapa interactivo", "heading", font_size="24")
    text(1035, 525, "Gráficas y tabla de registros")
    text(1035, 560, "Comparación de observaciones")
    text(1035, 609, "Mismos filtros en la consulta", "small")

    # La imagen aporta contexto visual; no produce nuevas detecciones.
    rect(52, 706, 365, 158, "#f0f5fa", "#c4d5e4")
    text(73, 741, "Copernicus Data Space", "heading", font_size="25")
    text(73, 777, "Sentinel-3 OLCI")
    text(73, 808, "Mosaicos trimestrales Sentinel-2")
    text(73, 840, "Imágenes opcionales de contexto", "small")
    line("M417 784H510", True)
    rect(510, 706, 420, 158, "#f0f5fa", "#c4d5e4")
    text(535, 741, "Imágenes bajo demanda", "heading", font_size="25")
    text(535, 778, "Preparación, caché y límites")
    text(535, 810, "Detalle local opcional en Sentinel-2")
    text(535, 840, "No añade puntos al catálogo térmico", "small")
    line("M930 784H972V600H1010", True)

    line("M1229 647V706")
    rect(1010, 706, 438, 206, "#183d30", "#183d30")
    text(1035, 744, "Resultados para compartir", "heading", style="fill:white;font-size:25px")
    for y, label in [(784, "Reporte analítico PDF"), (818, "Mapa PDF georreferenciado · beta"), (852, "Datos CSV / GeoJSON"), (886, "Imágenes y metadatos por separado")]:
        text(1035, y, label, style="fill:#edf4ef;font-size:20px")

    parts.append('<path d="M52 947H1448" stroke="#d6e2da"/>')
    text(52, 983, "Las detecciones son observaciones térmicas; requieren interpretación y verificación en campo.", "body", font_size="20")
    text(52, 1018, "Las imágenes aportan contexto visual. El visor funciona en navegador; los servicios se ejecutan en equipo o servidor propio.", "small")
    parts.append('</svg>')
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    DESTINATION.write_text("\n".join(parts)+"\n", encoding="utf-8")
    print(DESTINATION)


if __name__ == "__main__":
    build()
