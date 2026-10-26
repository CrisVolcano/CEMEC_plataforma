# Beta del puente de datos CEMEC → GeoLibre

Implementación local del 26 de octubre de 2026. Entrada: **Datos → Del dato al análisis → Abrir catálogo SIG · beta** o `/sig-beta/`.

## Alcance y responsabilidades

CEMEC ofrece una copia estática del ejercicio y la descarga de sus capas. GeoLibre es el SIG externo (`https://web.geolibre.app/`), abierto en otra pestaña. No se instala GeoLibre ni GeoLens, no se ofrece procesamiento servidor ni almacenamiento de resultados de visitantes. No se utilizan claves API ni se realizan sincronizaciones para construir o abrir este catálogo. El observatorio conserva sus datos y filtros.

La beta es de prueba local, no una publicación institucional aprobada. No se inicia túnel ni despliegue público. La revisión de redistribución de los límites CEMEC queda pendiente antes de publicar. Software libre no significa alojamiento externo garantizado o capacidad de cálculo ilimitada.

## Datos y reproducción

`scripts/build_sig_beta.py` utiliza únicamente el catálogo original `v-79544d8e805b0b1d`:

- Municipios: las 14 geometrías de tipo `municipio`.
- Áreas protegidas: las 68 geometrías de tipo `protegida`, incluidos fragmentos del catálogo. No se han disuelto ni reparado para esta beta.
- Puntos: registros de `web/2026-03.json` con instrumento VIIRS y pertenencia `region-peten`. Se conservan identificador, fuente, instrumento, satélite, fecha/hora UTC, confianza, FRP y versión de producto cuando existen. La membresía de Petén procede del catálogo original, no de un nuevo cálculo espacial. No se aplica deduplicación adicional ni se redefine un incendio.

Esta selección produce **986 puntos**. Las tres capas juntas pesan aproximadamente **791 KiB** sin compresión, según el manifiesto; no incluyen motores de análisis, mapas base ni otros recursos descargados por GeoLibre.

Ejecutar desde la raíz:

```bash
./.conda-env/bin/python scripts/build_sig_beta.py
```

Salida: `ui/sig-beta/data/`. `manifest.json` registra selección, cantidades, procedencia, límites, coordenadas longitud/latitud WGS84 y SHA256 de entradas/salidas. La generación es determinista y no toma el catálogo activo mutable ni datos sintéticos de QA.

## Prueba en localhost

Arranque habitual: `PORT=8090 ./Start-CEMEC.sh`. Si el servidor estaba abierto antes de este cambio, hay que reiniciarlo para registrar las nuevas rutas.

1. Abrir `http://localhost:8090/sig-beta/`.
2. Descargar las tres capas GeoJSON y sus metadatos.
3. Abrir GeoLibre con el botón del catálogo.
4. Agregar los archivos locales desde **Add Data**. El enlace no intenta enviar localhost al sitio HTTPS externo.
5. Preparar una capa con una única área protegida seleccionada. En **Processing → GeoLibre Toolbox → Vector → Select by location**, seleccionar los puntos que intersectan esa máscara, usando **Client (Turf.js)**. Los nombres y el comportamiento deben comprobarse en la versión externa utilizada.
6. Descargar el resultado y anotar entradas, versiones, máscara, predicado y motor. Si se hace un conteo de varias áreas, una detección puede contar en varias por solapamiento; definir tratamiento de bordes y duplicados.

No confundir detecciones con incendios independientes o hectáreas quemadas. No comparar umbrales de confianza como si fueran equivalentes entre productos.

## Apertura conectada futura

GeoLibre documenta parámetros `data` repetidos para cargar varias URL públicas. Para prepararlos se admite `CEMEC_SIG_PUBLIC_BASE_URL`, que debe ser una URL HTTPS del **directorio del catálogo**, por ejemplo `https://datos.example.org/sig-beta/` (ejemplo, no desplegado).

```bash
CEMEC_SIG_PUBLIC_BASE_URL=https://datos.example.org/sig-beta/ PORT=8090 ./Start-CEMEC.sh
```

El botón apuntará a las tres rutas `data/*.geojson` bajo ese directorio. **Configurar esa variable no publica archivos**. Hay que alojar las copias, habilitar CORS y comprobar que sean exactamente la edición del manifiesto. Las rutas de datos de este servidor permiten lectura CORS GET/HEAD/OPTIONS, sin acceso de escritura. La configuración solo devuelve esa URL pública; no devuelve variables de entorno ni secretos. Se rechazan credenciales, parámetros, direcciones IP y nombres locales en esa opción.

Si el sitio externo o los enlaces dejan de funcionar, la descarga directa permite continuar en un SIG de escritorio o volver a importar en GeoLibre. El estado “preparado” no garantiza disponibilidad remota. No hay promesa de funcionamiento de todas las herramientas externas; se limita el ejercicio a operaciones locales.

## Validación y pendientes

Comprobar rutas de lectura, CORS, archivos privados inaccesibles, descargas válidas, procedencia de cada punto y reproducibilidad. Probar el catálogo en pantallas de escritorio y móvil. Comprobar generación del enlace automático sin efectuar una publicación de datos.

Pendientes para declarar validado el recorrido científico: apertura real de los archivos en GeoLibre externo, selección espacial y exportación, comparación con resultado de referencia independiente, comportamiento de fronteras/solapamientos y pruebas con usuarios Windows. No presentar la beta como validada para producción por superar las pruebas HTTP y de interfaz.

Validación ejecutada el 26 de octubre: **47 pruebas Python superadas**; prueba `tests/check_sig_beta_ui.cjs` superada (entrada desde Datos, tres fichas, descarga real de 986 puntos, móvil sin desbordamiento, enlace público simulado y manejo de fallos); regresión `tests/check_redesign_ui.cjs` superada (unidades, filtros, navegación, comparación, PDF, CSV y teclado). Capturas revisadas en `runtime/sig-beta-qa/`. Reconstrucción de datos con SHA256 idénticos. No se transfirieron los datos a un servicio externo durante estas pruebas.

## Respaldo y recuperación

Respaldo anterior al cambio: `respaldos/antes-sig-beta_20261026_121651/codigo.tar.gz`, con SHA256 en `manifest.json`; incluye código y documentación, sin `.env` ni runtime. Para retirar la beta basta quitar su tarjeta en `ui/cemec-view.js` y su bloque de rutas en `serve.js`; los archivos originales no se modificaron. Revisar diferencias antes de restaurar archivos completos para conservar cambios posteriores.

Las entregas ZIP del 19 de octubre y los manuales PDF anteriores no incluyen esta beta. El empaquetador que incluye `ui/` sí incorporará los archivos al generar una nueva entrega; no se generó una nueva en esta tarea.

## Referencias oficiales

- [GeoLibre: apertura remota, parámetros y CORS](https://geolibre.app/user-guide/embedding/).
- [Motores locales de procesamiento](https://geolibre.app/user-guide/processing/).
- [Conexión GeoLens–GeoLibre, alternativa para el catálogo futuro](https://geolibre.app/user-guide/data-integrations/).
