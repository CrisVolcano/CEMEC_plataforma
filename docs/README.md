# Documentación de CEMEC

Índice actualizado el 26 de octubre de 2026. Las instrucciones de instalación y
arranque están en el [README principal](../README.md); los parámetros reproducibles
están en [config.yaml](../config.yaml).

## Manuales completos

- [Instalación y configuración para Windows y alternativas](manuales/README.md): PDF, Word y fuente editable.
- [Uso e interpretación de la plataforma](manuales/manual-uso.pdf): sensores, filtros, imágenes, comparación y reportes.

## Operación y mantenimiento

- [Preparación para GitHub](github.md): copia revisable, exclusiones, credenciales, instalación y publicación posterior.
- [FIRMS hasta 30 días por tarea](firms-30-dias.md): ventanas, bloques, consumo y recuperación de fallos.
- [Mapa PDF georreferenciado · beta](mapa-georreferenciado.md): exportación con MapLibre, metadatos, límites y recuperación.
- [Fondo Esri opcional](fondo-esri.md): selector, consumo, atribución y recuperación.

- [Retención de archivos](retencion.md): plazos acordados, datos protegidos,
  simulación de limpieza y condiciones pendientes para activar eliminación real.
- [Capa Sentinel-3 OLCI](olci-visor.md): consulta de imágenes, caché, metadatos,
  credenciales del servidor y recuperación de errores CDSE.
- [Mosaicos trimestrales Sentinel-2](mosaicos-sentinel2.md): producto actual,
  trimestre publicado, caché regional compartida, presupuesto diario y medición de consumo.
- [Detalle de una zona del mosaico](detalle-mosaico.md): carga manual, límites, caché y recuperación.
- [Sentinel-2 RGB anterior](sentinel2-visor.md): registro de la versión L2A sustituida.
- [Recuperar sincronización FIRMS/EUMETSAT](recuperacion-sincronizacion.md):
  diagnóstico de tareas, errores de acceso y consultas sin detecciones.
- [Restaurar la versión anterior](../respaldos/RESTAURAR.md): respaldo y
  recuperación del proyecto.

## Diseño y verificación

- [Interfaz cartográfica del observatorio](diseno/interfaz-cartografica-20261026.md): diseño implementado, controles y recuperación desde el respaldo oculto.
- [Maqueta visual aprobada](diseno/propuesta-visual-20261026/README.md): referencia separada y comparación con la presentación previa.
- [Beta del puente de datos hacia GeoLibre](beta-puente-sig.md): catálogo de prueba local, capas reproducibles y apertura en un SIG externo; revisión científica pendiente.
- [Propuesta de SIG CEMEC Cloud](propuesta-sig-cloud.md): evaluación de GeoLibre, GeoLens, MapLibre y RustGIS; arquitectura y piloto pendientes de validación.
- [Diagrama de arquitectura y flujo de información](diagramas/README.md): PNG para presentaciones, SVG editable y fuente Mermaid.
- [Diseño de interfaz](diseno/README.md) y [registro de entrega](diseno/entrega.json).
- [Validación del fondo Esri](validacion-esri.json).
- [Validación Linux](validacion-linux.json).
- [Validación FIRMS](validacion-firms.json).
- [Validación EUMETSAT](validacion-eumetsat.json).
- [Validación del diseño](validacion-diseno.json).
- [Prueba inicial de acceso CDSE/OLCI](validacion-cdse-olci.md).
- [Validación de OLCI integrado](validacion-olci-visor.json).
- [Validación de Sentinel-2 integrado](validacion-sentinel2.json).
- [Validación de mosaicos trimestrales y consumo](validacion-mosaicos.json).
- [Validación del detalle bajo demanda](validacion-detalle.json).
- [Prueba histórica del recorte OLCI, función retirada](validacion-detalle-s3.json).
- [Diagnóstico del incidente EUMETSAT 403](diagnostico-eumetsat-403.md).

## Estado de la política de retención

Configurada en **modo de simulación**, sin borrado ni tarea automática. Plazos:
OLCI y Sentinel-2, 30 días sin uso; temporales conocidos, 24 horas; snapshots, 30 días con
protección del activo, las tres versiones anteriores más recientes y sus
referencias; registros de tareas terminadas, 90 días.

Se preservan el histórico y las detecciones activas, los originales, los
respaldos, la caché EUMETSAT, las evidencias y el entorno Conda. La primera
simulación del 13 de octubre encontró **cero candidatos**. El procedimiento y las
limitaciones están en [retencion.md](retencion.md).
