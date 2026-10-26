# Capa OLCI del visor

Desde el 19 de octubre de 2026 comparte el mapa con un segundo botón de
[mosaicos trimestrales Sentinel-2](mosaicos-sentinel2.md). Solo una imagen de fondo permanece activa;
la selección, metadatos y caché de OLCI se conservan separados.

Implementada el 13 de octubre de 2026. Consulta CDSE/Sentinel Hub para obtener
RGB de Sentinel-3 OLCI; el conector EUMETSAT/SLSTR continúa separado. No se cambian
el histórico INAB, los archivos originales ni los snapshots de detecciones.

## Flujo y trazabilidad

`ui/olci-layer.js` usa trabajos asíncronos del servicio `scripts/olci_service.py`,
publicados por el backend existente y su proxy local. El catálogo recibe el bbox
de la unidad de análisis; después se descartan productos sin intersección con su
geometría. Se recorren todas las páginas antes de ordenar por adquisición UTC.

El modo Última revisa siete días y, si están vacíos, treinta. El modo Período
admite hasta 366 días y selecciona una referencia del catálogo. Hay un máximo de
100 páginas para proteger la consulta; si se alcanza, se informa búsqueda
incompleta sin etiquetar una referencia como última.

Process recibe B08/B06/B04 y dataMask, EPSG:3857, ganancia 2,5 y ventana ±10
minutos. El ID seleccionado es una referencia temporal: Process puede combinar
segmentos/versiones de esa pasada. La resolución nominal es 300 m; la grilla de
salida no añade detalle y queda limitada a 2400 píxeles por lado aproximadamente.

Cada composición guarda PNG y JSON en `runtime/olci/<sha256>/`. La identidad
incluye territorio, bbox, referencia, ventana, brillo y proyección. El JSON
registra fecha, satélite, bandas, proyección, cobertura territorial/rectangular,
unidades de procesamiento y SHA-256 del PNG. El enlace de metadatos está en el
panel. El PNG requiere su JSON para conservar la georreferenciación.

La cobertura territorial se mide en centros de píxeles dentro de la geometría
con alpha > 0. No es porcentaje despejado. Al cambiar unidad se retira la imagen
anterior y se descarta su respuesta si todavía estaba en curso en el navegador.
La consulta del servidor puede terminar y dejar una composición en caché.

La opacidad, fecha y advertencia temporal no modifican los filtros térmicos. Los
límites y detecciones se dibujan encima del raster; los caminos/rellenos se
suavizan mientras está visible. La capa está disponible en el mapa de Explorar.
El PDF de detecciones y los mapas de comparación siguen su funcionamiento
anterior; OLCI se descarga como PNG/JSON por separado.

## Endpoints

- `GET /api/olci/status`: disponibilidad de configuración, sin credenciales.
- `POST /api/olci/search`: unit_id, mode, start/end cuando mode=period.
- `POST /api/olci/render`: unit_id, search_id y product_id de una búsqueda válida.
- `GET /api/olci/jobs/<id>`: pendiente/en curso/completado/error.
- `GET /api/olci/images/<hash>.png` y `.json`: resultados inmutables.

Las búsquedas y tareas recientes se conservan en memoria; los resultados raster
se conservan en disco. Después de reiniciar, repite la búsqueda: la composición
idéntica usa la caché. Se procesa una tarea OLCI a la vez, en un trabajador
independiente de las sincronizaciones térmicas. Los endpoints internos requieren
el token del proxy; el despliegue conserva su alcance local.

## Si falla

1. Falta configuración: comprobar los nombres CDSE_CLIENT_ID y CDSE_CLIENT_SECRET
   en `.env`, `olci.enabled: true` y reiniciar con `PORT=8090 ./Start-CEMEC.sh`.
   No pegar secretos en los archivos públicos.
2. Autenticación 400/401: revisar cliente OAuth CDSE, secreto y caducidad. El
   servicio renueva automáticamente el token antes de expirar y reintenta una
   vez ante 401 de Catalog/Process.
3. 403: comprobar el acceso de la cuenta a Sentinel Hub/CDSE; son credenciales
   distintas de EUMETSAT.
4. 429: esperar y revisar cuotas. No repetir clics continuamente; las imágenes
   nuevas consumen procesamiento, las composiciones guardadas se reutilizan.
5. Sin imágenes: ampliar fechas o cambiar territorio; el catálogo debe cubrir
   la geometría y el período elegido.
6. Imagen parcial o 0 % con datos: elegir otra pasada. Nubes no transparentes
   siguen contando como datos; el visor no detecta humo/fuego por RGB.
7. Tarea no encontrada tras reinicio: volver a buscar. Los PNG/JSON ya guardados
   siguen disponibles.
8. Otra consulta en curso: esperar a su finalización antes de iniciar otra.

Una consulta fallida no borra la composición visible ni afecta FIRMS/EUMETSAT.
Si no hay conectividad no se pueden consultar pasadas nuevas; los enlaces de
resultados ya guardados continúan siendo locales.

## Verificación y respaldo

La [política de retención](retencion.md) propone conservar la caché OLCI durante
30 días sin uso. Actualmente solo genera un inventario: no elimina imágenes.

Pruebas deterministas: `tests/test_olci.py`. Prueba del flujo con datos simulados
y almacenamiento aislado: `tests/check_olci_ui.cjs`. Evidencia real y capturas en
`runtime/olci-qa`, incluida `live-verification.json`.

`respaldos/ultimo-respaldo-olci.json` identifica el archivo de código anterior a
esta integración. El manifiesto de su carpeta registra SHA-256 y rutas. Excluye
`.env` y no restaura datos activos.

Para recuperar el código anterior: detener el servidor; comprobar SHA-256 contra
el manifiesto; extraer `codigo.tar.gz` en una carpeta separada con Python 3.12 y
`tarfile.extractall(..., filter='data')`; copiar de esa carpeta las rutas del
manifiesto sobre el proyecto, y volver a iniciar. La ruta nueva
`scripts/olci_service.py` y los archivos nuevos pueden conservarse: el código
restaurado deja de invocarlos. Conserva `.env` y `runtime/` para no perder datos.
Como alternativa de presentación inmediata, `CEMEC_LEGACY_UI=1 PORT=8091
./Start-CEMEC.sh` inicia la interfaz heredada, sin la capa nueva.


## Recorte OLCI retirado

El 19 de octubre de 2026 se probó un recorte manual de la zona visible. Se retiró
por solicitud del usuario porque la vista general ya se aproxima a los 300 m
nominales de OLCI y recortar no aporta detalle físico adicional. El visor mantiene
búsqueda, selección de período, opacidad y descarga de la imagen general.
El botón y el endpoint de detalle OLCI están deshabilitados. El detalle de
Sentinel-2 permanece disponible. Los archivos ya generados se conservan para
trazabilidad; no se realizaron borrados de datos ni cambios en la retención.

El [registro de la prueba](validacion-detalle-s3.json) es histórico y no describe
una función activa. El respaldo previo sigue identificado en
[`ultimo-respaldo-detalle-s3.json`](../respaldos/ultimo-respaldo-detalle-s3.json).
