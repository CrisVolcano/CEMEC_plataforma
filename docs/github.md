# Preparación del repositorio CEMEC

Visibilidad acordada: **privado inicialmente**. El usuario creó el repositorio [CrisVolcano/CEMEC_plataforma](https://github.com/CrisVolcano/CEMEC_plataforma). Se configuró esa URL como `origin` de la copia preparada. El 26 de octubre se verificaron mediante la autenticación Git local su visibilidad privada, los permisos de escritura y la ausencia de ramas remotas antes de la primera publicación. La conexión integrada de GitHub devolvía 404 para este repositorio; se utilizó la autenticación HTTPS local existente, sin copiar credenciales al proyecto.

## Copia preparada

El entorno de trabajo reserva una carpeta `.git` protegida y vacía. Para no modificar esa carpeta ni mezclar datos operativos con Git, se prepara una copia independiente en **`repositorio-github/`**. Esta copia usa la rama `main`, un hook local de auditoría y el remoto `origin` indicado arriba. El script de preparación no crea commits; la revisión, el commit y el envío se realizan posteriormente. La aplicación operativa sigue en la carpeta original.

Para preparar otra copia nueva desde la raíz:

```bash
./.conda-env/bin/python scripts/github_repository.py prepare --destination repositorio-github
```

El destino debe ser nuevo. El comando nunca sobrescribe una copia existente, nunca hace commit y nunca publica. El informe local queda en `.github-preparacion/preparacion.json`, fuera de la copia.

Incluye código, interfaz, dependencias declaradas, pruebas, documentación y la compilación original con su conjunto inicial de datos. No incluye `.env`, entornos instalados, claves de cuentas, `runtime`, archivos de origen, respaldos, ZIP de entrega ni otras carpetas operativas. Los datos actualizados por API no sustituyen el conjunto inicial del repositorio.

## Instalación reproducible

Un checkout completo se verifica con `scripts/replicate.py` usando el manifiesto de la compilación. El ZIP original y su manual son opcionales cuando todos los archivos ya están presentes. Si se proporcionan, se verifican sus hashes; si falta un archivo del sitio y no está el ZIP original, la instalación se detiene en lugar de inventar o sobrescribir contenido.

`.gitattributes` mantiene los bytes de `cemec-sitio-estatico/` sin conversión de finales de línea y conserva LF para los lanzadores. `.env.example` define las cinco variables vacías. Crear el entorno y completar las claves se hace después del clone, en cada equipo. Las imágenes y las consultas externas requieren internet.

## Revisión antes del primer commit

Desde `repositorio-github/`, usando el Python del entorno Conda:

```bash
git status --short
git diff --cached --stat
python scripts/github_repository.py audit --staged
python scripts/replicate.py --verify-only
python -m unittest discover -s tests -p 'test_*.py'
```

La auditoría de índice revisa los bytes realmente preparados, no solo los del archivo de trabajo. Detecta las claves locales conocidas si existen en `.env`, variantes Basic codificadas, algunos patrones de tokens, claves privadas, rutas excluidas y archivos de 100 MiB o más. También inspecciona el contenido de Word/ZIP. No es una garantía de detectar cualquier secreto o información sensible.

El hook instalado se conserva como archivo en `.githooks/pre-commit`. Tras un clone debe habilitarse localmente con `git config core.hooksPath .githooks`; esa configuración no viaja con el repositorio. Puede ejecutarse la auditoría manualmente aunque no se habilite el hook.

## GitHub Actions

`.github/workflows/ci.yml` define comprobaciones Linux sin secretos de proveedores: auditoría, integridad de originales y pruebas Python. Utiliza las acciones oficiales checkout y setup-miniconda fijadas a un commit, con permisos de solo lectura y sin conservar credenciales del checkout. La instalación fresca y la ejecución en un runner de GitHub quedan pendientes; las pruebas locales reutilizan el entorno Conda existente. Las pruebas visuales de Chrome/Playwright no forman parte de esta primera configuración de CI.

## Licencias y contenido público

`NOTICE.md` registra la procedencia y las licencias conservadas. No se ha impuesto MIT ni otra licencia global a código o capas de terceros. Antes de publicar de forma pública, confirmar la redistribución de la compilación recibida, las capas CEMEC, la cartografía de contexto y el histórico. Se incluye el conjunto inicial para que la copia sea funcional; su inclusión no debe confundirse con una autorización de redistribución pública ya verificada.

El repositorio no contiene los respaldos locales a los que hacen referencia los registros históricos. Estos documentos describen el trabajo realizado; los enlaces a archivos operativos y resultados locales pueden no estar disponibles en un checkout nuevo. Las entregas privadas anteriores con claves deben permanecer fuera de Git incluso si los destinatarios son de confianza.

## Publicación posterior

Cuando se confirme cuenta/organización, nombre, visibilidad y contenido:

1. Revisar el índice y configurar la identidad real de autor en Git.
2. Crear el commit inicial.
3. Verificar el acceso al repositorio ya creado, su contenido y visibilidad. Si contiene archivos o commits, conservarlos e integrarlos antes de enviar cambios.
4. Revisar `origin` y enviar `main` sin forzar ni sobrescribir historia remota.
5. Revisar la primera ejecución de Actions y probar una instalación desde un clone nuevo.

El script de preparación no ejecuta estos pasos remotos. No colocar contraseñas o tokens en la URL de Git. El servidor de monitoreo continúa arrancando con `Start-CEMEC.sh` en infraestructura propia.

Fuentes: [límites de archivos GitHub](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github), [gestión de credenciales expuestas](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository), [checkout](https://github.com/actions/checkout) y [setup-miniconda](https://github.com/conda-incubator/setup-miniconda).

## Validación local de esta preparación

El 26 de octubre de 2026 se exportó una copia limpia del índice Git, sin `.env`, `origen/` ni `runtime/`. Se verificaron los 1127 archivos originales, pasaron 58 pruebas Python y arrancó el servidor en un puerto temporal, con el catálogo inicial de 66.582 observaciones y sin claves configuradas. Se comprobó el rango HTTP de PMTiles, las fuentes locales, la página SIG beta y el hook sobre el índice. Se reutilizó el entorno Conda existente; no se realizó una instalación fresca ni se ejecutó GitHub Actions. Los informes operativos están en `.github-preparacion/` del equipo de preparación y no se publican.
