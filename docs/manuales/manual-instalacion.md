# Manual de instalación y configuración de CEMEC

Guía para equipos Windows y responsables de la instalación

Versión documental 1.1 | Plataforma revisada el 19 de octubre de 2026

Este manual distingue el uso de CEMEC desde un navegador de la instalación del servidor en una computadora. Una persona que utiliza Windows puede consultar una instancia ya instalada sin incorporar Linux, Conda ni claves de API a su equipo. El manual de uso describe esa experiencia común.

Si se necesita ejecutar toda la plataforma localmente, Windows nativo es una ruta de adaptación prevista y WSL2 con Ubuntu es una alternativa para reutilizar la versión actual. El origen de la aplicación en Windows y su migración a Ubuntu muestran que el visor es portable; no certifican automáticamente las integraciones añadidas después. Esta edición no presenta WSL2 como requisito general ni afirma que ya exista una entrega nativa Windows validada.

## 1 Elegir la modalidad de uso

Antes de instalar, determine qué necesita la persona. Esta elección evita preparar un entorno de desarrollo cuando solo se necesita consultar la plataforma.

| Modalidad | Qué instala el usuario de Windows | Estado de esta entrega |
|---|---|---|
| Acceso a una instancia instalada | Un navegador actualizado y la dirección facilitada por el responsable. | No requiere WSL2 ni Conda en el equipo del usuario. La disponibilidad depende del servidor y de su acceso de red. |
| Servidor local nativo en Windows | Conda de Windows, entorno del proyecto y una entrega con arranque y conectores adaptados. | Preparación documentada; adaptación y prueba integral del backend pendientes. |
| Servidor local con WSL2 | WSL2, Ubuntu y Conda de Linux dentro de Ubuntu. | Alternativa para ejecutar los scripts Linux existentes; debe validarse en el equipo Windows de destino. |
| Servidor local en Linux | Conda de Linux y los lanzadores incluidos. | Entorno en el que se ha verificado la versión actual. |

### Qué ejecuta la plataforma

El navegador muestra una interfaz web compilada y cartografía. Node.js sirve la web y Python ejecuta las conexiones FIRMS, EUMETSAT y CDSE. Son tecnologías que pueden ejecutarse en Windows y Linux; los scripts de arranque, las rutas y los bloqueos de archivos deben estar adaptados a cada sistema.

Para un usuario de una instancia instalada, las credenciales y la instalación son responsabilidad del operador del servidor. No necesita QGIS, Python, Node.js, Conda ni las cuentas de los proveedores en su computadora para consultar los resultados disponibles.

### Responsables

| Responsable | Tareas |
|---|---|
| Usuario del visor | Abrir la dirección indicada, consultar mapas, filtros y reportes. |
| Responsable técnico | Elegir el sistema del servidor, instalar dependencias, configurar secretos, verificar funciones y conservar respaldos. |
| Operador de datos | Sincronizar fuentes, revisar resultados y documentar incidencias. |
| Administrador del equipo | Autorizar software y red cuando corresponda; WSL2 solo si se elige esa alternativa. |

El menú Administración organiza funciones, pero no implementa cuentas, roles ni una barrera de acceso. Publicar una instancia para terceros requiere preparar esos controles y no está resuelto únicamente por instalarla.

## 2 Requisitos según la modalidad

### Para consultar desde Windows

Necesita un navegador actualizado como Edge, Chrome o Firefox, WebGL habilitado y acceso a la dirección de CEMEC. No se requiere espacio para el archivo institucional ni instalar las dependencias del servidor. La dirección puede ser una URL institucional; localhost solo identifica un servidor en la misma computadora.

### Para instalar el servidor local

La preparación descrita está orientada a Windows 11 de 64 bits y procesador Intel o AMD x86_64. En Windows nativo se utiliza Conda de Windows. En WSL2 se utiliza Conda de Linux dentro de Ubuntu. No se mezclan los entornos ni sus archivos de bloqueo.

| Recurso | Preparación recomendada para el servidor local |
|---|---|
| Memoria | 8 GB para una evaluación; preferiblemente 16 GB para consultas amplias y otras aplicaciones simultáneas. Es una recomendación inicial, no un mínimo medido. |
| Disco | Reservar al menos 20 GB para instalación, dependencias y crecimiento inicial; WSL2 requiere además su distribución. Los datos y respaldos pueden necesitar más. |
| Red | Acceso HTTPS a conda-forge y a los proveedores habilitados. |
| Permisos | Instalar Conda según la política del equipo; administración de Windows para habilitar WSL2 solo si se elige esa ruta. |
| Ubicación | Carpeta local como C:\CEMEC\CEMEC_plataforma; evitar OneDrive, rutas excesivamente largas y discos extraíbles para el servidor. |

El lock environment-linux-64.lock.txt corresponde únicamente a Linux x86_64, incluido WSL2 x86_64. No se utiliza para crear un entorno nativo Windows. Equipos ARM requieren una resolución y una validación específicas.

### Conectividad

Los datos y cartografía locales pueden consultarse sin conexión una vez disponibles. Sin Internet no se sincronizan proveedores, no se preparan imágenes nuevas ni se carga Esri. Los servicios utilizados incluyen FIRMS, EUMETSAT Data Store, CDSE y World Imagery; conda-forge y GitHub intervienen durante la preparación técnica. WSL2 añade las descargas de Microsoft y Ubuntu solo cuando se utiliza.

Ante restricciones de red, solicite a TI la configuración de proxy y certificados. No desactive HTTPS ni su verificación para hacer funcionar una descarga.

## 3 Archivos que se deben recibir

El ZIP original por sí solo no contiene las integraciones, el rediseño ni los lanzadores de esta versión. Solicite una entrega completa del proyecto actualizado.

| Archivo o carpeta | Función y necesidad |
|---|---|
| origen/ | ZIP del sitio y documento originales. Setup verifica sus hashes; se deben conservar. |
| config.yaml | Configuración y trazabilidad de la réplica. No contiene secretos. |
| environment.yml | Dependencias portables del entorno Conda. |
| environment-linux-64.lock.txt | Referencia exacta de Linux x86_64; no usar en Windows nativo. |
| Setup-CEMEC.sh y Start-CEMEC.sh | Lanzadores de Linux y de la alternativa WSL2. No son ejecutables nativos de Windows. |
| serve.js y scripts/ | Servidor, adaptadores, conectores y herramientas de mantenimiento. |
| ui/ | Interfaz añadida, imágenes opcionales y configuración del fondo Esri. Es imprescindible. |
| tests/ y docs/ | Comprobaciones, manuales, registros y manifiesto de originales. |
| .env.example | Ejemplo parcial de variables de entorno; CDSE se añade como indica este manual. |
| cemec-sitio-estatico/ | Sitio extraído. Setup puede reconstruirlo si falta, a partir del ZIP original. |
| runtime/ | Necesaria para trasladar el estado operativo acumulado; opcional para iniciar desde los datos originales. |
| respaldos/ | Historial de recuperación. Conservarlo cuando forme parte de la entrega acordada. |

No reutilice .conda-env ni .conda-pkgs de otro equipo: contienen binarios, cachés y rutas de instalación. No distribuya .env como parte de una entrega abierta.

### Elegir entre instalación inicial y traslado operativo

Una instalación inicial sin runtime conserva el catálogo original: 66.582 observaciones y 117 unidades, con corte al 6 de octubre de 2026. Estos valores describen el paquete original, no un catálogo actualizado automáticamente.

Para trasladar el estado acumulado se debe copiar runtime íntegramente con el servidor detenido, incluyendo snapshots y sus referencias. Copiar solo active.json es insuficiente. Las imágenes guardadas también están bajo runtime. Las credenciales del destino se configuran por separado. Los totales operativos se comprueban en Datos y pueden superar los del paquete original.

Para una entrega nativa Windows se deben proporcionar y validar sus instrucciones de arranque. Esta revisión no añade archivos BAT o PowerShell ni los cita como si ya existieran. La carpeta que contiene solo estos manuales no sustituye una entrega completa de la aplicación.

## 4 Preparar Windows nativo

Esta sección prepara el equipo y el entorno de Windows. La creación del entorno y la verificación de originales no equivalen todavía a una puesta en servicio completa de los conectores. La sección 11 identifica los ajustes pendientes antes de entregar una instalación nativa operativa.

### Instalar Conda de Windows

Descargue Miniforge para Windows x86_64 desde el sitio oficial de conda-forge. Ejecute el instalador y siga las políticas del equipo. Si ya tiene Conda nativo Windows compatible, no necesita instalar otra distribución. No instale Ubuntu ni habilite virtualización para esta modalidad.

Abra Miniforge Prompt desde Inicio y compruebe conda --version. Los comandos de este apartado se ejecutan en esa consola de Windows. Una terminal Ubuntu corresponde a otra modalidad.

### Copiar la entrega

Descomprima la entrega completa en C:\CEMEC\CEMEC_plataforma. Compruebe que config.yaml, environment.yml, serve.js, scripts, ui y origen estén directamente en esa carpeta. Conserve los originales y no reutilice .conda-env ni .conda-pkgs procedentes de Linux o de otro equipo.

### Crear un entorno dedicado

Los siguientes comandos preparan dependencias y verifican el paquete original. No son un lanzador nativo del backend actual.

```cmd
cd /d C:\CEMEC\CEMEC_plataforma
conda env create --prefix .\.conda-env --file environment.yml
conda run --prefix .\.conda-env python scripts/replicate.py
conda run --prefix .\.conda-env python --version
conda run --prefix .\.conda-env node --version
```

Conda debe resolver las dependencias para win-64 desde environment.yml. La resolución de este conjunto en Windows no se ha ejecutado en esta revisión. Si falla, registre la incompatibilidad y ajuste con el responsable; no utilice el lock Linux para forzarla. No repita la creación sobre un entorno ya existente sin revisar su estado.

El entorno declara Python 3.12, Node.js 22, PyYAML, Shapely, NumPy, PyArrow y EUMDAC. No se instala React ni se ejecuta npm install: el frontend se entrega compilado. Una vez resuelto y aceptado en Windows, registre sus paquetes en un lock propio:

```cmd
conda list --prefix .\.conda-env --explicit --sha256 > environment-win-64.lock.txt
```

Este comando se muestra para Miniforge Prompt con sintaxis CMD. No sustituya una redirección de texto por otra codificación sin comprobar que Conda pueda volver a leer el archivo.

### Antes del primer inicio nativo

Solicite o prepare la adaptación descrita en la sección 11 y complete las pruebas. Los scripts SH y la ruta actual de scripts/start.py no deben presentarse como un arranque nativo ya validado. Si se necesita ejecutar la entrega actual sin completar esa adaptación, utilice la alternativa WSL2 de la sección 12 o un servidor Linux existente.

## 5 Configurar las credenciales de los servicios

### Archivo central de secretos

Las variables se guardan en .env en la raíz del proyecto, al mismo nivel que config.yaml. Se editan en el equipo que ejecuta el servidor, no en la computadora de cada usuario del navegador. El backend las carga al iniciar.

En Windows nativo, abra .env con un editor de texto como Bloc de notas o Visual Studio Code. Guárdelo como texto UTF-8 sin BOM y con nombre exacto .env, no .env.txt. Active la visualización de extensiones en el Explorador. Si no existe, cree el archivo sin sobrescribir uno que ya tenga credenciales.

En la alternativa WSL2, puede editarlo desde Ubuntu:

```bash
cd ~/proyectos/CEMEC_plataforma
nano .env
```

Utilice este esquema. Los textos entre menor y mayor son marcadores: se sustituyen completamente por los valores reales, sin esos signos. No ponga espacios alrededor del signo igual.

```dotenv
FIRMS_MAP_KEY=<MAP_KEY_DE_NASA>
EUMETSAT_CONSUMER_KEY=<CONSUMER_KEY_DE_EUMETSAT>
EUMETSAT_CONSUMER_SECRET=<CONSUMER_SECRET_DE_EUMETSAT>
CDSE_CLIENT_ID=<CLIENT_ID_DE_CDSE>
CDSE_CLIENT_SECRET=<CLIENT_SECRET_DE_CDSE>
```

En Windows, restrinja el acceso al archivo desde sus propiedades de seguridad según la política institucional. En nano, guarde con Ctrl+O, confirme con Enter y salga con Ctrl+X. Solo en Ubuntu, puede restringir sus permisos con:

```bash
chmod 600 .env
```

El ejemplo distribuido .env.example puede no incluir las dos líneas CDSE: añádalas manualmente. No sobrescriba un .env existente con cp .env.example .env porque perdería su configuración. No agregue secretos a config.yaml, ui/basemaps.json, capturas ni reportes.

Después de modificar .env, detenga y reinicie CEMEC. Las variables exportadas en la terminal tienen prioridad sobre .env; si un valor antiguo persiste, revise esa configuración sin imprimir los secretos en pantalla.

### NASA FIRMS

Solicite una MAP_KEY en el portal oficial de FIRMS. Guárdela en FIRMS_MAP_KEY. La integración valida 32 caracteres alfanuméricos. En Administración > Ajustes también se puede introducir una clave para una tarea; esa entrada no modifica .env ni guarda una configuración permanente del servidor.

La clave permite consultar las detecciones disponibles mediante la API Area. La versión integra VIIRS S-NPP, NOAA-20 y NOAA-21, y MODIS. Cada solicitud a NASA admite hasta cinco días; la aplicación permite tareas de hasta 30 días dividiéndolas en bloques. Cambiar la clave no amplía la disponibilidad histórica del proveedor.

### EUMETSAT

Cree o utilice una cuenta en EUMETSAT Data Store. Revise la colección EO:EUM:DAT:0417 y la licencia Copernicus aplicable. La implementación usa Consumer Key y Consumer Secret con EUMDAC. Son diferentes del usuario y contraseña del portal y diferentes de CDSE.

Obtenga las credenciales en la sección de acceso API de su cuenta y colóquelas en las variables EUMETSAT. EUMDAC obtiene y renueva el token; no copie tokens temporales al código ni utilice curl con verificación HTTPS desactivada. Si el portal muestra una migración de autenticación, siga la documentación vigente y compruebe la compatibilidad del conector antes de cambiar el método.

Si el portal descarga pero la API responde 403, revise cuenta y licencia, vuelva a entrar específicamente en Data Store, pruebe un producto y repita la tarea. Ese error no prueba por sí solo que el usuario haya olvidado aceptar la licencia. La guía docs/recuperacion-sincronizacion.md describe el incidente verificado y su recuperación.

### Copernicus Data Space y Sentinel Hub

Las imágenes OLCI y los mosaicos Sentinel-2 utilizan un cliente OAuth de CDSE. En el Dashboard de Sentinel Hub de CDSE, abra User Settings y OAuth clients y registre un cliente. Copie su Client ID y Client Secret a CDSE_CLIENT_ID y CDSE_CLIENT_SECRET. Guarde el secreto cuando se muestre y revise sus permisos y vigencia.

Una cuenta del Copernicus Browser o una Consumer Key de EUMETSAT no sustituyen este cliente. El backend gestiona los tokens. Para que la descarga funcione, la cuenta debe tener acceso a Catalog, Process y las colecciones utilizadas, con cuota disponible. Consulte el panel del proveedor para consumo total y permisos.

### Esri

El fondo World Imagery configurado se consultó mediante acceso público anónimo. No hay una API key de Esri que pegar en esta versión. Su configuración y atribución se encuentran en ui/basemaps.json. La disponibilidad y las condiciones del servicio externo pueden cambiar; no se implementó una descarga de teselas para uso sin conexión.

## 6 Ajustes reproducibles y límites

Haga una copia de config.yaml antes de editarlo. Mantenga la indentación con espacios y reinicie después de cambiar parámetros del backend. Los campos descriptivos del catálogo original no regeneran datos ni geometrías.

| Ruta de configuración | Función |
|---|---|
| server.host y server.port | Dirección y puerto de escucha; por defecto 127.0.0.1 y 8000. HOST y PORT de la terminal tienen prioridad. |
| interface.layout | modern para la interfaz actual; legacy para la presentación anterior. |
| firms.enabled y eumetsat.enabled | Habilitan las integraciones térmicas; no crean una sincronización programada. |
| firms.bbox y eumetsat.bbox | Área de consulta como oeste, sur, este, norte en grados. No reconstruyen los límites institucionales. |
| firms.days | Valor de respaldo del backend; la tarea enviada desde el visor puede elegir otro período de 1 a 30 días, limitado por firms.max_days_per_sync. |
| eumetsat.max_days_per_sync | Máximo de la API local, actualmente 31; la interfaz ofrece 1, 3, 5, 10 y 30 días. |
| olci.enabled y sentinel2.enabled | Disponibilidad de las imágenes; requieren además credenciales CDSE. |
| sentinel2.max_image_side | Vista regional limitada a 1024 píxeles por lado. |
| sentinel2.catalog_cache_hours | Caché de catálogo durante 24 horas, incluidas búsquedas vacías. |
| sentinel2.max_new_mosaics_per_day | Seis intentos nuevos por día UTC compartidos por vistas generales y detalles de Sentinel-2. |
| sentinel2.detail_max_area_km2 | Máximo de 400 km² por detalle; también se limita a 30 km por lado y 1024 píxeles. |
| retention.mode | dry_run; solo inventario. Cambiarlo no habilita eliminación real. |

OLCI conserva su imagen general de aproximadamente 300 m nominales; su botón de detalle está retirado. El límite diario de Sentinel-2 no es una cuota global de todas las llamadas de CDSE ni limita las vistas generales OLCI. Los intentos fallidos de preparación de mosaicos también cuentan. Los resultados ya guardados siguen disponibles al alcanzar el límite local.

Si un texto heredado de Ajustes menciona SYNC_INTERVAL_MINUTES, no lo interprete como un programador operativo: esta versión no lo implementa.

Los nombres de variables de credenciales se documentan en config.yaml; sus valores se guardan exclusivamente en .env o en el entorno del proceso. La configuración del fondo Esri está en el JSON identificado por interface.basemaps; el adaptador lee ese archivo al preparar el JavaScript.

## 7 Abrir cerrar y volver a acceder

### Usuario de una instancia instalada

Abra la dirección facilitada por el responsable. Si es una instancia en otro equipo, use su URL; localhost no representa ese servidor remoto. No ejecute comandos de instalación ni introduzca claves personales para consultar datos ya publicados. Cerrar el navegador no detiene la instancia.

### Servidor local nativo Windows

La entrega actual aún requiere completar los ajustes de la sección 11. Esta edición no proporciona un comando de inicio que se haya comprobado en Windows nativo. Cuando la entrega adaptada esté aceptada, utilice el lanzador y el puerto que documente su responsable. No invente un archivo Start-CEMEC.bat ni intente ejecutar directamente los SH como si fueran lanzadores Windows.

### Servidor local en Linux o WSL2

Desde Ubuntu o Linux, dentro de la carpeta del proyecto:

```bash
PORT=8090 ./Start-CEMEC.sh
```

Abra http://localhost:8090 en el mismo equipo. Mantenga esa terminal abierta y pulse Ctrl+C para detener el servidor. Sin PORT se usa config.yaml, inicialmente 8000. Use el puerto anunciado en la terminal. El anexo WSL2 detalla la preparación.

No abra index.html con doble clic: cartografía PMTiles y API requieren HTTP. Después de cambiar .env, detenga y reinicie el servidor. No hay arranque automático instalado. Cambiar datos en el navegador tampoco crea una programación de actualizaciones.

### Puerto y acceso de red

Si el puerto está ocupado, identifique el proceso o elija otro y use la misma dirección en el navegador. Para una instalación WSL2, localhost permite normalmente acceder desde Windows; los problemas de VPN o firewall se revisan con TI. No amplíe la escucha a 0.0.0.0 como primer remedio. La publicación institucional requiere revisar red y permisos por separado.

## 8 Verificación y puesta en servicio

### Integridad y entorno

La verificación de originales se puede preparar desde el entorno nativo Windows con Conda, sin afirmar todavía que los conectores estén listos:

```cmd
cd /d C:\CEMEC\CEMEC_plataforma
conda run --prefix .\.conda-env python scripts/replicate.py --verify-only
```

En Linux o WSL2, dentro del proyecto:

```bash
.conda-env/bin/python scripts/replicate.py --verify-only
.conda-env/bin/python --version
.conda-env/bin/node --version
```

Una vez que el servidor de la modalidad elegida esté iniciado, puede consultar su estado desde PowerShell en Windows:

```powershell
Invoke-RestMethod -Uri http://localhost:8090/api/status
Invoke-RestMethod -Uri http://localhost:8090/api/olci/status
Invoke-RestMethod -Uri http://localhost:8090/api/sentinel2/status
```

Sustituya localhost y el puerto si la instancia está en otro servidor. Estas consultas informan estados; no inician una sincronización ni preparan una imagen.

La comprobación de integridad debe confirmar 1.127 archivos originales, 66.582 detecciones originales y 117 territorios. No confunda ese resultado con el catálogo operativo servido por el backend, que puede tener más registros. La API de estado informa configuración y trabajos, no valores de credenciales.

### Interpretar el estado

configured true significa que existen variables y que el servicio está habilitado; no valida por sí solo la contraseña, licencia, cuota o acceso remoto. Una prueba funcional exige una consulta y puede consumir recursos.

### Prueba funcional controlada

Abra el visor y confirme cartografía, filtros y Datos. Luego haga una sincronización FIRMS de un día y una EUMETSAT de un día, si las credenciales y el alcance lo permiten. Espere a cada resultado y revise historial, período, productos, registros en el área y duplicados. Una consulta sin puntos puede ser correcta.

Para CDSE prepare una única imagen OLCI y un mosaico publicado, revise metadatos y repita la misma selección para comprobar reutilización. No precargue todos los trimestres. Seleccione Esri, verifique su atribución y vuelva a CEMEC. Esri no consume PU de CDSE.

### Pruebas automatizadas opcionales

```bash
.conda-env/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Estas pruebas usan datos controlados y no sustituyen una prueba real de acceso a los proveedores. Las pruebas visuales necesitan Chrome y Playwright, son opcionales para servir la aplicación y no se deben dar por instaladas en un equipo nuevo. El comando de pruebas mostrado utiliza la terminal Linux o WSL2; una aceptación nativa se ejecuta en su propio entorno Windows.

## 9 Respaldos mantenimiento y traslado

### Respaldo completo

Detenga el servidor y copie por separado: código y configuración; origen; sitio extraído o sus insumos; runtime íntegro; respaldos existentes; y una copia privada y protegida de .env. Conserve environment.yml, el lock recibido y el lock instalado. Guarde una copia externa al mismo disco y registre fecha, versión, totales y hashes.

Los archivos codigo.tar.gz de respaldos protegen cambios de código, pero no sustituyen un respaldo de los datos activos ni de las credenciales. Para restaurar un respaldo de código, compruebe su SHA-256 contra manifest.json, extraiga con filtro data en una carpeta separada y revise las rutas antes de sustituirlas con el servidor detenido. No sobrescriba runtime con una versión incompleta.

### Recuperar en otra carpeta o equipo

Restaure una entrega coherente; reinstale .conda-env en su nueva ubicación; configure .env de forma privada; compruebe integridad; inicie y compare catálogo, filtros, imágenes guardadas y exportaciones con el registro del respaldo. No mueva el entorno Conda ya instalado y suponga que sus rutas siguen funcionando.

### Crecimiento y retención

En un entorno nativo Windows preparado, el inventario puede comprobarse mediante Conda; esa comprobación no inicia los conectores:

```cmd
conda run --prefix .\.conda-env python scripts/retention.py
```

En Linux o WSL2:

```bash
.conda-env/bin/python scripts/retention.py
```

El informe runtime/retention/latest-plan.json lista candidatos y protecciones. La herramienta actual no elimina archivos ni instala una tarea automática. La política propone imágenes sin uso durante 30 días, temporales conocidos tras 24 horas, snapshots tras 30 días con protección del activo, tres anteriores y sus referencias, y tareas terminadas tras 90 días.

No borre snapshots, datos originales o active.json para liberar espacio. Las referencias pueden ser transitivas. Las cachés EUMETSAT, respaldos y evidencias están fuera de esa limpieza. Activar eliminación real requiere desarrollar y verificar la ejecución segura; no basta con cambiar dry_run.

### Otros territorios

Cambiar bbox permite consultar otra extensión, pero no reconstruye municipios, áreas protegidas, cartografía PMTiles ni estadísticas. Una réplica institucional para otra región necesita geometrías compatibles, regeneración consistente de productos y una validación territorial. Parte del frontend original sigue integrado mediante adaptadores sobre una compilación; una compilación distinta puede requerir adaptar esos puntos.

## 10 Solución de problemas

| Síntoma | Comprobación y solución |
|---|---|
| Solo necesito consultar y me piden WSL | Solicitar la URL de una instancia ya instalada. WSL2 no es requisito del usuario del navegador. |
| Quiero ejecutar todo en Windows nativo | Revisar la preparación de la sección 4 y los ajustes pendientes de la sección 11. |
| WSL no se instala en la modalidad alternativa | Revisar versión de Windows, permisos, virtualización y reinicio con TI. No afecta al acceso por navegador a una instancia externa. |
| conda no se reconoce | En Windows nativo usar Miniforge Prompt; en WSL abrir Ubuntu con Conda de Linux inicializado. No mezclar consolas. |
| Permission denied en la alternativa Linux | Ejecutar chmod +x sobre los dos scripts dentro de Ubuntu. No usar ese comando en Windows nativo. |
| bad interpreter con caracteres CR | El archivo fue convertido a finales de línea Windows. Recuperar la copia con LF o convertir una copia controlada; verificar los scripts originales. |
| Falta entorno Conda | Comprobar la instalación de su modalidad: .conda-env de Windows y de Linux tienen estructura y binarios distintos. |
| Setup avisa de hash distinto | Detener el proceso de instalación y comparar con una entrega íntegra. No forzar sobrescritura ni cambiar el manifiesto para ocultarlo. |
| No abre la dirección | Comprobar si la instancia es local o remota, puerto anunciado y estado del servidor; revisar WSL solo si se utiliza esa modalidad. |
| Página antigua tras cambios | Usar Ctrl+F5. Si cambió código del adaptador o secretos, reiniciar además el servidor. |
| Mapa vacío o error WebGL | Probar navegador actualizado, aceleración gráfica y carga HTTP. No abrir index.html directamente. |
| Falta configurar CDSE | Añadir las dos variables CDSE a .env, habilitar la integración y reiniciar. |
| 400 o 401 remoto | Revisar servicio, credenciales, expiración y reloj; no intercambiar Consumer Key con Client ID. |
| 403 EUMETSAT | Revisar cuenta/licencia y acceso real en Data Store; seguir la guía de recuperación sin asumir una causa única. |
| 429 o límite local de mosaicos | Esperar; consultar cuota del proveedor; reutilizar imágenes guardadas. No aumentar límites sin revisar consumo. |
| Sin datos después de sincronizar | Revisar tarea, período, área, fuente, instrumento y duplicados. Cero filas no demuestra ausencia de fuego. |
| Un cambio en .env no se refleja | Reiniciar y comprobar si la terminal ya exporta una variable con el mismo nombre. |
| Esri no carga | El visor vuelve a CEMEC; comprobar Internet y servicio y reintentar desde Capas del mapa. |

Para solicitar soporte registre fecha y hora UTC, identificador y estado de tarea, proveedor, territorio, período y mensaje. Adjunte metadatos y versiones cuando correspondan. No adjunte .env, tokens ni capturas de secretos.

## 11 Ajustes pendientes para Windows nativo

La aplicación original fue creada para Windows y el visor se ejecuta en el navegador. La adaptación a Ubuntu permitió reutilizar esa interfaz. Los conectores y mecanismos añadidos posteriormente requieren una revisión específica antes de declarar una entrega nativa de Windows lista para uso.

### Trabajo técnico identificado

| Componente | Ajuste que se debe completar |
|---|---|
| Arranque | Adaptar o proporcionar un lanzador Windows y resolver correctamente python.exe y node.exe dentro del entorno Conda. Los SH incluidos corresponden a Linux. |
| Bloqueos de archivos | Los motores de imágenes importan fcntl, disponible en Unix. Sustituir ese mecanismo por uno compatible con Windows conservando exclusión entre procesos y protección del presupuesto. |
| Dependencias y datos | Resolver environment.yml en win-64, registrar un lock propio y verificar rutas, escritura atómica, certificados, cierre de procesos y referencias de los snapshots. |
| Aceptación | Probar servidor, mapa, sincronizaciones, imágenes, caché, exportaciones y reinicio en un Windows real. |

Estos son ajustes localizados de portabilidad, no una necesidad de rehacer el visor completo. Su existencia tampoco significa que una persona usuaria de Windows vaya a encontrar todos esos problemas: se resuelven antes de entregarle una instalación local.

Esta revisión modifica los manuales, no realiza esa adaptación del código. Instalar Conda y crear el entorno no resuelve por sí solo un import de fcntl ni una ruta de ejecutable específica de Linux. Hasta completar y aceptar esos cambios, se puede utilizar una instancia existente o la alternativa WSL2.

## 12 Alternativa con WSL2 y Ubuntu

### Instalar WSL2 y Ubuntu

Abra PowerShell como administrador. La guía utiliza Ubuntu 24.04 como distribución concreta; compruebe antes que esté disponible.

```powershell
wsl --list --online
wsl --install -d Ubuntu-24.04
```

Reinicie Windows si se solicita. Abra Ubuntu 24.04 desde Inicio y cree un usuario y una contraseña de Linux. Al escribir la contraseña puede no aparecer ningún carácter: es normal. Esta cuenta es diferente de las cuentas NASA, EUMETSAT y CDSE.

### Comprobar la versión de WSL

En PowerShell:

```powershell
wsl --list --verbose
```

La fila Ubuntu-24.04 debe indicar versión 2. Si indica 1, conviértala con el siguiente comando y espere a que termine:

```powershell
wsl --set-version Ubuntu-24.04 2
```

Si Windows indica que falta virtualización, revisar UEFI o BIOS y Virtual Machine Platform con TI. Si no se encuentra la distribución, usar exactamente el nombre devuelto por wsl --list --online. No desinstalar ni anular el registro de una distribución que ya contiene trabajo.

### Preparar Ubuntu

Abra la terminal Ubuntu y ejecute:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl unzip rsync nano
uname -m
```

Para el lock distribuido se espera x86_64. No se necesita instalar un escritorio completo de Ubuntu. Los pasos oficiales de Microsoft y Ubuntu se enlazan al final del manual.

### Conda de Linux dentro de Ubuntu

Utilice una instalación de Conda para Linux dentro de WSL. Una instalación de Anaconda o Miniconda de Windows no sustituye esta dependencia. Si ya tiene Conda funcional en Ubuntu, puede conservarlo y comprobar con conda --version.

### Instalación con Miniforge

Descargue desde el proyecto oficial de conda-forge la versión Linux x86_64 de Miniforge. El siguiente ejemplo fija la versión 26.7.2-0, cuya publicación oficial se comprobó al preparar el manual. Conserve el instalador, su versión y su hash; si adopta otra publicación, actualice ambos archivos y valide el entorno.

```bash
mkdir -p ~/instaladores
cd ~/instaladores
miniforge_version=26.7.2-0
miniforge_release=https://github.com/conda-forge/miniforge/releases/download
miniforge_file=Miniforge3-${miniforge_version}-Linux-x86_64.sh
curl -fLO "${miniforge_release}/${miniforge_version}/${miniforge_file}"
curl -fLO "${miniforge_release}/${miniforge_version}/${miniforge_file}.sha256"
sha256sum -c "${miniforge_file}.sha256"
bash "${miniforge_file}"
```

Continúe solo si el checksum coincide. Si el nombre del archivo de checksum cambia, descárguelo desde la misma publicación oficial y verifique allí el nombre; no omita la comprobación ni utilice un hash de otra versión.

Acepte o seleccione la ruta de instalación propuesta, por ejemplo ~/miniforge3. Permita inicializar Conda para Bash. Cierre y vuelva a abrir Ubuntu. Después compruebe:

```bash
conda --version
```

Si no se encuentra Conda y se instaló en la ruta anterior:

```bash
source ~/miniforge3/etc/profile.d/conda.sh
conda init bash
```

Vuelva a abrir Ubuntu. No instale los paquetes de CEMEC en Conda base; Setup creará su entorno dedicado.

### Copiar e instalar la versión actual en WSL2

### Paso 1 Preparar la entrega

Descomprima la entrega en Windows, por ejemplo en C:\CEMEC\entrega. Esa carpeta debe contener config.yaml directamente, junto a los scripts, ui y origen. Si existe una carpeta adicional dentro del ZIP, ajuste la ruta hasta llegar a ella.

En Ubuntu copie el proyecto al sistema de archivos Linux. Evite ejecutarlo directamente en una carpeta sincronizada con OneDrive o en un disco extraíble.

```bash
mkdir -p ~/proyectos/CEMEC_plataforma
rsync -a --exclude='.conda-env' --exclude='.conda-pkgs' \
  --exclude='.env' --exclude='__pycache__' \
  /mnt/c/CEMEC/entrega/ ~/proyectos/CEMEC_plataforma/
cd ~/proyectos/CEMEC_plataforma
ls config.yaml Setup-CEMEC.sh Start-CEMEC.sh ui origen
```

La barra final en entrega/ copia su contenido. Este comando incluye runtime si forma parte de la entrega. Para una instalación inicial, use una entrega preparada sin datos operativos. No copie una colección operativa incompleta ni mezcle snapshots de entregas distintas.

### Paso 2 Ejecutar Setup

Conserve una copia del lock recibido antes de instalar: Setup vuelve a escribir environment-linux-64.lock.txt con los paquetes efectivamente instalados.

```bash
cp environment-linux-64.lock.txt environment-linux-64.recibido.txt
chmod +x Setup-CEMEC.sh Start-CEMEC.sh
./Setup-CEMEC.sh
```

El instalador crea .conda-env, verifica las entradas originales y extrae los archivos que falten. Si encuentra un original modificado, se detiene para no sobrescribirlo. No solucione ese aviso borrando la carpeta; revise la entrega y el respaldo.

El entorno declara Python 3.12, Node.js 22, PyYAML 6.0, Shapely 2.1, NumPy 2, PyArrow 23 y EUMDAC 3.1.1. Los módulos del frontend están compilados: no ejecute npm install. La primera instalación requiere Internet y puede tardar según el equipo y la red.

### Reproducción exacta opcional

Solo en Linux x86_64, incluyendo Ubuntu WSL2 x86_64, puede crear el entorno desde el lock recibido antes de ejecutar Setup:

```bash
CONDA_PKGS_DIRS="$PWD/.conda-pkgs" conda create \
  --prefix "$PWD/.conda-env" \
  --file environment-linux-64.recibido.txt --yes
./Setup-CEMEC.sh
```

Esta es una alternativa a la creación inicial desde environment.yml, no un paso que se deba repetir sobre un entorno ya creado. En otra arquitectura se resuelven las dependencias desde environment.yml y se valida el resultado.

### Iniciar desde Ubuntu

```bash
cd ~/proyectos/CEMEC_plataforma
PORT=8090 ./Start-CEMEC.sh
```

Abra http://localhost:8090 en el navegador de Windows. La instalación de WSL2 y la comprobación de acceso deben validarse en el equipo de destino; la aplicación se ha probado en Linux. Esta alternativa no es necesaria para una persona que solo consulta una instancia instalada ni constituye un requisito de una futura entrega nativa Windows.

## 13 Lista de aceptación por modalidad

### Usuario que solo consulta

- Dispone de la dirección correcta y puede abrirla desde el navegador de Windows.
- Visualiza mapa y filtros y puede consultar datos y generar o descargar los productos habilitados.
- Sabe a quién informar un fallo de actualización y no necesita las credenciales del servidor.

### Responsable de una instalación local

- Ha identificado modalidad, sistema, arquitectura y versión de la entrega.
- Conserva originales, configuración y un entorno Conda propio del sistema.
- Si utiliza Windows nativo, ha completado los ajustes de la sección 11; no confunde preparación con aceptación final.
- El servidor inicia y termina correctamente y se accede desde el navegador.
- La integridad y referencias de datos se han comprobado.
- Credenciales propias configuradas fuera del código y documentación.
- Consultas, errores, vacíos y duplicados revisados; imágenes, caché y exportaciones probadas.
- Existe respaldo completo y procedimiento de recuperación con responsable asignado.

Esta lista se completa en el equipo de destino. No afirma que se haya probado Windows nativo o WSL2 durante esta revisión. Una instancia pública necesita además autenticación y permisos para administración, HTTPS, protección de secretos, límites de acceso y seguimiento operativo; el menú Administración no sustituye esos controles.

## 14 Referencias y documentación de apoyo

Documentación del proyecto: README.md; docs/README.md; docs/recuperacion-sincronizacion.md; docs/retencion.md; docs/olci-visor.md; docs/mosaicos-sentinel2.md; docs/detalle-mosaico.md; docs/fondo-esri.md. Los registros de validación describen pruebas concretas y no una garantía universal de disponibilidad.

Fuentes externas consultadas el 19 de octubre de 2026:

- Microsoft, instalación de WSL: https://learn.microsoft.com/en-us/windows/wsl/install
- Microsoft, red y localhost en WSL: https://learn.microsoft.com/en-us/windows/wsl/networking
- Ubuntu, instalación en WSL2: https://ubuntu.com/wsl/docs/latest/howto/install-ubuntu-wsl2/
- conda-forge, instaladores Windows y Linux: https://conda-forge.org/download/
- Python, disponibilidad Unix de fcntl: https://docs.python.org/3.12/library/fcntl.html
- Miniforge, distribución e instalación: https://github.com/conda-forge/miniforge
- NASA FIRMS, API Area y solicitud de MAP_KEY: https://firms.modaps.eosdis.nasa.gov/api/area/
- EUMETSAT Data Store: https://data.eumetsat.int/product/EO:EUM:DAT:0417
- CDSE, autenticación de Sentinel Hub: https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Overview/Authentication.html
- Esri World Imagery y condiciones: https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9

Los portales y sus procedimientos pueden cambiar. Use la documentación oficial al actualizar cuentas, autenticación y dependencias; verifique después las funciones de CEMEC que dependan del cambio.
