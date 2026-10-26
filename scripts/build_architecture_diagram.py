"""Diagrama técnico de la arquitectura real; genera SVG sin dependencias.

PNG: convert -background white -density 120 <svg> <png>
"""
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESTINATION = ROOT / 'docs/diagramas/cemec-arquitectura-tecnica.svg'


def build():
    ink, muted = '#173449', '#52697a'
    web, api, image = '#2d5fb1', '#137b7a', '#775bb0'
    parts = ['''<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1410" viewBox="0 0 1800 1410" role="img" aria-labelledby="title desc">
<title id="title">Arquitectura técnica de CEMEC</title>
<desc id="desc">El navegador ejecuta React y MapLibre. Node.js sirve la interfaz y los archivos y reenvía las solicitudes API a Python por loopback con un token interno. Python integra FIRMS, EUMETSAT y Copernicus y mantiene un catálogo de archivos versionados y cachés. Esri sirve teselas directamente al navegador. No hay base de datos SQL ni cola distribuida.</desc>
<rect width="1800" height="1410" fill="#f5f8fb"/>
<path d="M0 0H1800V175H0Z" fill="#173449"/>
<path d="M1510 0V175M1550 0V175M1590 0V175M1630 0V175M1670 0V175M1710 0V175M1750 0V175M1490 35H1800M1490 75H1800M1490 115H1800M1490 155H1800" stroke="#315569" stroke-width="1"/>
''']

    def text(x, y, label, size=23, color=ink, weight=400, mono=False):
        family = 'DejaVu Sans Mono,monospace' if mono else 'DejaVu Sans,Arial,sans-serif'
        parts.append(f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" fill="{color}">{escape(label)}</text>')

    def box(x, y, w, h, fill='#fff', stroke='#d7e1e9', radius=12, dash=False):
        dashed = ' stroke-dasharray="7 6"' if dash else ''
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"{dashed}/>')

    def path(d, color=api, dash=False, width=2.5):
        dashed = ' stroke-dasharray="8 6"' if dash else ''
        parts.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"{dashed}/>')

    def tip(x, y, direction='right', color=api):
        points = {'right':f'{x},{y} {x-11},{y-6} {x-11},{y+6}',
                  'left':f'{x},{y} {x+11},{y-6} {x+11},{y+6}',
                  'down':f'{x},{y} {x-6},{y-11} {x+6},{y-11}',
                  'up':f'{x},{y} {x-6},{y+11} {x+6},{y+11}'}[direction]
        parts.append(f'<polygon points="{points}" fill="{color}"/>')

    def rule(x1, y, x2):
        path(f'M{x1} {y}H{x2}', '#d7e1e9', width=1)

    text(55, 66, 'CEMEC', 42, '#fff', 700)
    text(55, 115, 'Arquitectura técnica de la plataforma', 34, '#fff', 600)
    text(55, 151, 'Interfaz web, servicios de integración, APIs y persistencia geoespacial', 22, '#c7dae7')

    # Límites de ejecución, no supuestos servicios independientes.
    box(50, 225, 420, 1025, '#eef3fa', '#c8d7e8', 18)
    box(530, 225, 780, 1025, '#eef7f5', '#b8d5ce', 18)
    box(1370, 225, 380, 1025, '#f4f0fa', '#d7cce7', 18)
    text(75, 207, 'Cliente', 24, web, 700)
    text(555, 207, 'Equipo o servidor CEMEC', 24, api, 700)
    text(1395, 207, 'Servicios externos', 24, image, 700)

    # Ventana del navegador con una pequeña vista cartográfica.
    box(80, 280, 360, 470, '#fff', '#b6c8dc')
    box(80, 280, 360, 43, '#dfe8f3', '#b6c8dc')
    for x in (101, 118, 135):
        parts.append(f'<circle cx="{x}" cy="301" r="4" fill="#7e99b4"/>')
    text(155, 307, 'localhost:8090', 18, muted, mono=True)
    text(102, 364, 'Interfaz web', 29, ink, 700)
    text(102, 398, 'React + JavaScript + CSS', 22)
    text(102, 430, 'MapLibre GL JS · WebGL', 22, web, 600)
    box(103, 453, 314, 125, '#eaf2f0', '#d1dfd8', 5)
    path('M105 550L160 491L208 530L265 473L317 527L415 482', '#b2c9bd', width=2)
    path('M222 454C190 480 281 518 247 577', '#a3bfd7', width=5)
    for x, y in [(155, 513), (181, 536), (301, 491), (325, 518), (351, 507)]:
        parts.append(f'<circle cx="{x}" cy="{y}" r="5" fill="#da7941"/>')
    text(102, 615, 'Filtros territoriales y temporales', 20)
    text(102, 647, 'Mapa, gráficas y tabla', 22)
    text(102, 679, 'Comparación entre sensores', 21)
    text(102, 721, 'Compilación original + capa ui/', 18, muted)

    # Node expone la web y el único punto de entrada para las rutas internas.
    box(560, 280, 300, 250, '#fff', '#a5cbbb')
    box(580, 301, 75, 28, '#e0f0ea', '#e0f0ea', 5)
    text(589, 321, 'HTTP', 17, api, 700)
    text(582, 369, 'Servidor web', 28, ink, 700)
    text(582, 405, 'Node.js 22', 24, api, 600)
    text(582, 445, 'serve.js', 21, muted, mono=True)
    text(582, 482, 'Archivos + proxy API', 21)
    text(582, 511, 'HTTP Range para PMTiles', 18, muted)
    path('M440 373H560', web); tip(560, 373, color=web); tip(440, 373, 'left', web)
    text(455, 350, 'HTTP', 18, web, 600)
    path('M860 380H900'); tip(900, 380); tip(860, 380, 'left')
    text(560, 575, '/api/… · /live-data/…', 18, api, mono=True)
    text(560, 604, '/data/catalog.json', 18, api, mono=True)

    # Un proceso Python aloja API, tareas e integración de proveedores.
    box(900, 280, 380, 470, '#fff', '#a5cbbb')
    text(924, 323, 'Backend de datos', 28, ink, 700)
    text(924, 358, 'Python 3.12', 24, api, 600)
    text(924, 393, 'ThreadingHTTPServer', 20, muted, mono=True)
    rule(924, 416, 1256)
    text(924, 452, 'API HTTP + respuestas JSON', 21)
    text(924, 487, 'Tareas en hilos y polling', 21)
    text(924, 522, 'Validación y deduplicación', 21)
    text(924, 557, 'Cruces espaciales · Shapely', 21)
    text(924, 592, 'Publicación de snapshots', 21)
    rule(924, 612, 1256)
    text(924, 647, 'Imágenes: caché y presupuestos', 20)
    text(924, 679, 'NumPy · PyArrow · EUMDAC', 20, api)
    text(924, 723, 'Loopback + token interno', 19, muted)

    # Adaptadores y protocolos reales de cada proveedor.
    for y, title, rows, color in [
        (280, 'NASA FIRMS', [('Area API → CSV', 22), ('VIIRS / MODIS · MAP_KEY', 19)], api),
        (465, 'EUMETSAT', [('Data Store · EUMDAC', 21), ('Sentinel-3 SLSTR · FRP', 20), ('OAuth / client credentials', 18)], api),
        (680, 'Copernicus Data Space', [('Catalog + Process API', 20), ('OLCI / mosaicos Sentinel-2', 18), ('OAuth2 · client credentials', 18)], image),
    ]:
        height = 147 if len(rows) == 2 else 168
        box(1395, y, 330, height, '#fff', '#d7cce7')
        parts.append(f'<rect x="1395" y="{y+17}" width="4" height="{height-34}" fill="{color}"/>')
        text(1414, y+38, title, 23 if title.startswith('Copernicus') else 26, ink, 700)
        for idx, (label, size) in enumerate(rows):
            text(1414, y+77+idx*30, label, size, muted)
    path('M1280 439H1340V355H1395'); tip(1395, 355); tip(1280, 439, 'left')
    path('M1280 487H1320V548H1395'); tip(1395, 548); tip(1280, 487, 'left')
    path('M1280 650H1340V763H1395', image); tip(1395, 763, color=image); tip(1280, 650, 'left', image)
    text(1395, 901, 'HTTPS desde el backend', 22, image, 600)
    text(1395, 932, 'Claves y tokens en el servidor', 18, muted)

    # Persistencia real: no dibujar una base PostgreSQL inexistente.
    text(560, 829, 'Persistencia geoespacial en archivos', 25, api, 700)
    box(560, 855, 720, 255, '#fff', '#a5cbbb')
    for x, title, lines in [
        (580, 'Base incluida', [('Histórico INAB', 20), ('JSON · Parquet', 20), ('GeoJSON · PMTiles', 18), ('cemec-sitio-estatico/', 15)]),
        (811, 'Catálogo activo', [('Snapshots versionados', 17), ('JSON · Parquet', 20), ('Estado + procedencia', 17), ('runtime/firms/', 16)]),
        (1056, 'Cachés y tareas', [('Imágenes PNG', 20), ('Metadatos JSON', 19), ('Jobs y uso de APIs', 18), ('runtime/', 17)]),
    ]:
        parts.append(f'<ellipse cx="{x+15}" cy="888" rx="15" ry="6" fill="#d7eae3" stroke="#74a594"/>')
        path(f'M{x} 888V907C{x} 916 {x+30} 916 {x+30} 907V888', '#74a594', width=1.5)
        text(x, 948, title, 22, ink, 600)
        for idx, (label, size) in enumerate(lines):
            text(x, 983+idx*31, label, size, muted)
    path('M791 880V1088M1036 880V1088', '#d7e1e9', width=1)
    path('M840 530V778H543V900H560', web); tip(560, 900, color=web); tip(840, 530, 'up', web)
    text(563, 665, 'Lectura de recursos', 19, web)
    text(563, 694, 'y datos base', 19, web)
    path('M1090 750V855'); tip(1090, 855, 'down'); tip(1090, 750, 'up')
    text(1110, 790, 'Leer / escribir', 18, api)

    # Exportación en navegador, separada de la persistencia del servidor.
    path('M260 750V855', web); tip(260, 855, 'down', web)
    box(80, 855, 360, 255, '#fff', '#b6c8dc')
    text(102, 896, 'Exportación en cliente', 24, ink, 700)
    text(102, 939, 'PDF analítico', 23)
    text(102, 973, 'GeoPDF · beta', 23)
    text(102, 1007, 'CSV / GeoJSON', 23)
    rule(102, 1030, 418)
    text(102, 1064, 'Imágenes + metadatos:', 20, muted)
    text(102, 1091, 'descarga desde el backend', 19, muted)

    box(560, 1140, 720, 83, '#dfeee9', '#c5ded4')
    text(580, 1175, 'Configuración y ejecución', 22, ink, 600)
    text(580, 1206, 'config.yaml + .env local · entorno Conda · scripts/start.py', 19, muted)
    text(80, 1161, 'Procesamiento visual y reportes', 19, web)
    text(80, 1190, 'en el navegador del usuario', 19, web)

    box(1395, 1008, 330, 130, '#fff', '#d7cce7')
    text(1415, 1048, 'Esri World Imagery', 24, ink, 700)
    text(1415, 1084, 'Teselas de fondo opcionales', 19, muted)
    text(1415, 1116, 'Conexión directa al navegador', 18, web)
    path('M1560 1138V1290H24V650H80', web, dash=True)
    tip(80, 650, color=web)
    text(545, 1281, 'Fondo Esri: teselas HTTPS al navegador, sin descarga de colección en CEMEC', 20, web)

    rule(50, 1325, 1750)
    for x, color, label in [(55, web, 'Web y archivos'), (395, api, 'Detecciones / catálogo'), (865, image, 'Imágenes bajo demanda')]:
        path(f'M{x} 1361H{x+38}', color, width=3)
        text(x+50, 1368, label, 20, muted)
    text(55, 1397, 'Arquitectura actual: persistencia en archivos versionados, tareas en hilos y servicios Python / Node.js dentro del mismo entorno Conda.', 19, muted)
    parts.append('</svg>')
    DESTINATION.write_text('\n'.join(parts)+'\n', encoding='utf-8')
    print(DESTINATION)


if __name__ == '__main__':
    build()
