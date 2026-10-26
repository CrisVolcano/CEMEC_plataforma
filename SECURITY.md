# Credenciales y reporte de problemas

Las credenciales de FIRMS, EUMETSAT y CDSE se configuran en el servidor mediante `.env` o variables de entorno. El archivo `.env.example` contiene únicamente nombres y valores vacíos. Los visitantes no necesitan recibir esas claves.

Si se detecta una credencial en un archivo preparado para Git, detener la publicación, retirar el archivo del índice y revocar o cambiar la credencial si se compartió. Quitarla del último archivo no la elimina de un historial ya publicado. [Guía de GitHub](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).

No incluir claves, tokens o datos sensibles en issues públicos. Informar al responsable del repositorio por el canal institucional acordado; no se configura aquí una dirección de contacto sin confirmar.

La versión actual está preparada para ejecución local. Publicar el código en GitHub no despliega la aplicación ni añade autenticación. Para alojar el servicio operativo se requiere revisar acceso a las rutas administrativas, HTTPS y configuración del servidor. No activar GitHub Pages como sustituto del backend Python/Node.
