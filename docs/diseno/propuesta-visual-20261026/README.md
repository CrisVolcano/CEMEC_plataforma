# Propuesta visual CEMEC · 26 de octubre de 2026

Estado actualizado: **diseño aprobado e implementado en el observatorio** por solicitud posterior del usuario. Esta carpeta conserva la maqueta separada, cuyos controles siguen siendo demostrativos. Consultar [implementación y recuperación](../interfaz-cartografica-20261026.md). El SIG beta es otra función ya existente y no es el centro de este rediseño.

## Primera pasada: dirección de diseño

Público: personal de monitoreo, técnicos territoriales y visitantes que consultan observaciones térmicas de Petén. Tarea principal: elegir un territorio y período, entender las observaciones y producir una salida con trazabilidad.

Concepto: **observatorio cartográfico de Petén**. El territorio aporta la identidad. La interfaz funciona como una mesa de consulta: selección a la izquierda, mapa amplio y resultados a continuación. Evitar que la portada se convierta en una sucesión de tarjetas informativas de igual peso.

Paleta de interfaz propuesta:

| Token | Color | Uso |
|---|---|---|
| Bosque | `#17483F` | Acciones principales y marca de navegación |
| Tinta | `#263E40` | Lectura y datos |
| Niebla | `#E7EEEB` | Fondos secundarios y separaciones |
| Blanco | `#FCFDFC` | Superficie de trabajo |
| Brasa | `#B94A21` | Detecciones y énfasis puntual, sin representar un nivel de riesgo |
| Pizarra | `#586D70` | Texto secundario |

Los colores de sensores se conservan: VIIRS `#c96025`, MODIS `#8954b7`, SLSTR `#3557ae`, ABI `#286d78`. No reinterpretar confianza ni agregar categorías de riesgo mediante color.

Tipografía: Barlow regular/semibold para controles, títulos y lectura de datos, con cifras tabulares. Familia elegida por su legibilidad en una interfaz de trabajo compacta; alternativa del sistema cuando no esté disponible. Sin descargas tipográficas por parte del visor operativo en esta propuesta.

Composición: alineación a la izquierda, encabezado discreto y blanco, un único acento verde dominante, mapa como elemento memorable. En móvil la selección precede al mapa y los controles se distribuyen en filas; no ocultar funciones por tamaño de pantalla.

```text
CEMEC / Observatorio       Explorar · Datos · Fuentes       Administración
──────────────────────────────────────────────────────────────────────────
Petén, Guatemala                              [Descargar] [Generar reporte]
──────────────────────────────────────────────────────────────────────────
Selección territorial │   986 detecciones / período y alcance visibles
Unidad y búsqueda     │   Mapa | Análisis | Registros       Comparar
Territorio            │ ┌──────────────────────────────────────────────┐
Fechas y atajos        │ │                                              │
Más filtros           │ │                 MAPA                         │
Filtros activos       │ │                                              │
Restablecer           │ └──────────────────────────────────────────────┘
                      │   Leyenda + interpretación / cronología
```

## Segunda pasada: crítica antes de construir

Un encabezado verde, métricas en tres tarjetas y más tarjetas de explicación repetirían el patrón actual. Se revisa la composición: encabezado claro, métricas en una sola banda de lectura, explicación en un detalle expandible y ninguna columna informativa permanente a la derecha. Los controles de imágenes se agrupan en una barra cartográfica para evitar competir sobre el mapa. Se conserva una denominación explícita de cada producto. No se usa un mapa inventado ni se simulan nuevos datos.

## Maqueta y límites

Abrir `propuesta.html` directamente en el navegador. La maqueta es autónoma: no inicia APIs, no contiene claves y no utiliza los datos activos del servidor. Incluye una captura real de un mapa del observatorio, no un mapa interactivo. Sus diálogos muestran la ubicación propuesta de las funciones. Las operaciones del producto (sincronizar, filtrar, exportar, cargar imágenes) no se ejecutan aquí.

También se puede servir por separado desde la raíz del proyecto:

```bash
./.conda-env/bin/python -m http.server 8092 --bind 127.0.0.1 --directory docs/diseno/propuesta-visual-20261026
```

Abrir `http://localhost:8092/propuesta.html`. El visor operativo continúa en su puerto habitual, 8090. Detener este servidor de propuesta con Ctrl+C no detiene el observatorio. En móvil, la selección territorial comienza plegada con su alcance visible y se abre al pulsar su título.

El ejemplo corresponde a Petén, VIIRS, marzo de 2026. El conteo se obtiene del visor al capturar y se registra en `ejemplo.json`. La captura de mapa y la del visor vigente son referencias, no productos cartográficos para análisis. No eliminar atribuciones si una futura implementación muestra otros fondos.

## Conservación funcional

| Función vigente | Ubicación propuesta | Condición para implementar |
|---|---|---|
| Región, municipio, área protegida, zona de manejo | Columna Selección territorial | Reutilizar eventos y geometrías actuales |
| Búsqueda y selección de territorio | Misma columna | Conservar búsqueda y unidad activa |
| Fechas UTC y períodos rápidos | Misma columna | Sin cambio de ventanas temporales |
| Fuente, instrumento, satélites, confianza, día/noche, color | Más filtros | Conservar todas las opciones y sus semánticas |
| Resumen y restablecimiento | Bajo los controles | Mantener filtros activos visibles |
| Mapa, análisis y registros | Pestañas sobre el mapa | Reutilizar vistas actuales |
| Comparación entre fuentes | Comparar observaciones | Preservar filtros y reporte de comparación |
| Límites, contexto, capas y fondo Esri | Capas del mapa | Mantener atribuciones y selección opcional |
| Sentinel-3 OLCI e imágenes por fecha | Barra de imágenes: Sentinel-3 | Conservar búsquedas, opacidad, fechas y metadatos |
| Mosaico trimestral Sentinel-2 | Barra de imágenes: Mosaico Sentinel-2 | Conservar producto, presupuesto, caché y opacidad |
| Detalle Sentinel-2 | Dentro de sus controles | Mantener límites y retorno a vista general; no reintroducir detalle S3 |
| Reportes PDF y tablas | Generar reporte | Conservar alcance, selección de opciones y comparación |
| PDF georreferenciado beta | Dentro de Generar reporte | Mantener CRS, extensión, DPI, leyendas y metadatos |
| CSV, GeoJSON, GeoParquet, FGB, PMTiles y catálogo | Descargar / Datos | Conservar diferencias entre selección y catálogo completo |
| Fuentes, sensores, metodología y cobertura | Fuentes y sensores / explicación expandible | Mantener advertencias y estados de actualización |
| FIRMS y EUMETSAT | Administración y Fuentes | Conservar autenticación del backend, tareas y errores |
| Ajustes, importar, mapas y lotes | Administración | Mantener flujos completos, sin fingir control de acceso nuevo |
| Puente a GeoLibre | Datos | Conservar beta y descarga local |
| Vacío, carga, error y aviso de cobertura | Junto a los resultados | Igual información, jerarquía más clara |

## Aplicación futura y verificación

Si se solicita implementar: empezar con estilos y redistribución de componentes existentes en `ui/cemec-ui.css` y `ui/cemec-view.js`. No modificar backend, motores de exportación, datos, claves, productos de imágenes ni presupuestos para lograr este aspecto. Mover un control requiere comprobar foco, accesibilidad, diálogo y comportamiento en móvil, no solo apariencia.

La propuesta no puede garantizar conservación funcional por sí sola: la implementación debe pasar las pruebas del visor y de cada módulo afectado, además de comparación visual de filtros, mapas, imágenes, reportes y descargas. No se añaden alertas automáticas, pronósticos, clasificaciones de riesgo ni nuevas mediciones científicas.

Validación de la maqueta: anchos 1600, 1024 y 390 px; diálogos, cierre con Escape y retorno del foco; tabla y 31 barras de datos diarios reales; 28 días con observaciones; ausencia de desbordamiento horizontal y de solicitudes HTTP externas al abrir el archivo local. Registro en `validacion-maqueta.json`. Capturas de escritorio, tablet, móvil, fuentes, reporte y filtros móviles en esta carpeta. Esta validación corresponde a la propuesta, no a una implementación del rediseño. Durante la etapa de maqueta, los archivos `ui/`, `scripts/`, `serve.js` y `config.yaml` del visor se compararon con el respaldo y entonces permanecían idénticos. La implementación posterior está documentada por separado.

## Recuperación

El respaldo está identificado por `respaldos/ultimo-respaldo-propuesta-visual.json`. Contiene código, sitio estático y snapshots de detecciones existentes, configuración y entorno reproducible; excluye credenciales, instalación Conda y cachés de imágenes. El catálogo activo se comparó antes/después de la copia. Consultar su `manifest.json` para SHA256 y alcance exacto.

Para recuperar, verificar SHA256 y extraer con Python 3.12 `tarfile.extractall(destino_nuevo, filter='data')` a una carpeta nueva; nunca sobre la aplicación en uso. Conservar `.env` del proyecto privado y reconstruir/reutilizar el entorno según los manuales. Si solo se desea recuperar apariencia, comparar `ui/cemec-ui.css`, `ui/cemec-view.js` y los adaptadores en `scripts/` para no revertir datos más recientes. La recuperación de la interfaz inmediatamente anterior a la implementación está documentada en la guía de implementación; el respaldo completo anterior a la propuesta se conserva como referencia adicional.
