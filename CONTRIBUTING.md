# Colaborar en CEMEC

1. Instalar el entorno Conda y configurar un `.env` propio, según el README.
2. Trabajar en una rama con un cambio concreto. Mantener intactos los archivos de `cemec-sitio-estatico/`; los cambios del visor van en `ui/` y los adaptadores en `scripts/`.
3. Ejecutar `python scripts/replicate.py --verify-only`, `python -m unittest discover -s tests -p 'test_*.py'` y `python scripts/github_repository.py audit` desde el entorno dedicado.
4. Para cambios visuales, comprobar escritorio y móvil, filtros por las cuatro unidades, navegación, imágenes, descargas y reportes. Las pruebas `check_*_ui.cjs` necesitan Chrome y Playwright 1.58.2 en el entorno local; no están instalados por el entorno mínimo ni por la integración continua básica.
5. Describir el problema, el comportamiento resultante y la validación en el pull request. Registrar los cambios de operación en `docs/`.

No subir `.env`, claves, cachés, snapshots de operación, respaldos ni entregas privadas. Las pruebas de proveedores deben usar respuestas simuladas; las consultas reales se realizan manualmente y no forman parte del flujo automático de contribución.

Los datos de referencia y la compilación original no deben reemplazarse silenciosamente. Toda actualización requiere procedencia, versión y validación. Consultar `NOTICE.md` antes de redistribuir componentes o capas.
