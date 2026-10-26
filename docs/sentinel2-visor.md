# Sentinel-2 RGB en el visor

**Versión anterior:** el selector L2A descrito aquí fue sustituido por
[mosaicos trimestrales oficiales](mosaicos-sentinel2.md) el 19 de octubre de 2026.
Este documento conserva el registro de la implementación y sus pruebas iniciales.

Implementado el 19 de octubre de 2026. En **Explorar → Mapa** aparecen dos
botones equivalentes: **Sentinel-3 · OLCI** y **Sentinel-2 · RGB**.

## Uso

1. Elegir región, municipio, área protegida o zona de manejo.
2. Abrir **Sentinel-2 · RGB**.
3. Usar **Última disponible → Buscar última imagen**, o **Elegir período**,
   definir fechas UTC, **Buscar imágenes**, elegir una referencia y pulsar
   **Mostrar esta imagen**.
4. Ajustar opacidad, mostrar/ocultar y descargar PNG/JSON desde ese panel.

Solo una imagen de fondo permanece visible. Activar Sentinel-2 oculta OLCI y
viceversa; las composiciones preparadas pueden reactivarse con la casilla
**Mostrar imagen en el mapa**. Cambiar territorio retira ambas imágenes y descarta
respuestas antiguas del navegador. Una consulta fallida conserva la imagen
visible. La búsqueda no cambia las fechas ni los conteos de detecciones térmicas.

Las fechas de búsqueda son UTC; las horas de referencia del panel y mapa se
muestran para Guatemala (UTC−6). Se avisa si la referencia queda fuera del
período de detecciones. Puede haber varias teselas/versiones de una pasada.

## Producto y límites de interpretación

Se consulta **sentinel-2-l2a**, instrumento MSI, RGB **B04/B03/B02**, bandas
nominales de **10 m**, con ganancia visual 2,5 y transparencia dataMask. La salida
se solicita en EPSG:3857 para alinearse con el mapa web. No es un detector de
incendios ni una medición de superficie quemada.

La vista tiene un límite configurable de **1600 píxeles por lado** para controlar
memoria, transferencia y cuota. En un territorio extenso se reduce la resolución
de salida; seleccionar un territorio menor permite una escala más detallada. El
mapa distingue resolución nominal y **Vista ≈ … m/px**, estimada en el centro del
recorte. El zoom no añade detalle a la composición descargada.

Process recibe una ventana de ±10 minutos alrededor de la referencia con
`mosaickingOrder: mostRecent`: puede combinar teselas/versiones de esa pasada.
No está fijado exclusivamente al ID del producto elegido. La última referencia
que intersecta el territorio puede cubrir solo una fracción y presentar nubes.

**Nubosidad del catálogo** corresponde a la tesela de referencia; no es una
medición de nubes sobre el territorio ni sobre todo el mosaico. **Cobertura con
datos** se calcula por alpha > 0 dentro de la geometría y tampoco significa
superficie despejada. No se aplica una máscara automática de nubes ni se exige
una tesela despejada para etiquetarla como la más reciente.

El modo Última busca siete días y amplía a treinta si no encuentra productos. El
modo Período admite hasta 366 días. La búsqueda recorre la paginación completa,
con un máximo de cien páginas; si se alcanza, solicita reducir las fechas sin
presentar resultados incompletos como últimos.

## Configuración, almacenamiento y API

`config.yaml`, sección `sentinel2`: enabled, cache, credenciales por variables,
colección, proyección, resolución nominal y `max_image_side` (128–2400).
Reutiliza CDSE_CLIENT_ID y CDSE_CLIENT_SECRET de `.env`, fuera del sitio público.
Reiniciar el servidor después de cambiar estos parámetros.

El servicio `Sentinel2Service` reutiliza autenticación, catálogo, trabajos,
decodificación PNG, cobertura y caché del motor de imágenes. OLCI conserva sus
rutas y caché anteriores. Las rutas nuevas son:

- `GET /api/sentinel2/status`: configuración y estado ocupado, sin secretos.
- `POST /api/sentinel2/search`: unit_id, mode y start/end para período.
- `POST /api/sentinel2/render`: unit_id, search_id y product_id de esa búsqueda.
- `GET /api/sentinel2/jobs/<id>`: resultado o error de la consulta asíncrona.
- `GET /api/sentinel2/images/<hash>.png` y `.json`: composición y metadatos.

La caché reside en `runtime/sentinel2/<hash>/`. Incluye referencia, colección,
ventana, tamaño de salida, bandas, brillo y bbox en su identidad. El JSON
registra cobertura, escala efectiva, nubosidad del catálogo, unidades de
procesamiento y SHA-256. `.last_used` registra uso desde el backend. El token vive
en memoria y se renueva antes de expirar; se reintenta una vez ante 401.

Cada imagen nueva consume cuota de CDSE. Una composición idéntica guardada se
reutiliza; buscar el catálogo sigue produciendo solicitudes. Hay un trabajador
por servicio de imágenes, independiente de FIRMS/EUMETSAT. Las tareas/búsquedas
recientes viven en memoria; tras reiniciar, se repite la búsqueda para recuperar
una composición existente. El acceso sigue destinado al despliegue local.

Se agregó `retention.sentinel2_unused_days: 30` al inventario de retención,
incluyendo sus temporales conocidos y marcador de uso. **Solo simulación**:
esta integración no activa borrados ni una tarea programada. El PDF y los mapas
de comparación siguen mostrando detecciones/límites; las imágenes RGB se
descargan separadamente.

## Verificación real

En la revisión del 19 de octubre se obtuvo una composición de Sentinel-2C con
referencia **18 de octubre de 2026, 16:48:59 UTC** (10:48:59 en Guatemala).
Resultado: aproximadamente **15,24 %** del territorio con datos; nubosidad de la
tesela de referencia **98,75 %**; vista regional **152,49 m/px** en su centro;
**8,6731 unidades de procesamiento** reportadas. Es una escena parcial y nubosa,
no un fallo de conexión. El período 14–16 de octubre devolvió nueve referencias.

Evidencia: [verificación real](../runtime/sentinel2-qa/live-verification.json),
[mapa](../runtime/sentinel2-qa/localhost-desktop.png),
[selector temporal](../runtime/sentinel2-qa/localhost-period.png) y
[vista móvil](../runtime/sentinel2-qa/localhost-mobile.png).

Pruebas sin cuota real:

```bash
.conda-env/bin/python -m unittest discover -s tests -p 'test_*.py' -v
.conda-env/bin/node tests/check_sentinel2_ui.cjs
.conda-env/bin/node tests/check_olci_ui.cjs
.conda-env/bin/node tests/check_redesign_ui.cjs
```

## Recuperación y respaldo

Para 400/401 comprobar cliente OAuth CDSE y caducidad; para 403 comprobar acceso
a Sentinel Hub; para 429 esperar/revisar cuota. Ante una consulta vacía ampliar
fechas o revisar el territorio. Elegir otra referencia si su cobertura o nubes
impiden interpretarla. Para un trabajo perdido tras reiniciar, volver a buscar.
Los enlaces guardados de PNG/JSON permanecen locales.

`respaldos/ultimo-respaldo-sentinel2.json` identifica `codigo.tar.gz` anterior a
la integración. El manifiesto de su carpeta contiene SHA-256 y rutas. Incluye
código, configuración y documentación; excluye `.env` y datos activos.

Para recuperar: detener el servidor, verificar SHA-256, extraer en una carpeta
separada con Python 3.12 y filtro `data`, copiar las rutas del manifiesto sobre
el proyecto y reiniciar. Conservar `.env` y `runtime/`. El modo
`CEMEC_LEGACY_UI=1` continúa disponible como alternativa de presentación.

Referencias oficiales: [Sentinel-2 L2A](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html),
[ejemplos RGB](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Process/Examples/S2L2A.html).
