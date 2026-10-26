# Procedencia y licencias

Este proyecto reúne una compilación original del observatorio CEMEC, adaptadores de presentación, servicios de datos y componentes de terceros.

## Código del observatorio

La carpeta `cemec-sitio-estatico/` contiene la compilación recibida, conservada con un manifiesto SHA256. No contiene el proyecto fuente original de React. Los cambios legibles del visor se encuentran en `ui/` y `scripts/` y se aplican al servir esa compilación.

No se ha asignado una licencia global de código abierto al conjunto. Deben confirmarse con los titulares las condiciones de redistribución de la compilación original y de las contribuciones antes de una publicación pública. Un repositorio privado no cambia las condiciones de sus componentes.

## Componentes distribuidos

- MapLibre GL JS: motor incluido en la compilación original. [Repositorio y licencia](https://github.com/maplibre/maplibre-gl-js).
- Exportador MapLibre 6.0.0: licencia y avisos de dependencias conservados en `ui/vendor/maplibre-gl-export-6.0.0/`.
- Barlow: SIL Open Font License, conservada en `ui/vendor/barlow/OFL.txt` y en la maqueta que incluye las fuentes.
- Las dependencias Conda se instalan desde `environment.yml` o el lock Linux; conservan sus respectivas licencias.

## Datos y cartografía

El conjunto inicial conserva la atribución registrada en el catálogo: CEMEC (límites y zonificación), geoBoundaries / CONRED-OCHA (municipios, CC BY 3.0 IGO) e INAB (procedencia del histórico de detecciones). La presencia de una capa en la aplicación no acredita por sí sola autorización para redistribuirla públicamente. Deben confirmarse las condiciones de las capas CEMEC, el contexto y el histórico antes de cambiar la visibilidad del repositorio.

NASA FIRMS, EUMETSAT y CDSE son servicios externos sujetos a sus condiciones de acceso y uso. Las claves personales no se distribuyen en el repositorio. El fondo Esri se solicita opcionalmente a su servicio y conserva atribución; no se incluye una descarga de ese fondo.
