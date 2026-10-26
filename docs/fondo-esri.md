# Fondo Esri opcional

Incorporado el 19 de octubre de 2026. En **Capas del mapa → Mapa de fondo** se
elige entre **Mapa CEMEC** y **Esri · Imagen satelital**. La selección corresponde
a cada mapa y se conserva al cerrar el panel; recargar la página restablece CEMEC.
Los mapas de comparación también ofrecen el selector de forma independiente.

Esri muestra un fondo de referencia. No modifica fechas, filtros, detecciones,
límites ni el histórico. La fecha de las imágenes varía por zona y puede diferir
del período consultado. Los límites, caminos y otras capas del panel se conservan
encima. Las imágenes OLCI y Sentinel-2 también quedan encima de Esri, con su
opacidad habitual, incluso si se cambia el fondo después de cargarlas.

## Consumo

La fuente raster se crea únicamente al elegir Esri. MapLibre solicita las teselas
de la zona y el zoom visibles. Al volver a CEMEC se retiran la capa y la fuente,
sin mantener otro fondo externo oculto. La caché normal del navegador depende de
las respuestas HTTP del proveedor. No se implementa descarga masiva, precarga,
exportación de teselas para uso sin conexión ni almacenamiento en `runtime/`.

Esri necesita Internet y genera tráfico de red y trabajo de dibujo en el
navegador. No utiliza CDSE ni consume su presupuesto de preparaciones o PU; no
requiere nuevos paquetes Conda. La carga pública depende de la disponibilidad y
condiciones del proveedor; un servicio público no supone una cuota ilimitada.
Si una tesela produce un error, el visor vuelve a CEMEC y muestra un aviso en el
panel. Seleccionar Esri nuevamente permite reintentar.

## Configuración y atribución

`config.yaml → interface.basemaps` identifica
[`ui/basemaps.json`](../ui/basemaps.json), leído por el adaptador al preparar el
JavaScript. El valor `default: cemec` evita conexiones externas por defecto.
El archivo define URL, tamaño de tesela, zoom máximo y atribución. Mantener el
predeterminado CEMEC conserva el comportamiento optativo. Reiniciar el servidor
tras cambiar el adaptador; recargar el navegador con Ctrl+F5.

Se utiliza el servicio público **World Imagery**:

`https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`

El acceso anónimo y las teselas se comprobaron en la fecha de incorporación.
La atribución declarada por el servicio y el elemento se incluye mediante el
control de MapLibre: **Esri, Vantor, Earthstar Geographics, and the GIS User
Community**. Los créditos se retiran al desactivar esa fuente.

Referencias: [elemento oficial World Imagery y sus condiciones](https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9),
[servicio y créditos](https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer),
[fuentes raster en MapLibre](https://maplibre.org/maplibre-gl-js/docs/examples/map-tiles/).

El selector afecta al mapa interactivo. Los reportes PDF conservan su cartografía
térmica actual; no se incorporó Esri al exportador ni se alteraron las imágenes
descargables de Sentinel.

## Verificación y recuperación

Código: `ui/basemap-layer.js`, `ui/basemaps.json` y el adaptador
`scripts/redesign.cjs`. Prueba aislada de Chrome, sin peticiones reales a Esri:

```bash
.conda-env/bin/node tests/check_esri_ui.cjs
```

Comprueba carga optativa, atribución, selección al reabrir el panel, detención de
peticiones al desactivar, coexistencia con Sentinel-2, móvil y recuperación de
fallos. La [validación registrada](validacion-esri.json) recoge también la prueba
con teselas reales en localhost.

Si no carga: volver a CEMEC, revisar conexión y disponibilidad de World Imagery y
volver a seleccionarlo. Los datos de CEMEC siguen disponibles sin ese fondo.
No sustituir la URL por servicios desconocidos con credenciales incrustadas.

El respaldo de código anterior está identificado en
[`ultimo-respaldo-esri.json`](../respaldos/ultimo-respaldo-esri.json).
Para restaurarlo: detener el visor, verificar el SHA-256 del archivo frente al
manifiesto, extraer en otra carpeta mediante `tarfile` con filtro `data`, copiar
las rutas del manifiesto y reiniciar. Conservar `.env` y `runtime/`: el respaldo
no sustituye las credenciales ni los datos activos.
