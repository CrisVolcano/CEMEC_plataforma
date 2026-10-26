# Manuales de CEMEC

Actualización del 26 de octubre: las fuentes Markdown incorporan FIRMS hasta 30 días. Los PDF y Word conservan la edición 1.1 anterior; consultar [la guía de FIRMS](../firms-30-dias.md) y [la interfaz cartográfica](../diseno/interfaz-cartografica-20261026.md) para los cambios posteriores.

Edición 1.1, 19 de octubre de 2026. Documentos de referencia para la versión
actual con interfaz moderna, conectores, imágenes opcionales y fondo Esri.

| Manual | Lectura | Edición | Fuente |
|---|---|---|---|
| Instalación y configuración | [PDF](manual-instalacion.pdf) | [Word](manual-instalacion.docx) | [Markdown](manual-instalacion.md) |
| Uso e interpretación | [PDF](manual-uso.pdf) | [Word](manual-uso.docx) | [Markdown](manual-uso.md) |

El manual distingue tres situaciones: **consultar desde Windows sin instalar
componentes del servidor**, preparar una instalación local **nativa Windows** y
utilizar **WSL2 con Ubuntu como alternativa**. WSL2 no es un requisito general.

La entrega actual requiere adaptar los lanzadores y los bloqueos de archivos del
backend antes de considerarse lista para Windows nativo. La revisión documental
no implementa esos cambios ni afirma que se haya probado Windows. El manual
explica la preparación, los ajustes concretos pendientes y la aceptación necesaria.

Incluye requisitos, entrega de archivos, entorno Conda, credenciales separadas de
FIRMS/EUMETSAT/CDSE, puertos, diagnóstico, respaldo y recuperación. El de uso
explica controles, sensores, confianza, FRP, territorio, tiempos UTC, imágenes,
comparación, exportaciones, reportes, actualización e importación.

Los ejemplos de secretos son marcadores: los documentos no contienen valores
reales. Las capturas proceden de verificaciones reales del visor y se recortaron
para mejorar su lectura. Sus cifras y fechas no son un estado en vivo.

## Mantener los manuales

Editar primero los Markdown y regenerar los Word con `scripts/build_manuals.py`.
Las figuras se conservan en `figuras/`. Esta herramienta editorial usa
python-docx y Pillow; no son dependencias necesarias para servir CEMEC. Para
repetir la edición, preparar un entorno separado con las dependencias de
[requirements-edicion.txt](requirements-edicion.txt), sin alterar Conda base ni
el entorno operativo del visor.

Los PDF se exportan desde los Word con Word o LibreOffice y se revisan visualmente.
El script `scripts/finalize_manual_pdfs.py` conserva los enlaces en los PDF de
LibreOffice que no los exportan; espera las conversiones en
`runtime/manuales-qa/instalacion/manual-instalacion.pdf` y
`runtime/manuales-qa/uso/manual-uso.pdf`, y escribe los PDF finales en esta carpeta. La
verificación de esta edición está en [validacion.json](validacion.json). Las
imágenes de páginas y otros archivos intermedios quedan en
`runtime/manuales-qa/` y no son entregables.

Si cambia un botón, formato, variable, límite o función, actualizar el manual y
su fecha, volver a exportar ambos formatos y revisar los enlaces y las páginas.
La documentación de operación detallada sigue en el [índice central](../README.md).

## Revisión de la edición 1.1

Se separó el acceso del usuario desde la instalación del servidor, se documentó
Conda nativo Windows y la edición de .env en el servidor, y se trasladaron los
pasos WSL2 a una alternativa específica. La revisión no cambia conectores,
datos, credenciales ni lanzadores de la aplicación. El respaldo de la edición
anterior está identificado en
[ultimo-respaldo-manuales.json](../../respaldos/ultimo-respaldo-manuales.json).
