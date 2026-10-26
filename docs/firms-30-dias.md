# NASA FIRMS: hasta 30 días por tarea

26 de octubre de 2026. En **Administración → Ajustes → Conexión NASA FIRMS**, el selector **Ventana de actualización** permite 1, 2, 3, 4, 5, 10, 15 o 30 días. Elegir productos y pulsar **Sincronizar ahora**. El valor inicial continúa siendo tres días; no se activa ninguna tarea automática.

La ventana reciente incluye la fecha actual UTC y las anteriores: treinta días equivalen a hoy y los 29 días precedentes. No es una ventana móvil de 720 horas como intervalo de instantes; la API FIRMS trabaja por fechas. El fin consultado puede ser posterior a la última observación recibida, sin que eso implique un error.

NASA admite de 1 a 5 días por petición Area. CEMEC divide una tarea larga en bloques consecutivos de hasta cinco días por producto, usando fechas iniciales explícitas. Para treinta días son seis bloques por producto: dieciocho peticiones de datos con los tres productos VIIRS configurados, antes de reintentos. Las transacciones de cuota del proveedor no equivalen necesariamente una a una a peticiones HTTP.

La interfaz muestra el bloque en proceso. Los resultados se validan contra fechas y área de cada bloque y se integran al completar las descargas. Los CSV originales, fechas, número de filas, nombres de archivo y SHA256 se conservan en `runtime/firms/downloads/<tarea>/` y en la procedencia de la consulta. La identidad y deduplicación ya existentes se mantienen, incluido el histórico INAB. La disponibilidad depende del producto de NASA.

Si una descarga falla, la tarea falla sin publicar los bloques ya recibidos ni reemplazar el catálogo activo. Los CSV parciales pueden conservarse para diagnóstico. Corregir el motivo y repetir la tarea completa. Un resultado sin detecciones no demuestra ausencia de fuego.

Tras completar la tarea, Explorar adopta las fechas consultadas conservando los otros filtros. Puede ser necesario revisar fuente, instrumento y territorio si la selección vigente excluye los datos descargados. No se requiere cambiar claves.

## Configuración

`config.yaml`:

```yaml
firms:
  days: 3
  max_days_per_sync: 30
```

`max_days_per_sync` admite valores entre 1 y 30. El visor oculta opciones superiores al máximo. El límite por petición a NASA continúa siendo cinco días y no se configura por encima de ese valor. Reiniciar el servidor al cambiar configuración o backend.

## Validación y respaldo

Pruebas sin consumo de la MAP_KEY: cobertura continua de treinta días; ninguna petición mayor de cinco días; último bloque parcial de una tarea de doce días; repetición sin duplicados; preservación del catálogo ante fallo; límite configurable; selección de treinta días y dieciocho respuestas simuladas desde la UI; exportación CSV y fechas del visor.

El código previo está en `.respaldos/antes-firms-30dias_20261026_133358/`, con SHA256. Este cambio no dispara una consulta real de treinta días durante su instalación. Los manuales Markdown están actualizados; PDF/Word y ZIP anteriores conservan su edición previa.

Referencia oficial: [NASA FIRMS Area API](https://firms.modaps.eosdis.nasa.gov/api/area/), documentación del rango 1–5 y de las fechas iniciales.
