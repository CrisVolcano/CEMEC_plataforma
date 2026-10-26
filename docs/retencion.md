# Retención de archivos

Configurada el 13 de octubre de 2026 en `config.yaml`, sección `retention`.
Estado inicial: **dry_run**, sin eliminación ni programación automática.

Esta política forma parte de la documentación de operación del proyecto y está
enlazada desde el [índice central](README.md) y el [README principal](../README.md).

| Categoría | Política |
|---|---|
| Histórico y catálogo activo | Conservar |
| Caché OLCI | Candidata tras 30 días sin uso |
| Caché Sentinel-2 | Candidata tras 30 días sin uso; incorporada el 19 de octubre |
| Temporales conocidos | Candidatos después de 24 horas; verificar tareas |
| Snapshots anteriores | Conservar 30 días, el activo, las tres versiones anteriores más recientes y todas sus referencias |
| Registros de tareas | Candidatos después de 90 días, únicamente tareas terminadas |
| Originales, respaldos, caché EUMETSAT, evidencias y entorno | Conservar; fuera de esta limpieza |

Ejecutar desde la carpeta del proyecto:

```bash
.conda-env/bin/python scripts/retention.py
```

El informe está en `runtime/retention/latest-plan.json`: lista candidatos,
tamaños, motivos y elementos protegidos. El comando no tiene opción de borrado:
modificar `mode` tampoco activa una eliminación. La primera revisión encontró
cero candidatos. No se ha creado una tarea programada.

La primera simulación se ejecutó el 13 de octubre de 2026 a las 13:37, hora de
Costa Rica. El informe registró cero candidatos y 0 bytes recuperables. Este
resultado corresponde a esa revisión; el informe se reemplaza al volver a
ejecutar el comando. Los plazos se cuentan desde las fechas de uso/modificación
o finalización de cada categoría, no desde la fecha de este documento.

La protección sigue recursivamente las referencias `/live-data/v-.../` del
catálogo activo y de cada snapshot conservado. Si falta una referencia o un
catálogo necesario, se detiene el inventario. Los enlaces simbólicos en rutas
evaluadas también detienen el proceso. Esto evita tratar una geometría antigua
todavía utilizada como una versión prescindible.

Los recortes OLCI actualizan también el uso de su imagen de origen.
OLCI registra uso en `.last_used` al servir una imagen/metadatos o reutilizar la
composición desde el backend. El inventario toma la modificación más reciente de
cualquier archivo de su carpeta como criterio conservador. Una imagen guardada
únicamente en la caché del navegador no produce una nueva solicitud al servidor.
Las imágenes iniciales sin marcador se protegen por sus fechas de modificación.
El registro nuevo de uso entra en vigor al reiniciar el servidor con la versión
actualizada del backend.
Sentinel-2 utiliza el mismo marcador en `runtime/sentinel2` y el plazo
`retention.sentinel2_unused_days`. Incluye los recortes de detalle. Servir o
reutilizar un detalle actualiza también el marcador de su mosaico regional de
origen para conservar esa referencia mientras se utiliza. Su incorporación no
activa eliminaciones.

Los temporales evaluados son `.building-*` de snapshots y `image.tmp` /
`metadata.tmp` de OLCI. No se eliminan archivos genéricos de `/tmp` ni cualquier
archivo por tener determinada extensión. Los registros de tareas pendientes o en
curso se protegen y generan una advertencia.

Antes de habilitar una eliminación real se debe revisar un informe con candidatos
concretos, comprobar tareas activas de ambos motores y revalidar referencias en
el momento de ejecución. También debe evitarse que la publicación y la limpieza
se ejecuten a la vez. Este inventario es la primera etapa; esas garantías de
ejecución todavía no forman parte de un limpiador automático.

Pruebas: `tests/test_retention.py` cubre referencias transitivas, las últimas tres
versiones, referencias faltantes, reutilización de OLCI y tareas activas.
