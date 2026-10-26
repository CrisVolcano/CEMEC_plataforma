# Entrega de CEMEC Plataforma

**Si descargaste el proyecto desde GitHub:** sigue primero el [README](README.md). Este documento describe las entregas ZIP, que pueden incluir originales y respaldos ausentes del repositorio.

Esta carpeta contiene la aplicación, su configuración, los manuales, los datos
originales, el catálogo actualizado incluido en la entrega y los respaldos de
recuperación. Empiece por `docs/manuales/manual-instalacion.pdf` y después consulte
`docs/manuales/manual-uso.pdf`. También se incluyen las versiones Word y Markdown.

## Instalar y abrir

1. Extraiga **todo** el ZIP en una carpeta nueva y de su propiedad. No ejecute
   archivos dentro del comprimido ni lo extraiga encima de una instalación activa.
2. Consulte el manual de instalación para instalar Conda y preparar el equipo.
   El entorno dedicado se reconstruye desde `environment.yml`; no se distribuyen
   el entorno del equipo de origen ni su caché de paquetes. Hace falta Internet
   para instalar las dependencias. El lock exacto incluido corresponde a Linux.
3. En Ubuntu/Linux, desde la carpeta extraída y con Conda disponible, ejecute:

   ```bash
   chmod +x Setup-CEMEC.sh Start-CEMEC.sh
   ./Setup-CEMEC.sh
   PORT=8090 ./Start-CEMEC.sh
   ```

4. Abra **http://localhost:8090**. Mantenga la terminal abierta; Ctrl+C detiene
   el servidor. El puerto predeterminado sin la variable PORT es 8000.
5. Para ver las detecciones incluidas, elija un período dentro de la cobertura
   indicada en Datos, o pulse Temporada. La ventana inicial de siete días puede
   estar vacía si los datos de esta entrega son anteriores.

En Windows, el navegador puede utilizar una instancia ya instalada sin Conda ni
WSL2. Para ejecutar el servidor en esa computadora, el manual distingue la
preparación nativa de Windows de la alternativa WSL2 con Ubuntu. **El servidor
actual aún necesita adaptar los lanzadores y los bloqueos de archivos antes de
validarse como instalación nativa de Windows.** WSL2 es una alternativa para
reutilizar la versión Linux; no es un requisito para todos los usuarios.

## Credenciales propias

La entrega **no contiene claves personales**. El histórico y las detecciones
incluidas se pueden consultar sin credenciales. Para sincronizar datos nuevos o
solicitar imágenes, cree `.env` a partir de `.env.example` en el equipo servidor:

- `FIRMS_MAP_KEY`: NASA FIRMS, para detecciones VIIRS/MODIS.
- `EUMETSAT_CONSUMER_KEY` y `EUMETSAT_CONSUMER_SECRET`: EUMETSAT, para SLSTR FRP.
  La cuenta debe tener aceptada la licencia correspondiente.
- `CDSE_CLIENT_ID` y `CDSE_CLIENT_SECRET`: Copernicus Data Space, para imágenes
  Sentinel-3 OLCI y mosaicos trimestrales Sentinel-2.

Guarde `.env` como UTF-8, con ese nombre exacto, y reinicie el servidor tras
cambiarlo. No reenvíe archivos `.env`, tokens ni entornos privados. Las imágenes
satélites y el fondo externo requieren Internet; las API dependen del acceso,
la disponibilidad y las cuotas de cada proveedor. La sincronización es manual.

## Contenido y comprobación

- `cemec-sitio-estatico/`: visor y datos originales; se conserva la compilación
  recibida. No se dispone del proyecto fuente completo del frontend original.
- `ui/`, `scripts/` y `serve.js`: interfaz añadida y servicios actuales.
- `config.yaml`, `environment.yml` y el lock Linux: configuración y dependencias.
- `runtime/firms/active.json` y `runtime/firms/snapshots/`: catálogo incluido y
  snapshots necesarios, también los referenciados por geometrías anteriores.
- `origen/`: ZIP y documento recibidos originalmente, más el ejemplo EUMETSAT.
- `respaldos/`: recuperación de versiones anteriores, con sus instrucciones.
- `docs/` y `tests/`: documentación y verificaciones.
- `ENTREGA.json`, `MANIFIESTO-SHA256.json` y `verificar-entrega.py`: identificación,
  inventario y comprobación de integridad sin dependencias adicionales.

Con Python 3.12 instalado, puede ejecutar `python verificar-entrega.py` **antes
de instalar o modificar archivos**. Comprueba tamaño y SHA-256 de cada archivo
inventariado, no solicita claves ni accede a Internet. Al instalar, el script de
configuración puede actualizar el lock; conserve el ZIP como referencia original.

No se incluyen cachés de imágenes, registros de tareas, descargas temporales,
pruebas visuales ni entornos instalados. Las referencias a esas verificaciones
en los documentos describen pruebas del equipo de origen. Las fuentes originales
y los datos necesarios para abrir el catálogo sí se incluyen. La configuración
de retención continúa en simulación y no elimina datos automáticamente.

La entrega está destinada a ejecución local. El menú Administración no aporta
autenticación ni permisos por usuario. Publicar en Internet requiere preparar
el despliegue y sus controles de acceso.

## Para continuar con otro agente

Pídale que lea este archivo, `config.yaml` y los manuales; que verifique la
entrega y detecte el sistema operativo. En Windows nativo, debe completar y
probar los ajustes descritos en el manual antes de afirmar que funciona.
Debe conservar el histórico y los originales, trabajar en un entorno Conda
dedicado y solicitar las credenciales propias del nuevo responsable. No necesita
el historial de la conversación para revisar estos archivos.
