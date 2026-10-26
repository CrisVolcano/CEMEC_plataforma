# Validación de acceso Sentinel-3 OLCI — 13 de octubre de 2026

Esta prueba precede la integración. La capa ya está incorporada al visor;
consulta [operación de OLCI](olci-visor.md) para el estado y uso actuales.

Se probó CDSE/Sentinel Hub con las credenciales del servidor. Esta etapa es una
validación independiente: no modifica el visor, el catálogo de detecciones ni las
sincronizaciones FIRMS/EUMETSAT. Las credenciales están en `.env`, fuera del
directorio público; no forman parte de los resultados guardados.

## Resultados reales

- Autenticación OAuth client_credentials: correcta.
- Catálogo completo de los últimos siete días: 13 productos que intersectan el
  rectángulo de Petén configurado en `firms.bbox`.
- Referencia más reciente: Sentinel-3B, 2026-10-13 16:05:12 UTC
  (10:05:12 en Guatemala y Costa Rica).
- RGB B08/B06/B04: PNG RGBA de 815 × 730 píxeles, resolución nominal del sensor
  300 m, ganancia visual 2,5. Se procesó una sola composición.
- Ventana procesada: 15:55:12–16:15:12 UTC; puede combinar segmentos/versiones de
  la pasada. No se afirma que cada píxel corresponda exactamente a la referencia.
- Unidades de procesamiento reportadas: 2,2695541381835938.
- Píxeles con datos en el rectángulo: 99,997647 %.
- Píxeles con datos dentro del límite de Petén: 99,996480 %.
- Búsqueda histórica adicional, sin procesar otra imagen: 9–10 de octubre UTC,
  seis productos. Se confirma el acceso al catálogo con fechas explícitas.

La imagen presenta abundante nubosidad. La cobertura se calcula por alpha > 0;
no mide superficie libre de nubes ni detecta humo/fuego automáticamente.
La medición territorial rasteriza el límite existente y es aproximada por píxel.

## Georreferenciación

La salida se solicitó en EPSG:3857 con un bbox transformado desde las coordenadas
CRS84 del proyecto. Esto coincide con la proyección de dibujo del mapa web.
Se verificaron las dimensiones y se superpuso el límite real de Petén utilizando
la misma transformación, con consistencia visual. Esta comprobación permite
preparar una capa raster; no es una evaluación independiente de precisión con
puntos de control ni una prueba de una capa ya incorporada al mapa del visor.

El PNG no tiene georreferenciación interna: debe conservarse con su JSON, que
registra bbox, proyección, fechas, bandas, referencia y SHA-256.

## Evidencias

- [RGB descargado](../runtime/cdse-validation/20261013T185335Z/olci-rgb.png).
- [Superposición del límite de Petén](../runtime/cdse-validation/20261013T185335Z/peten-overlay.png).
- [Metadatos](../runtime/cdse-validation/20261013T185335Z/metadata.json).
- [Medición de cobertura](../runtime/cdse-validation/20261013T185335Z/coverage.json).
- [Catálogo por período](../runtime/cdse-validation/catalog-20261013T185439Z/catalog.json).

## Repetir la prueba

Desde la raíz del proyecto, con CDSE_CLIENT_ID y CDSE_CLIENT_SECRET definidos en
`.env` o en el entorno del servidor:

```bash
# Busca siete días y procesa una composición; consume cuota CDSE.
.conda-env/bin/python scripts/check_cdse_olci.py

# Consulta un período incluido, sin procesar una imagen adicional.
.conda-env/bin/python scripts/check_cdse_olci.py --start 2026-10-09 --end 2026-10-10 --catalog-only

# Elegir una referencia por su índice, ordenada de más nueva a más antigua.
.conda-env/bin/python scripts/check_cdse_olci.py --start 2026-10-09 --end 2026-10-10 --index 1

# Reutiliza la imagen guardada para verificar cobertura y superposición.
.conda-env/bin/node scripts/check_olci_alignment.cjs runtime/cdse-validation/20261013T185335Z
```

Los scripts usan las dependencias existentes del entorno dedicado; no se añadió
Pillow ni se modificó el entorno Conda. La comprobación visual usa el Chrome y
Playwright ya empleados por las pruebas del proyecto. Un error HTTP no imprime
credenciales ni el token. El token de esta prueba vive solo en memoria.

## Integración propuesta

1. Capa opcional OLCI en el menú existente de capas, con opacidad y metadatos.
2. Modos `Última disponible` y `Elegir período`, con lista de pasadas.
3. Consultar intersección con el territorio elegido; mostrar cobertura parcial
   sin llamarla imagen completa ni despejada.
4. Backend con renovación de token, manejo de 401/403/429 y caché de PNG/JSON.
5. Fecha de imagen independiente de filtros térmicos, con aviso si difieren.
6. Mantener debajo de límites y detecciones; probar alineación dentro del visor y
   su comportamiento al cambiar unidad de análisis.

Fuentes: [OLCI](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S3OLCI.html),
[RGB](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Process/Examples/S3OLCI.html),
[OAuth](https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html).
