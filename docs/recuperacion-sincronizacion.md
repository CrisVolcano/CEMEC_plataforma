# Recuperar la sincronización de CEMEC

Revisado el 12 de octubre de 2026. Aplica a la integración actual de EUMETSAT /
Sentinel-3 y NASA FIRMS. La sincronización se inicia manualmente desde Ajustes.

Esta guía permite repetir el diagnóstico sin depender de esta conversación.
Para mantenimiento del almacenamiento consulta la [política de retención](retencion.md):
el catálogo activo y todas sus referencias se protegen; todavía no hay borrado automático.
La disponibilidad del servicio externo puede variar; estos pasos no garantizan
que EUMETSAT o NASA estén disponibles en todo momento.

## 1. Revisar el estado antes de intervenir

Abre **http://localhost:8090 → Ajustes → Historial de tareas** y revisa la tarea
más reciente del proveedor que estás consultando. Una tarea fallida antigua
permanece como evidencia aunque las siguientes hayan terminado correctamente.

Anota el identificador, fecha/hora, estado, etapa y mensaje. Si está pendiente o
en ejecución, deja que termine. El backend procesa una sola tarea a la vez.

Para comprobar el servicio local, ejecuta desde la carpeta del proyecto:

```bash
curl --fail --silent --show-error http://127.0.0.1:8090/api/status
```

La respuesta contiene estados e historial; no contiene claves ni tokens. Para
consultar una tarea concreta, reemplaza `ID_DE_TAREA` por su identificador:

```bash
curl --fail --silent --show-error http://127.0.0.1:8090/api/jobs/ID_DE_TAREA
```

Si usas otro puerto, reemplaza `8090` en las direcciones y comandos de esta guía.

## 2. Distinguir un fallo de una consulta vacía

| Resultado | Interpretación y siguiente paso |
| --- | --- |
| `status: completed`, `complete: true`, `products_processed == products_found` | La consulta EUMETSAT terminó. Revisar conteos y filtros. |
| `products_found: 0` | No hubo productos disponibles para ese área/periodo. Comprobar fechas, cobertura y disponibilidad del archivo. |
| `received > 0`, `in_area: 0`, `outside_bbox == received` | Los productos contienen detecciones, todas fuera del rectángulo configurado. No es un fallo de conexión. |
| `in_area > 0`, `added: 0`, `duplicates > 0` | Las observaciones ya estaban incorporadas. No se deben duplicar. |
| `published: false` en una tarea completada | No fue necesario generar un snapshot nuevo; la consulta puede haber sido correcta. |
| `status: failed` o `complete: false` | La actualización quedó incompleta. Revisar el error; no interpretar los conteos parciales como una consulta completa. |

Una consulta vacía no demuestra ausencia de incendios. El corte del catálogo
(`date_max`) corresponde a la última observación incorporada y puede ser anterior
a la última sincronización exitosa, si esa consulta no agregó observaciones.

Para revisar datos Sentinel-3 en el visor, selecciona **Origen: EUMETSAT**,
**Instrumento: SLSTR**, fechas de la consulta, todos los satélites y confianza
**Todas**. Revisa también territorio y filtro día/noche. Si existe, **Área de
consulta EUMETSAT** muestra el rectángulo consultado; no es un límite legal.

## 3. Recuperar un HTTP 403 de EUMETSAT

El servicio puede responder:

```text
Copernicus license required to access this collection
```

Ese texto no prueba por sí solo que falte aceptar la licencia. En el incidente
del 12 de octubre, la licencia ya figuraba activa desde el 8 de octubre.

Sigue esta secuencia:

1. Entra en [EUMETSAT User Portal](https://user.eumetsat.int) y verifica que
   **My data licences → Copernicus** figure activa y vigente.
2. Entra específicamente en [EUMETSAT Data Store](https://data.eumetsat.int).
   Cierra sesión allí y vuelve a iniciar sesión con la misma cuenta. El acceso al
   User Portal o a API Key Management no sustituye esta comprobación en Data Store.
3. Abre la [colección `EO:EUM:DAT:0417`](https://data.eumetsat.int/product/EO:EUM:DAT:0417)
   e intenta descargar un producto reciente.
4. En el visor, vuelve a pulsar **Sincronizar Sentinel-3**. La tarea nueva obtiene
   el token mediante EUMDAC; no hace falta pegar un token temporal en la aplicación.
5. Confirma que la nueva tarea termina y procesa todos los productos encontrados.

Si acabas de habilitar o modificar una licencia, EUMETSAT indica que debe hacerse
un nuevo inicio de sesión y que la actualización puede tardar hasta una hora.
Esta espera aplica a cambios recientes, no explica por sí sola un rechazo de una
licencia activa desde días anteriores. Véase la
[FAQ oficial del Data Store](https://user.eumetsat.int/resources/user-guides/frequently-asked-questions-for-data-store).

Si el portal permite descargar y la API sigue rechazando:

- Compara la Consumer Key de API Key Management con la configuración privada del
  servidor y verifica que pertenezcan a la misma cuenta. No copies los valores en
  capturas, tickets o registros compartidos.
- Reinicia CEMEC para descartar un proceso que conserve una configuración antigua
  y repite la sincronización una vez.
- Si persiste, documenta el producto concreto que descarga en el portal y falla
  en la API, su colección, la hora UTC y el mensaje. Solicita a EUMETSAT revisar
  la asociación de licencia y autorización de esa cuenta en la API.

Si tampoco descarga desde el portal, revisa el acceso de la cuenta y el estado
del servicio con EUMETSAT antes de modificar el conector local.

La página API Key Management puede mostrar un aviso de migración. Abre su enlace
y revisa la [guía oficial de autenticación](https://user.eumetsat.int/resources/user-guides/introductory-data-store-user-guide#ID-Authentication-and-login).
La sección compartida durante este incidente utilizaba `eumdac.AccessToken`, el
método implementado por CEMEC. El aviso no confirmó una necesidad de cambiar las
credenciales ni demostró la causa del HTTP 403.

## 4. Otros errores y acciones

| Señal | Acción |
| --- | --- |
| HTTP 401 / `authentication_failed` | Reintentar una vez. Verificar las credenciales privadas, su vigencia y posibles cambios de cuenta. Si se modificó `.env`, reiniciar CEMEC. |
| HTTP 403 sin mensaje de Copernicus | Revisar acceso al producto y cuenta; conservar el diagnóstico exacto para soporte. |
| HTTP 404 del servicio remoto | Verificar que el producto siga disponible. Repetir la consulta para obtener el catálogo actual; no reutilizar un identificador retirado. |
| HTTP 429 | Dejar que actúen los reintentos del cliente. Evitar iniciar varias consultas; si la tarea falla, esperar antes de repetir. |
| HTTP 5xx / timeout / error de conexión | Comprobar conexión y estado del proveedor. Reintentar después de recuperar el servicio. |
| HTTP 409 del visor | Ya hay una tarea en ejecución. Esperar y revisar el historial; no reiniciar para forzar una segunda tarea. |
| Credenciales no configuradas / botón deshabilitado | Verificar `eumetsat.enabled`, variables de credenciales, estado ocupado y configuración cargada por el servidor. |
| CSV no reconocido, incompleto o conteo incoherente | Guardar el archivo original y el manifiesto. Revisar cambios de formato antes de adaptar el lector; no tratar el fallo como cero detecciones. |
| Falta CSV MWIR estándar / búsqueda incompleta | Consultar el manifiesto y disponibilidad del producto. Reintentar; revisar el formato si el problema persiste. |
| Tarea interrumpida al apagar CEMEC | Reiniciar y repetir la consulta. Los CSV válidos guardados se reutilizan. |
| Espacio en disco insuficiente | Liberar espacio o ampliar almacenamiento conservando originales, datos activos y evidencia del error; después reintentar. |

EUMDAC gestiona la renovación de tokens, reintentos y restricciones del servicio.
El conector usa HTTPS con verificación de certificados. La revocación manual de
tokens no es un paso rutinario de recuperación: no resolvió el HTTP 403 de este
incidente y puede invalidar sesiones API que estén usando ese mismo token.

## 5. Reiniciar con la configuración correcta

Detén el proceso de CEMEC con **Ctrl+C** en su terminal y vuelve a iniciarlo:

```bash
PORT=8090 ./Start-CEMEC.sh
```

Si faltan dependencias, ejecuta `./Setup-CEMEC.sh` y después el lanzador. El entorno
dedicado se encuentra en `.conda-env`; la especificación y el lock están en
`environment.yml` y `environment-linux-64.lock.txt`.

Las variables predeterminadas son `EUMETSAT_CONSUMER_KEY` y
`EUMETSAT_CONSUMER_SECRET`. Se cargan desde `.env`; variables ya exportadas en la
terminal tienen prioridad. Si deseas utilizar exclusivamente los valores de
`.env`, elimina esas variables heredadas antes de iniciar:

```bash
unset EUMETSAT_CONSUMER_KEY EUMETSAT_CONSUMER_SECRET
PORT=8090 ./Start-CEMEC.sh
```

Recarga el visor con **Ctrl+F5** tras actualizar el código. Ninguno de estos pasos
requiere borrar los datos descargados ni el catálogo histórico.

## 6. Archivos que permiten auditar y repetir

Rutas predeterminadas relativas a la carpeta del proyecto:

| Archivo o carpeta | Uso |
| --- | --- |
| `config.yaml` | Colección, área, días, variante, reintentos y nombres de variables. |
| `.env` | Credenciales privadas del servidor; excluir de materiales compartidos. |
| `runtime/firms/jobs/{id}.json` | Estado, progreso, resultados y error de cada tarea de ambos proveedores. |
| `runtime/firms/downloads/{id}/eumetsat.json` | Manifiesto de la consulta EUMETSAT, conteos y productos procesados. |
| `runtime/eumetsat/products/` | CSV originales, metadatos de descarga y SHA-256 para comprobar la caché. |
| `runtime/firms/active.json` | Catálogo activo y última sincronización exitosa de cada proveedor. |
| `runtime/firms/snapshots/` | Datos publicados en JSON, estadísticas y GeoParquet. |
| `origen/eumetsat/` | ZIP manual aportado por el usuario, conservado sin modificaciones. |
| `docs/validacion-eumetsat.json` | Evidencia de pruebas y sincronización real. |
| `docs/diagnostico-eumetsat-403.md` | Registro del incidente de acceso, ya resuelto, y modelo de consulta a soporte. |

Las rutas de almacenamiento pueden cambiar mediante `config.yaml`. El backend
publica el catálogo nuevo después de preparar el snapshot completo. Si una
descarga, validación o escritura falla antes de publicar, conserva el catálogo
activo anterior. No elimines `active.json`, snapshots ni originales para intentar
resolver un problema de autenticación.

Antes de mover el proyecto o hacer limpieza, respalda los originales, configuración,
datos activos y sus snapshots. Conserva las credenciales por separado y protegidas.

## 7. NASA FIRMS

Si el fallo afecta a FIRMS, usa la sección **Conexión NASA FIRMS** y su última
tarea. Verifica `FIRMS_MAP_KEY` y el producto configurado. Los pasos de licencia e
inicio de sesión en EUMETSAT corresponden únicamente a Sentinel-3.

El backend FIRMS acepta tareas de 1 a 30 días y divide cada producto en bloques consecutivos de hasta 5 días, con fecha inicial explícita para ventanas largas. Los CSV y sus hashes quedan registrados por bloque; no se publica una integración parcial si falla una descarga. Un error de clave/cuota o una
respuesta que no sea CSV válido se registra como fallo y conserva los datos
publicados. Si cambias `FIRMS_MAP_KEY` en `.env`, reinicia CEMEC; las variables
exportadas de la terminal también tienen prioridad sobre ese archivo.

## 8. Incidente de referencia y criterio de cierre

El 12 de octubre de 2026 se observó:

1. Licencia Copernicus activa, identidad API correcta y búsquedas exitosas.
2. HTTP 403 al descargar CSV y producto completo, incluso con token renovado.
3. Descarga exitosa desde el Data Store tras el acceso del usuario al portal.
4. Descarga exitosa por API del mismo producto y sincronización completa:
   **9 productos, 72 detecciones, 72 fuera del área y 0 añadidas**.

Se considera restablecido el acceso cuando una descarga nueva por API funciona y
la tarea del visor termina completa. Un token válido, un catálogo accesible o un
CSV ya existente en la caché no verifican por sí solos una descarga nueva.

La secuencia anterior es una recuperación observada. No se ha confirmado la causa
interna del rechazo inicial ni que se requiera iniciar sesión manualmente antes de
cada sincronización. Si se repite el fallo, registra la recurrencia y sigue esta
guía para distinguir sus causas posibles.
