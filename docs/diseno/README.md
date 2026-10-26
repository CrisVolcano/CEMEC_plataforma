# Propuesta de diseño de CEMEC

El [diseño cartográfico del 26 de octubre](interfaz-cartografica-20261026.md) está **implementado** y sustituye la presentación descrita abajo. La maqueta aprobada se conserva por separado; la interfaz anterior puede recuperarse desde el respaldo oculto.

Estado: **implementado por solicitud del usuario**. Las maquetas siguientes son
la referencia conceptual; la interfaz funcional usa los datos y mapas reales.
Fecha: 12 de octubre de 2026.

## Maquetas

- [Pantalla principal: Explorar](01-interfaz-principal.png).
- [Fuentes y sensores, comparación y generación de reporte](02-vistas-complementarias.png).

Las imágenes se generaron con la herramienta integrada de generación de imágenes.
Son referencias de composición: sus mapas, fechas, conteos y vista previa de PDF
son ilustrativos. La cartografía y el contenido científico definitivos deben usar
los datos y metadatos reales del proyecto. La especificación escrita siguiente
prevalece sobre diferencias menores de color, navegación o etiquetas en las imágenes.

## Objetivo y usuarios

Facilitar que una persona pueda elegir un territorio, consultar observaciones,
entender sus límites y generar un reporte sin conocimientos previos de las APIs.
Conservar los controles que necesitan analistas y responsables territoriales.

Las ventajas esperadas son menos decisiones iniciales, filtros más comprensibles,
mejor interpretación de fuentes y resultados y un recorrido claro hasta el reporte.
Estas ventajas deben validarse con usuarios; todavía no son resultados medidos.

## 1. Pantalla principal: Explorar

Navegación pública propuesta: **Explorar**, **Datos**, **Fuentes y sensores**.
Acerca de y metodología pueden reunirse en Fuentes y sensores y en el pie de página.
Administración ocupa un acceso separado para operaciones de actualización e importación.

Siempre visibles:

- **Unidad de análisis:** región, municipio, área protegida o zona de manejo.
- **Territorio:** selector con búsqueda y opciones correspondientes a la unidad.
- **Periodo:** accesos rápidos y rango de fechas personalizado.
- **Más filtros:** abre los controles adicionales.
- **Resumen de filtros activos:** cada criterio seleccionado se puede quitar;
  Restablecer vuelve a los valores iniciales.

Los valores equivalentes a «todos» deben verse en el resumen de alcance, sin
presentarse como filtros restrictivos. Un cambio de tipo de unidad exige elegir
un territorio válido; no se debe reutilizar silenciosamente una selección anterior
que pertenezca a otro tipo.

El bloque central contiene mapa, resumen y evolución temporal. El mapa resalta
el territorio seleccionado y contextualiza sus vecinos. La vista inicial ofrece
los resultados con una explicación corta; los registros quedan a un clic.

Indicadores según la selección:

- Número de **detecciones térmicas**, nunca llamado número de incendios.
- Días con observaciones.
- Sensores con observaciones en la selección. Distinguirlos de productos
  consultados que no aportaron observaciones; no afirmar «sensor consultado»
  únicamente porque existe en el catálogo histórico.

Si se muestra el número de municipios con detecciones, indicar que son municipios
distintos. No sumar municipios, áreas protegidas y zonas de manejo para presentarlos
como territorios excluyentes: un mismo punto puede pertenecer a varios límites.

FRP, ranking territorial y distribuciones detalladas se conservan en el análisis
avanzado. Explicar que FRP es potencia radiativa observada, no área quemada ni un
indicador suficiente de riesgo o gravedad del incendio.

## 2. Filtros que se conservan

| Control | Presentación propuesta |
| --- | --- |
| Tipo de unidad y territorio | Siempre visibles; mantener las cuatro categorías originales. |
| Fechas inicial y final | Siempre visibles, junto con accesos rápidos. |
| Fuente | Más filtros: INAB/histórico, NASA FIRMS, EUMETSAT y todas. |
| Instrumento | Más filtros: conservar VIIRS, MODIS, ABI y SLSTR cuando existan datos compatibles. |
| Satélite | Opciones dependientes del instrumento; conservar selección múltiple. |
| Confianza | Clasificación del producto; explicar diferencias y conservar la opción sin clasificar. |
| Día/noche | Más filtros; no excluir silenciosamente observaciones cuyo valor se desconoce. |

El mismo alcance gobierna mapa, estadísticas, registros, comparación y reporte.
Al pasar de una vista a otra, conservar la unidad, territorio, periodo y filtros.
Si se aplica una restricción adicional en comparación, mostrarla explícitamente.

Las unidades de consulta de las APIs, cuando existan, deben mantener su explicación
de rectángulo de consulta. No presentarlas como nuevas jurisdicciones administrativas.

## 3. Fuentes y sensores

Explicación inicial: **la fuente distribuye datos; el sensor realiza la observación**.

Las fichas distinguen:

- **INAB:** histórico incorporado a la plataforma y su procedencia documentada.
- **NASA FIRMS:** productos conectados de VIIRS y MODIS.
- **EUMETSAT:** Sentinel-3A/B, instrumento SLSTR y variante MWIR estándar utilizada.

Cada ficha debe indicar producto, satélite/instrumento, resolución nominal,
disponibilidad temporal, clasificación de calidad y limitaciones. Verificar la
documentación vigente del producto antes de publicar textos sobre frecuencia de
paso, latencia, sensibilidad o confianza. El tamaño del píxel no mide la superficie
del incendio: existen detecciones de fuentes térmicas menores que el píxel.

Explicaciones junto al resultado:

> Un punto de calor es una observación térmica. No confirma por sí solo un incendio.

> Un mismo evento puede ser observado por varios satélites.

> La confianza se define según cada producto; porcentajes o clases de sensores
> distintos no deben interpretarse como escalas idénticas.

El color del mapa puede representar sensor o confianza, según un control explícito
en Más filtros. La leyenda siempre debe indicar qué variable representa. Los
iconos de las fuentes se mantienen neutros, para no crear un segundo código de
colores que compita con la leyenda. No depender solo del color para distinguir
series o estados; añadir etiquetas, símbolos y estilos de línea.

## 4. Comparar observaciones

Vista derivada de Explorar. Elegir los productos/sensores a comparar y conservar
un territorio y periodo comunes.

- Mapas con igual extensión y escala.
- Serie temporal con el mismo eje de fechas y resultados separados.
- Tabla de conteos, días observados y cobertura/disponibilidad conocida por producto.
- Explicación visible de que más observaciones no equivale a más incendios.

No comparar rangos de confianza distintos como si fueran idénticos ni convertir
la suma de observaciones de varios sensores en un total de incendios. Una menor
cantidad de puntos puede obedecer a horario de paso, nubes, resolución, algoritmos
o cobertura; no implica automáticamente un fallo o inferioridad del sensor.

Si falta información para una comparación válida, indicarlo. No completar series
con ceros de forma que una descarga ausente parezca una observación sin detecciones.

## 5. Generar reporte

Acción principal de Explorar: **Generar reporte**, junto a **Descargar datos**.
Se ejecuta al pulsar el botón. La programación periódica de reportes queda fuera
de esta propuesta inicial.

Antes de generar, presentar un resumen del alcance:

> Municipio · San Andrés · periodo seleccionado · fuentes y sensores seleccionados.

Contenido propuesto del PDF:

1. Identificación del territorio y filtros aplicados.
2. Periodo de observación y fecha de generación.
3. Estado y fecha de las consultas de cada fuente; advertencia si faltan datos.
4. Mapa con límites, leyenda, escala y fuentes cartográficas.
5. Resumen y evolución temporal.
6. Resultados separados por fuente/producto y sensor.
7. Explicación de confianza, FRP y limitaciones de interpretación.
8. Metodología, referencias y versión del catálogo utilizado.

Mostrar progreso y confirmar la descarga al terminar. Con cero observaciones,
permitir un reporte que describa el alcance y las limitaciones. Ante datos
incompletos, informar antes de generar y reflejarlo en el documento; no presentar
un informe incompleto como una consulta completa.

Descargar datos conserva los formatos realmente disponibles y los campos de
trazabilidad, especialmente hora UTC y calidad original de Sentinel-3. La vista
de reporte reutiliza las capacidades existentes que se verifiquen adecuadas; la
implementación futura deberá validar el PDF y su correspondencia con la selección.

## 6. Estado de los datos

Mostrar por separado **última consulta exitosa** y **última observación incorporada**,
con detalle por fuente cuando corresponda. La consulta usa un periodo en UTC;
las etiquetas de hora deben especificar UTC o la zona local de presentación.

| Situación | Mensaje propuesto |
| --- | --- |
| Consulta completa sin observaciones en el área | «No se encontraron detecciones dentro del territorio y periodo seleccionados. Esto no demuestra ausencia de incendios». |
| Sin productos disponibles | «No hubo productos disponibles para esta consulta. Comprueba el periodo o la cobertura». |
| Actualización fallida | «La fuente no pudo actualizarse. Se muestran los datos de la última consulta exitosa». |
| Datos parciales | «La consulta está incompleta; los resultados no representan todo el periodo solicitado». |
| Filtros sin resultados | «No hay registros que coincidan con estos filtros». Ofrecer revisar/restablecer. |

El estado de una fuente no debe ocultar el de las demás. La existencia de históricos
no equivale a una consulta reciente de esa fuente. Mostrar errores técnicos,
reintentos y credenciales exclusivamente en administración; el público necesita
entender disponibilidad, antigüedad y alcance.

## 7. Pantallas pequeñas y accesibilidad

En móvil, unidad, territorio y periodo siguen accesibles antes del mapa. Más filtros
abre una hoja o panel con Aplicar y Restablecer; mostrar el número de restricciones
activas. El resumen y las acciones de reporte/descarga deben poder consultarse sin
recorrer varios paneles.

Usar etiquetas completas, foco visible, navegación con teclado, contraste suficiente
y estados comprensibles sin color. El desplegable con búsqueda debe funcionar con
teclado. Las gráficas necesitan un resumen y acceso a sus valores en tabla. Comprobar
el contraste y las medidas finales en el prototipo funcional; las imágenes no
constituyen una validación de accesibilidad.

## 8. Criterios para validar antes de implementar

Probar con usuarios nuevos y personas que ya utilicen el visor:

- Elegir un municipio y cambiar a un área protegida sin ayuda.
- Identificar qué territorio, fechas y fuentes respaldan un resultado.
- Explicar la diferencia entre fuente, sensor y detección/incendio.
- Encontrar una restricción avanzada y retirarla.
- Comparar dos productos manteniendo territorio y periodo comunes.
- Distinguir cero detecciones, ausencia de productos y actualización fallida.
- Generar un reporte y comprobar que coincide con la selección.
- Realizar las tareas básicas en móvil y con teclado.

Registrar tiempo, dudas y errores de interpretación. Ajustar la propuesta con
esas observaciones antes de comenzar la implementación. Los controles avanzados
agrupados añaden un clic: revisar que los usuarios frecuentes los encuentren fácilmente.

## 9. Respaldo de la versión actual

Antes de preparar estas maquetas se guardó un archivo recuperable con código,
sitio original, configuración, especificación y lock Conda, pruebas, documentación,
originales, caché EUMETSAT e historial/snapshots de ambos proveedores.

Consulta [Restaurar la versión anterior](../../respaldos/RESTAURAR.md) y
`respaldos/ultimo-respaldo.json`. El manifiesto registra la versión y número de
observaciones reales del catálogo al crear el respaldo. La implementación añade
una presentación y adaptadores nuevos; los archivos originales y los datos
publicados se conservan.

Las credenciales de `.env` y los paquetes Conda no están en el archivo de respaldo.
Las credenciales existentes siguen en el proyecto; conservarlas por separado para
restaurar en otra ubicación. Los paquetes se reconstruyen con el lock Linux.

## Prompts y herramienta de las figuras

Herramienta: generación de imágenes integrada, sin CLI externo. Resumen del prompt
de la figura principal: una pantalla CEMEC con navegación simplificada, selector
abierto de las cuatro unidades de análisis, territorio/periodo visibles, filtros
adicionales agrupados, mapa/serie temporal y acciones Generar reporte/Descargar datos.

Resumen del prompt de vistas complementarias: tres pantallas consistentes para
explicar fuentes/sensores, comparar observaciones de un mismo territorio/periodo y
revisar el alcance antes de generar un PDF. Edición final: describir el histórico
INAB como detecciones térmicas, preservando la composición.
