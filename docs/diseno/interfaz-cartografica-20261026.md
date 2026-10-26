# Interfaz cartográfica CEMEC · implementación

Fecha: 26 de octubre de 2026. Diseño aprobado a partir de [la maqueta](propuesta-visual-20261026/README.md). Esta presentación sustituye la interfaz anterior en el observatorio funcional.

## Cambios visibles

- Encabezado claro con identidad CEMEC y nombre del territorio como título de Explorar.
- Selección territorial lateral: región, municipio, área protegida y zona de manejo, búsqueda, fechas UTC, períodos rápidos, resumen y restablecimiento.
- Más filtros conserva fuente, instrumento, satélites, confianza, día/noche y criterio de color.
- Indicadores compactos, incluido el número de sensores presentes; mapa ampliado y comparación accesible desde la barra de resultados.
- Explicaciones en “Cómo leer estos datos”, sin la columna permanente de tarjetas a la derecha.
- OLCI y mosaico Sentinel-2 en una franja sobre el mapa; zoom, capas, atribuciones e imágenes reales conservados.
- En móvil la selección comienza plegada y se abre pulsando su título. Cambiar el tamaño de pantalla ajusta esa disposición, sin cambiar territorio ni filtros.
- Reporte y descarga en la cabecera de Explorar. Los datos completos y el catálogo SIG beta siguen en Datos.
- Barlow servida localmente: dos fuentes TTF, aproximadamente 208 KiB, y licencia OFL en `ui/vendor/barlow/OFL.txt`. No hay proveedor remoto de tipografía.

Se reutilizan los componentes de mapa, análisis, registros y exportación y los adaptadores existentes. Se mantienen semánticas científicas y colores de sensores. El diseño no cambia backend, claves, presupuestos CDSE, productos de imágenes, sincronización ni políticas de retención. No se reintroduce detalle S3.

## Archivos

- `ui/cemec-view.js`: composición, selección plegable y jerarquía de acciones.
- `ui/cemec-ui.css`: estilos y adaptación de escritorio/móvil. El bloque final contiene el diseño cartográfico y conserva estilos de los módulos existentes.
- `ui/vendor/barlow/`: fuentes y licencia.
- `serve.js`: lista explícita de las dos fuentes locales permitidas, con MIME `font/ttf`. Las rutas privadas permanecen inaccesibles.
- Pruebas de interfaz: título territorial y panel móvil actualizados. La prueba de detalle desplaza la vista cuando el recorte existente ya cubre un zoom a resolución nativa, respetando la reutilización de imágenes. La simulación de caída del PDF bloquea solo el exportador, no los demás archivos del proveedor local.

## Recuperación de la interfaz anterior

El respaldo es **oculto**: `.respaldos/ultima-interfaz.json` identifica su carpeta. Contiene `interfaz-anterior.tar.gz` y `manifest.json`, con SHA256. Incluye `ui/`, `scripts/`, `serve.js`, configuración y pruebas de la versión previa. No contiene secretos ni modifica datos. El manifiesto referencia además el respaldo completo de sitio y snapshots realizado antes de la propuesta.

Para inspeccionarlo sin sobrescribir el proyecto, desde la raíz:

```bash
./.conda-env/bin/python - <<'PY'
from pathlib import Path
import json, hashlib, tarfile
pointer = json.loads(Path('.respaldos/ultima-interfaz.json').read_text())
folder = Path(pointer['directory'])
manifest = json.loads((folder / 'manifest.json').read_text())
archive = Path(manifest['archive'])
assert hashlib.sha256(archive.read_bytes()).hexdigest() == manifest['sha256']
destination = Path('.respaldos/recuperacion-interfaz-anterior')
destination.mkdir(exist_ok=False)
with tarfile.open(archive, 'r:gz') as backup:
    backup.extractall(destination, filter='data')
print('Versión anterior extraída en:', destination)
PY
```

Para volver: detener el servidor y recuperar `ui/cemec-view.js`, `ui/cemec-ui.css` y `serve.js` desde esa copia, revisando cambios posteriores antes de reemplazar. Los adaptadores se incluyen por si hacen falta en una recuperación futura. Conservar `.env`, configuración operativa y `runtime/` actuales para no revertir claves ni observaciones. Reiniciar y comprobar el visor. El respaldo no aparece en ningún menú ni se sirve por HTTP.

`CEMEC_LEGACY_UI=1` muestra la compilación original antigua; no recupera la presentación moderna inmediatamente anterior a este cambio.

## Validación

Servidor, fuentes locales y rutas privadas; filtros y navegación; FIRMS/EUMETSAT con datos sintéticos; comparación sincronizada y reporte; CSV; OLCI, mosaico trimestral y detalle Sentinel-2; Esri con teselas simuladas; GeoPDF con GDAL y comparación de esquinas; catálogo SIG beta. Se simulan proveedores en las pruebas para evitar consumo y cambios del catálogo operativo.

Capturas de implementación: `runtime/interfaz-cartografica-qa/`. Registro final: `docs/validacion-interfaz-cartografica.json`. Resultado: **48 pruebas Python y nueve recorridos de interfaz superados**. Los 1127 archivos de la compilación original conservan su integridad. En la prueba del reintento GeoPDF se activa la segunda pestaña y se captura un frame para evitar la suspensión del renderizado en Chromium headless. Las pruebas funcionales no equivalen a aceptación en Windows ni a nueva validación científica de los datos.

Los manuales PDF/Word y ZIP anteriores conservan su edición previa; esta guía documenta las nuevas ubicaciones de controles hasta actualizar esas ediciones.
