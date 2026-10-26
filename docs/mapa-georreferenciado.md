# Mapa PDF georreferenciado · beta

Implementado el 26 de octubre de 2026. Complementa al reporte térmico existente;
es una salida de mapa independiente y no cambia el catálogo ni los filtros.

## Uso

1. En Explorar, seleccione territorio, fechas, fuente, sensor y demás filtros.
2. Abra la pestaña Mapa. Puede activar las capas, el fondo Esri o una imagen ya
   preparada de OLCI/Sentinel-2. Solo se incluye lo visible en ese mapa.
3. Pulse **Generar reporte → Mapa PDF georreferenciado · beta**.
4. Elija A4 o Carta, orientación Horizontal o Vertical, y resolución de salida.
   **150 DPI** es el valor recomendado; 200 DPI requiere más memoria y tiempo.
5. Elija **Territorio completo** para encuadrar la unidad seleccionada, o
   **Vista actual del mapa** para encuadrar la extensión visible. El marco se
   ajusta a la proporción del papel con espacio para los elementos cartográficos.
6. Pulse **Exportar PDF georreferenciado** y espere sin cerrar la ventana.
7. Pulse **Descargar metadatos del mapa** para guardar también el JSON asociado.

El PDF contiene mapa, nombre del territorio, período UTC, filtros, leyenda de
observaciones según sensor o confianza, norte, escala y atribución cartográfica.
La leyenda diferencia el conteo de la selección del conteo dentro del marco.
El nombre del archivo identifica la unidad y las fechas.

## Georreferenciación y alcance

El PDF es una **imagen raster georreferenciada**, con información espacial
ISO 32000 incorporada. Usa **WGS 84 / Pseudo-Mercator, EPSG:3857**, mientras que el
JSON registra las esquinas en longitud/latitud WGS 84. No se genera en la
Transversa de Mercator particular del PDF de referencia de CEMEC.

El JSON conserva territorio, filtros, versión del catálogo, conteos, extensión
solicitada, esquinas efectivas, tamaño en píxeles, capas visibles, identificadores,
URL y coordenadas de las fuentes de imagen cuando existen. No sustituye a los
metadatos científicos de las imágenes: descárguelos en su panel para conservar
fecha/producto/procesamiento del proveedor.

La beta requiere un mapa plano, orientado al norte y sin inclinación ni relieve.
No conserva capas vectoriales editables. Los rótulos HTML de municipios se
omiten porque el exportador los convertiría en símbolos puntuales que podrían
confundirse con detecciones. El nombre de la unidad sí figura en el título.
La opción se ofrece para la selección de Explorar; no exporta los dos mapas de
Comparar observaciones en un mismo documento.

Las imágenes ya cargadas se incluyen con su opacidad. Aumentar DPI no añade
resolución física a OLCI ni a un mosaico. Esri conserva su fecha variable y su
atribución. Exportar puede solicitar teselas a la escala de impresión y leer
imágenes locales, pero **no sincroniza detecciones ni solicita procesamiento
nuevo de imágenes a FIRMS, EUMETSAT o CDSE**.

La composición se realiza en el navegador y se descarga al equipo del usuario;
no se mantiene otra colección de PDF en el servidor. El plugin se carga solo al
exportar. No requiere nuevas claves de API ni instalar GDAL para el usuario.

## Implementación y reproducción

- Motor existente: MapLibre GL JS 5.24.0 del bundle original.
- Exportador: `@watergis/maplibre-gl-export` **6.0.0**, distribución UMD local en
  `ui/vendor/maplibre-gl-export-6.0.0/`. Se comprobó su integridad SHA-512 contra
  npm. Licencia, avisos de terceros y procedencia acompañan los archivos.
- `ui/geopdf.js`: diálogo, exportación, elementos cartográficos y metadatos.
- `scripts/redesign.cjs`: comunica la instancia de MapLibre con la interfaz.
- `serve.js`: publica solo los recursos del complemento autorizados en una lista.
- `tests/check_geopdf_ui.cjs`: exportación real desde Chrome con servicios
  simulados y comprobación geoespacial mediante GDAL.

La adaptación del canvas utiliza el método `getFormat` de la versión fijada del
exportador. Antes de actualizar esa dependencia se debe revisar este punto y
repetir las pruebas. No se carga otra copia de MapLibre ni un SIG completo.
El PDF conserva un marco geográfico continuo; títulos y leyenda se dibujan sobre
la imagen sin desplazarla ni cambiar su transformación espacial.

## Validación

Las pruebas deben verificar la georreferenciación, no solo que el PDF abra:

```bash
.conda-env/bin/node tests/check_geopdf_ui.cjs
.conda-env/bin/python -m unittest discover -s tests -p 'test_*.py'
gdalinfo -json runtime/geopdf-qa/a4-horizontal.pdf
```

La prueba UI requiere Chrome y Playwright 1.58.2, como las otras pruebas visuales
del proyecto, y GDAL disponible en PATH. No son dependencias nuevas del servidor.
Genera A4 horizontal y Carta vertical con filtros VIIRS y una imagen Sentinel-2
simulada. Compara las cuatro esquinas que GDAL recupera con las registradas en
la exportación, con tolerancia de 0,00001 grados. Comprueba conteos, descarga de
metadatos, liberación del mapa temporal y presentación móvil.

La revisión automatizada con GDAL no equivale a una prueba manual en todas las
versiones de QGIS, ArcGIS o Avenza. Para aceptación institucional, abrir un mapa
en el SIG utilizado por CEMEC y compararlo con límites y puntos de referencia.
El registro de esta beta está en [validacion-geopdf.json](validacion-geopdf.json).

## Desactivar y recuperar

Para ocultar la beta al iniciar el servidor, conservando los datos y el reporte:

```bash
CEMEC_GEO_PDF_BETA=0 PORT=8090 ./Start-CEMEC.sh
```

Para activarla de nuevo, inicie sin esa variable o con valor 1. El servidor debe
reiniciarse tras cambiarla y el navegador debe recargar la página.

El respaldo previo de código, documentación y configuración se identifica en
`respaldos/ultimo-respaldo-geopdf.json`, con un manifiesto SHA-256. No incluye
secretos ni datos operativos. Si hace falta recuperar código, extraer primero en
una carpeta separada y comparar; no sobrescribir una instalación activa.

Los ZIP de entrega generados el 19 de octubre no contienen esta beta. Una nueva
entrega debe generarse después de validar los cambios, con la política de
credenciales apropiada para sus destinatarios.

Referencias: [MapLibre Export](https://maplibre-gl-export.water-gis.com/),
[código y compatibilidad](https://github.com/watergis/maplibre-gl-export),
[PDF geoespacial en GDAL](https://gdal.org/en/stable/drivers/raster/pdf.html).
