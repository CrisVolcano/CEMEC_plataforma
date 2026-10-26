# Detalle de Sentinel-2 bajo demanda

Implementado el 19 de octubre de 2026. Amplía la vista del mismo mosaico
trimestral; no cambia las fechas ni añade detecciones térmicas.

## Uso

1. En **Explorar → Mapa**, cargar **Sentinel-2 · Mosaico**.
2. Acercarse a la zona de interés. El botón muestra **Acércate para cargar detalle**
   mientras el área sea demasiado extensa.
3. Pulsar **Cargar detalle de esta zona**. Se muestra una estimación de escala y
   superficie antes de solicitarlo. Mover o ampliar el mapa no descarga imágenes.
4. **Vista general** retira el detalle sin consultar CDSE. La vista regional se
   mantiene debajo del recorte para permitir desplazarse fuera de él.

Un detalle que ya cubre la vista con resolución suficiente muestra **Detalle
cargado**. Cambiar de unidad o cargar otro trimestre retira el detalle anterior.
Si una solicitud falla, la imagen anterior continúa visible. Mostrar/ocultar y
opacidad afectan a ambas imágenes; activar OLCI oculta Sentinel-2.

PNG y JSON descargan el detalle cuando está activo. La cobertura indicada es
**del recorte**, no de todo el municipio. El trimestre representa una composición
de tres meses. El PDF térmico conserva sus mapas de detecciones y límites.

## Límites y consumo

`config.yaml`, sección `sentinel2`:

```yaml
detail_enabled: true
detail_max_image_side: 1024
detail_max_area_km2: 400
detail_max_width_km: 30
detail_grid_m: 200
max_new_mosaics_per_day: 6
```

El recorte se intersecta con la extensión del mosaico y se ajusta a una cuadrícula
de 200 m en EPSG:3857 para compartir caché entre solicitudes cercanas. Se rechazan
coordenadas inválidas, áreas fuera del mosaico y recortes que superen 400 km² o
30 km por lado. La escala objetivo es aproximadamente 10 m en el terreno; el
límite de 1024 píxeles puede producir una escala más gruesa en áreas mayores.
Acercarse más a una imagen de 10 m no revela detalle físico adicional.

Los detalles y vistas generales comparten **seis intentos nuevos al día UTC para
todo el proyecto**, incluidos los fallidos. Los aciertos de caché siguen disponibles
al alcanzar el límite. La identidad considera trimestre, revisión, extensión y
resolución. Usuarios y unidades pueden reutilizar el mismo recorte. Los bloqueos
entre procesos evitan preparaciones simultáneas duplicadas.

Una prueba real preparó 3,52 km² a 9,98 m/px (307 × 115 píxeles) y reportó
0,13468 PU. Repetirla reutilizó la caché, sin aumentar el contador. Este consumo
corresponde a ese recorte; no es una tarifa fija ni una estimación de toda la
cuenta CDSE. El registro local está en `runtime/sentinel2/usage.json`.

## API y trazabilidad

`POST /api/sentinel2/detail` recibe:

```json
{"unit_id":"region-peten","image_id":"<id del mosaico regional>","bbox":[-90.31,16.84,-90.28,16.85]}
```

Devuelve una tarea consultable en `/api/sentinel2/jobs/<id>`. El mosaico regional
debe estar guardado; se conserva su colección, trimestre y revisión sin buscar
otro producto. `/api/sentinel2/status` publica `detail_limits`.

Los resultados se guardan en `runtime/sentinel2/<hash>/`, con
`kind: quarterly_mosaic_detail`, `regional_image_id`, `mosaic_period_utc`, extensión,
dimensiones, escala, PU reportadas y hash del PNG. `coverage_scope: visible_crop`
distingue la cobertura del recorte. Las credenciales permanecen en `.env`.
No se añadieron dependencias ni tareas programadas. La retención sigue en
simulación; usar el detalle actualiza también el uso del mosaico de origen.

## Recuperación y respaldo

- Botón desactivado: cargar y activar el mosaico, acercarse o volver a su extensión.
- Límite diario: reutilizar recortes guardados o esperar al siguiente día UTC.
- Mosaico de origen ausente: volver a cargar la vista general y solicitar el detalle.
- Errores CDSE: revisar credenciales, permisos y cuota siguiendo la
  [guía de mosaicos](mosaicos-sentinel2.md). El detalle anterior permanece visible.
- Imagen borrosa: revisar la escala indicada; solicitar un área menor permite
  aproximarse a 10 m, que es el detalle nominal de estas bandas.

El respaldo previo está identificado en
[`ultimo-respaldo-detalle.json`](../respaldos/ultimo-respaldo-detalle.json).
Con el servidor detenido, comprobar el SHA-256 del archivo contra su
`manifest.json`, extraerlo en otra carpeta mediante `tarfile` con filtro `data`
y restaurar las rutas del manifiesto. Conservar `.env` y `runtime/`; este respaldo
contiene código y documentación y no sustituye las detecciones actuales.

La [validación registrada](validacion-detalle.json) enlaza pruebas y evidencia
real. Para ejecutar las pruebas aisladas, sin consumir CDSE:

```bash
.conda-env/bin/python -m unittest discover -s tests -p 'test_*.py'
.conda-env/bin/node tests/check_detail_ui.cjs
```
