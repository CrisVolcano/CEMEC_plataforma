# CEMEC · Monitoreo de incendios

Plataforma para consultar detecciones térmicas, comparar sensores y generar reportes territoriales de Petén, Guatemala.

[![Arquitectura de CEMEC: interfaz web, servicios internos, almacenamiento y APIs](docs/diagramas/cemec-arquitectura-tecnica.png)](docs/diagramas/README.md)

## Qué permite hacer

- Consultar NASA FIRMS y Sentinel-3 SLSTR vía EUMETSAT.
- Filtrar por región, municipio, área protegida, zona de manejo y período.
- Visualizar imágenes Sentinel-3 OLCI y mosaicos trimestrales Sentinel-2.
- Exportar reportes PDF, datos y mapas georreferenciados en PDF —estos últimos en beta—.

## Inicio rápido

Servidor validado en **Ubuntu/Linux de 64 bits**, con **Conda/Miniforge** instalado. Desde la carpeta del proyecto:

```bash
./Setup-CEMEC.sh
cp -n .env.example .env
PORT=8090 ./Start-CEMEC.sh
```

Abre **http://localhost:8090**. El instalador crea un entorno Conda dedicado. Para conectar las APIs, completa las claves en `.env` antes de iniciar; sin ellas puedes consultar los datos incluidos.

Para instalar el servidor en Windows, revisa las alternativas y adaptaciones descritas en el [manual de instalación](docs/manuales/manual-instalacion.md).

## Documentación

- [Instalación y configuración](docs/manuales/manual-instalacion.md)
- [Manual de uso](docs/manuales/manual-uso.md)
- [Arquitectura técnica](docs/diagramas/README.md)
- [Operación y documentación completa](docs/README.md)
- [Desarrollo y pruebas](CONTRIBUTING.md) · [Procedencia y licencias](NOTICE.md)
