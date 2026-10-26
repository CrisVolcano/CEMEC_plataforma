# Discrepancia entre licencia activa y descarga EUMETSAT

**Estado actualizado: acceso restablecido y descarga API verificada el 12 de
octubre de 2026.** Después de iniciar sesión y descargar un producto desde el
Data Store, el usuario volvió a tener acceso por API. Se descargó también por API
el mismo producto aportado como ZIP. La sincronización completa procesó 9 productos
y 72 detecciones, todas fuera del área configurada. No se ha determinado la causa
interna del rechazo previo; el diagnóstico siguiente registra las pruebas del
incidente, ya resuelto.

Comprobación: 12 de octubre de 2026. Este documento no contiene claves, secretos
ni tokens y puede compartirse con soporte EUMETSAT.

La captura aportada por el usuario muestra **Copernicus: active**, con inicio
**8 Oct 2026** y fin **N/A**. El usuario confirmó que la cuenta del portal tiene
el identificador **crisvolcano** y que las credenciales son las mismas que usó
anteriormente para descargar los CSV del notebook.

La colección consultada es **EO:EUM:DAT:0417**, Sentinel-3 SLSTR L2 FRP NRT.
Se comprobó lo siguiente:

- OAuth `POST https://api.eumetsat.int/token`: HTTP 200.
- Información de usuario `GET https://api.eumetsat.int/epcs/user_info`:
  HTTP 200, `username: crisvolcano`.
- Catálogo: 9 productos encontrados para el área de Petén y los últimos 3 días.
- Metadatos del producto en la API de descarga: HTTP 200.
- CSV `FRP_MWIR1km_standard.csv`: HTTP 403.
- Producto completo: HTTP 403.

Respuesta del servicio de descarga:

```text
Copernicus license required to access this collection
```

Se reprodujo la descarga usando directamente EUMDAC 3.1.1, fuera del código del
conector del visor, sobre un producto del 8 de octubre cuyo CSV ya existe en la
carpeta del notebook. También se reprodujo con llamadas HTTP directas utilizando
Bearer en el encabezado y el mecanismo de token en el parámetro de acceso.
La clave y el secreto del visor coinciden con los incluidos en el cURL compartido
por el usuario; los valores utilizados dentro del notebook no se guardaron allí.

Se revocó y volvió a obtener el token para descartar su estado anterior. Hubo una
respuesta transitoria HTTP 401 usando un token invalidado devuelto durante la
renovación; las peticiones posteriores con el token recién obtenido continuaron
devolviendo HTTP 403. No se modificaron la Consumer Key ni el Consumer Secret.

El notebook conserva 9 CSV previamente descargados, con 36 detecciones legibles.
Su existencia confirma descargas anteriores exitosas; reutilizar esos archivos
locales no comprueba que una descarga nueva esté actualmente autorizada.

## Solicitud sugerida a soporte

La cuenta `crisvolcano` muestra la licencia Copernicus activa desde el 8 de octubre
de 2026, sin vencimiento. OAuth y el catálogo funcionan, pero las descargas de la
colección `EO:EUM:DAT:0417` devuelven HTTP 403 con “Copernicus license required to
access this collection”, tanto al solicitar el CSV estándar como el producto
completo. El problema persiste con un token renovado y se reproduce con EUMDAC y
HTTP directo. Por favor, revisar la asociación y evaluación de la licencia de
esta cuenta en el servicio de descarga/API.

Referencia: [FAQ oficial del Data Store](https://user.eumetsat.int/resources/user-guides/frequently-asked-questions-for-data-store).
