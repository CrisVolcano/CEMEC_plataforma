# Evaluación inicial: SIG CEMEC Cloud

**Evolución del alcance:** esta evaluación conserva la alternativa institucional investigada inicialmente. Posteriormente se acordó que CEMEC sea un puente de datos hacia un SIG externo, sin ofrecer procesamiento SIG a visitantes desde su servidor. La implementación vigente de prueba está en [Beta del puente CEMEC → GeoLibre](beta-puente-sig.md). Las capacidades multiusuario y de cómputo descritas abajo son alternativas futuras, no funciones implementadas.

Fecha: 26 de octubre de 2026. Alcance: investigación documental y propuesta;
no se instalaron GeoLibre, GeoLens ni RustGIS y no se modificó el visor.

## Objetivo y recomendación

Ofrecer una aplicación SIG institucional independiente, accesible mediante un
botón **Ingresar al SIG CEMEC Cloud** desde el Observatorio de calor. Permitirá
administrar capas compartidas, preparar mapas y ejecutar análisis, sin convertir
el observatorio especializado en una interfaz SIG general.

Recomendación técnica preliminar: evaluar **GeoLens como catálogo y servicios
de datos**, **GeoLibre como espacio de trabajo SIG** y **MapLibre como motor
cartográfico**. Mantener RustGIS como alternativa complementaria a evaluar para
trabajo de escritorio y automatización. La decisión definitiva requiere un
piloto con datos de CEMEC, versiones fijadas y pruebas de recuperación y permisos.

## Qué representa cada proyecto

| Proyecto | Función | Encaje propuesto |
|---|---|---|
| MapLibre GL JS | Biblioteca de representación de mapas web; ya usada por CEMEC | Motor de visualización, no catálogo ni servidor multiusuario por sí solo |
| GeoLens | Catálogo y constructor de mapas, API, ingestión y análisis alrededor de PostGIS | Datos persistentes, usuarios, permisos, publicación y análisis vectorial en servidor |
| GeoLibre | Aplicación SIG web/escritorio con herramientas de análisis y proyectos | Interfaz de trabajo para explorar, procesar y componer mapas conectados al catálogo |
| RustGIS | Aplicación SIG en Rust, disponible en escritorio y navegador | Opción para usuarios técnicos y tareas específicas; su versión web no equivale a un repositorio institucional compartido |

MapLibre es una biblioteca, mientras que los otros proyectos son aplicaciones
con alcances diferentes. Sus nombres no describen piezas intercambiables.
Fuentes: [MapLibre](https://maplibre.org/maplibre-gl-js/docs/),
[GeoLens](https://github.com/geolens-io/geolens),
[GeoLibre](https://github.com/opengeos/GeoLibre),
[arquitectura de RustGIS](https://rustgis.app/architecture/).

## Qué aporta GeoLens

La documentación describe un catálogo autoalojado con PostGIS, almacenamiento
de ráster y APIs abiertas. Incluye roles viewer/editor/admin y permisos
configurables, además de autenticación OAuth/OIDC. Es la pieza más próxima a
la necesidad de conservar capas institucionales y compartirlas bajo permisos.

Su panel de análisis documenta ocho operaciones vectoriales: buffer, centroide,
recorte, disolución, unión espacial, medición, selección espacial e intersección.
Los resultados pueden materializarse como conjuntos de datos nuevos mediante
tareas del servidor. Este panel no equivale a un motor completo de análisis
ráster ni reemplaza todas las funciones de un SIG de escritorio.

Es posible iniciar el piloto utilizando solo GeoLens y su constructor de mapas;
así se comprueba primero la persistencia y la administración de datos. Añadir
GeoLibre cuando se necesiten más herramientas de trabajo evita exigir toda la
arquitectura desde el primer día.

Fuentes: [análisis](https://docs.getgeolens.com/guides/user/analysis/),
[roles](https://docs.getgeolens.com/guides/admin/users/),
[OAuth/OIDC](https://docs.getgeolens.com/guides/admin/oauth/).

## Qué aporta GeoLibre y cómo se conecta

La documentación de GeoLibre incluye un conector GeoLens para buscar datasets
y agregarlos mediante teselas vectoriales, GeoJSON u otras fuentes ráster. La
escritura de entidades cargadas como GeoJSON está documentada cuando el servidor
lo autoriza. No debe suponerse que una capa de teselas es directamente editable.

GeoLibre ofrece análisis en el navegador mediante distintas herramientas y
motores, con procesamiento auxiliar en ciertos casos. Procesar en un navegador
consume recursos de la computadora del usuario; instalar el sitio en un servidor
no traslada automáticamente todos los cálculos a ese servidor.

Guardar un proyecto, guardar datos y publicar una capa son acciones diferentes.
Una configuración de mapa con referencias a archivos locales puede no funcionar
para otro colega. Debe probarse el flujo completo de conservar el resultado de un
análisis en el catálogo, asignarle permisos y abrirlo desde otra computadora.

Fuentes: [integraciones](https://geolibre.app/user-guide/data-integrations/),
[herramientas](https://geolibre.app/user-guide/processing/),
[proyectos](https://geolibre.app/user-guide/projects/).

## Qué conservar y dónde

| Elemento | Ubicación propuesta |
|---|---|
| Capas vectoriales gestionadas | PostgreSQL/PostGIS del SIG |
| Ráster institucionales gestionados | Almacenamiento de objetos o archivos persistentes; publicación optimizada según el formato |
| Originales exactos recibidos | Archivo institucional independiente; no confiar en el staging de ingestión |
| Catálogo y permisos | Base y servicios del SIG |
| Proyectos y composiciones | Servicio persistente de proyectos o repositorio privado compatible; validar por separado del catálogo de capas |
| Resultados de análisis | Catálogo, después de guardarlos/publicarlos explícitamente |
| Temporales y cachés | Espacio separado, con límites y limpieza controlada |

GeoLens distingue copias gestionadas y referencias externas: registrar un activo
STAC remoto no garantiza conservar sus bytes. Además, la carga de un archivo no
es una promesa de archivo del original exacto. La política institucional debe
distinguir estos casos y respaldar base de datos, archivos, proyectos y originales.

Fuente: [dónde residen los datos en GeoLens](https://docs.getgeolens.com/guides/user/where-data-lives/).

Las capas oficiales aprobadas se conservarían persistentemente. No se les debe
aplicar automáticamente el plazo de limpieza de las imágenes temporales del
Observatorio. Cada resultado guardado debería identificar entradas y versiones,
operación, parámetros, sistema de coordenadas, responsable y fecha. Esta es una
regla propuesta para CEMEC; el grado de trazabilidad disponible se medirá en el piloto.

## Integración con la plataforma actual

Propuesta inicial: un botón que abra el SIG independiente en otra pestaña. Es
compatible con conservar el Observatorio tal como está y actualizar cada servicio
por separado. No requiere incrustar todo un SIG dentro del frontend compilado.

Direcciones ilustrativas, no dominios existentes:

- `https://observatorio.example.org/`: aplicación de monitoreo actual.
- `https://sig.example.org/`: catálogo GeoLens.
- `https://sig.example.org/gis/`: espacio de trabajo GeoLibre, servido bajo el
  mismo origen que el catálogo mediante un proxy.

El SIG necesita sus propios datos persistentes y configuración de acceso. La
aplicación actual ya usa `/api` para sus conectores; colocar ambos sistemas bajo
una sola ruta sin diseñar el proxy causaría conflictos. Separar el SIG del
Observatorio evita ese acoplamiento inicial.

La guía oficial de GeoLibre describe el despliegue junto a GeoLens bajo un mismo
origen. Un inicio de sesión común es viable, pero el proxy por sí solo no transmite
la identidad a GeoLens: se debe configurar también su autenticación y sus permisos.
Los proyectos compartidos tienen su propio contrato y persistencia; no asumir que
el catálogo GeoLens reemplaza automáticamente el servidor de proyectos GeoLibre.

Fuente: [autoalojamiento y datos privados](https://geolibre.app/self-hosting/).

Más adelante, el Observatorio podría abrir una selección en el SIG o publicar
versiones de detecciones mediante servicios/formatos abiertos. Empezar con una
copia publicada y de consulta evita que un análisis modifique el histórico vivo.

## RustGIS: papel posible

RustGIS ofrece herramientas SIG, layouts y automatización, además de una versión
web. Su arquitectura contempla proveedores de bases de datos en escritorio;
algunas capacidades no están en el navegador. Su despliegue web debe evaluarse
por lo que implementa, sin asumir almacenamiento multiusuario, proyectos
institucionales compartidos ni equivalencia con un servidor GIS.

Puede ser útil para equipos que prefieran una herramienta instalada o para
evaluar tareas concretas desde CLI. No se propone como una cuarta dependencia
obligatoria del piloto.

Fuentes: [arquitectura](https://rustgis.app/architecture/),
[espacio de trabajo](https://rustgis.app/user-guide/workspace/),
[datos](https://rustgis.app/user-guide/data/).

## Piloto propuesto y aceptación

Supuesto de trabajo para dimensionar el piloto: acceso inicialmente interno y
capas de prueba representativas, sin compromiso todavía sobre número de usuarios.

1. Acordar las capas y tareas prioritarias: por ejemplo, áreas protegidas,
   municipios, caminos, ríos, uso del suelo y una muestra de detecciones.
2. Levantar GeoLens en infraestructura de prueba separada, con almacenamiento
   persistente y cuentas de administrador, editor y consulta. Fijar versiones.
3. Subir datos vectoriales y un ráster; reiniciar servicios y comprobar persistencia.
4. Ejecutar recorte, buffer e intersección; guardar resultados y abrirlos con otra
   cuenta y desde otra computadora. Compararlos con un resultado de referencia.
5. Conectar GeoLibre y probar lectura privada, edición autorizada, guardado de
   resultados y restauración de un proyecto con sus capas disponibles.
6. Verificar permisos en las API y los archivos, además de en los botones; probar
   que retirar acceso impida nuevas lecturas y no prometer borrar copias descargadas.
7. Realizar una restauración de respaldo en otra instancia y medir respuesta,
   memoria, almacenamiento y concurrencia con tamaños reales de CEMEC.
8. Agregar el botón al Observatorio después de validar la instancia de prueba.

La edición simultánea de una misma capa, la resolución de conflictos, el historial
de versiones y la auditoría deben probarse explícitamente. La colaboración visual
de un proyecto no prueba que exista una transacción multiusuario sobre sus datos.

Para análisis grandes, evaluar tareas de servidor con límites de tiempo, memoria
y concurrencia. No asignar todavía un presupuesto mensual ni especificaciones
definitivas sin conocer datos y usuarios. El SIG puede alojarse en infraestructura
propia o contratada; "cloud" no obliga a contratar una nube específica.

La IA no es necesaria para las operaciones SIG propuestas. El piloto puede
mantenerla desactivada: no requiere tokens de un modelo para recortar o intersectar
capas. Sí necesita recursos de cómputo, almacenamiento, respaldos y operación.

## Estado y decisiones pendientes

Confirmado documentalmente: integración GeoLibre–GeoLens, catálogo persistente,
análisis vectorial de GeoLens, control de acceso y opciones de autoalojamiento.

No comprobado en CEMEC: instalación de los productos, funcionamiento extremo a
extremo, persistencia de todos los resultados, inicio de sesión compartido,
rendimiento, concurrencia, migraciones y recuperación. No es una certificación de
producción ni una promesa de reemplazo completo de QGIS/ArcGIS.

Antes del piloto, definir quiénes ingresan, qué pueden publicar/editar, qué capas
deben permanecer privadas, las primeras operaciones de análisis y quién operará
el servidor. El Observatorio y su beta GeoPDF siguen separados de esta propuesta.
