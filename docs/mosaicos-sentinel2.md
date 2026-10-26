# Mosaicos trimestrales Sentinel-2 y control de consumo

Estado: implementados el 19 de octubre de 2026 en sustitución del selector de
escenas L2A de Sentinel-2. OLCI y las detecciones FIRMS/EUMETSAT no cambian.

## Uso del visor

**Explorar → Mapa → Sentinel-2 · Mosaico** ofrece **Último publicado** y
**Elegir trimestre**. El segundo permite seleccionar año y T1/T2/T3/T4, y cargar
el resultado. No se permiten trimestres aún abiertos. Un trimestre terminado
puede no estar publicado todavía; se informa sin sustituirlo por una imagen de
otra fecha. Los períodos sin producto quedan también en la caché del catálogo.

Se conservan mostrar/ocultar, opacidad y descarga PNG/JSON. La imagen se alterna
con OLCI, manteniendo una sola capa de fondo activa. El mapa muestra el trimestre
completo, cobertura con datos y escala efectiva. Se avisa cuando ese trimestre
difiere de las fechas de detecciones. Cambiar unidad retira la capa anterior;
volver a cargar el trimestre reutiliza el mismo mosaico regional.

Desde la vista regional se puede solicitar **Cargar detalle de esta zona** tras
acercarse. Mantiene el trimestre y prepara únicamente el recorte visible bajo
demanda. Comparte el presupuesto de seis preparaciones nuevas con la vista
general. Consulta [uso, límites y recuperación](detalle-mosaico.md).

## Producto oficial

Colección Sentinel Hub BYOC:
`byoc-5460de54-082e-473a-b6ea-d5cbe3c17cca`, Sentinel-2 L3 Quarterly Mosaics.
Los mosaicos oficiales combinan observaciones de tres meses, aplican la
clasificación SCL para descartar observaciones y calculan el primer cuartil por
banda y píxel. Pueden conservar huecos. RGB utiliza B04/B03/B02, con 10 m
nominales en el producto. Sus valores DN se convierten a reflectancia dividiendo
por 10000 antes de aplicar ganancia visual 2,5. La salida solicitada es PNG RGBA,
EPSG:3857; dataMask indica datos disponibles y no superficie despejada.

La fecha del catálogo identifica el inicio del trimestre, no una pasada. Por eso
la interfaz presenta `mosaic_period_utc`, no una supuesta hora única. Process
recibe el primer día del trimestre como intervalo de acceso a ese producto
precalculado: no se solicita recalcular una composición de cientos de escenas.
Se guardan los IDs de las teselas utilizadas como referencias del catálogo.

Fuente: [documentación oficial de mosaicos](https://documentation.dataspace.copernicus.eu/Data/SentinelMissions/Sentinel2.html#sentinel-2-level-3-quarterly-mosaics).

## Estrategia aplicada

- **Un recorte regional compartido por trimestre/revisión.** Se utiliza el
  rectángulo configurado de Petén, independiente del municipio o área elegida.
  Una unidad fuera de ese rectángulo requiere su propio recorte.
- **Vista acotada a 1024 píxeles por lado.** Reduce transferencia, memoria de
  imagen y procesamiento frente a la anterior vista de 1600. No garantiza detalle
  de 10 m al ampliar: en Petén la vista queda aproximadamente a 240 m/px.
- **Sin solicitudes al hacer zoom o desplazar el mapa.** Se amplía la imagen
  disponible. No hay descargas periódicas ni precarga de todos los trimestres.
- **Catálogo persistente durante 24 horas.** La búsqueda se comparte para Petén,
  incluidas respuestas vacías. Último publicado revisa el archivo desde enero de
  dos años antes hasta el último trimestre cerrado, completa las páginas y
  ordena los trimestres realmente encontrados.
- **Máximo de seis preparaciones nuevas por día UTC.** Los intentos fallidos
  también se cuentan conservadoramente. Los aciertos de caché siguen funcionando
  al alcanzar el límite; cambiar de día permite nuevos intentos.
- **Bloqueo entre procesos.** Evita preparar la misma composición dos veces
  simultáneamente y protege el presupuesto compartido. El límite corresponde al
  proyecto, no a cada usuario.
- **Cobertura por unidad calculada al preparar el mosaico.** La reutilización
  solo lee metadatos y selecciona el valor correspondiente; no vuelve a decodificar
  el PNG para cada municipio. Un área sin centros de píxel suficientes presenta
  cobertura sin estimación, en lugar de atribuirle una precisión inexistente.

La reducción de PU medida también refleja la menor resolución de salida. No se
afirma que cualquier mosaico sea intrínsecamente más barato que cualquier escena
a igual tamaño. El principal ahorro acumulado viene de reutilizarlo entre zonas
y usuarios. Preparar otra revisión, resolución o recorte distinto puede consumir
cuota de nuevo. Las descargas locales siguen consumiendo ancho de banda y trabajo
del servidor/navegador.

## Configuración y archivos

`config.yaml`, sección `sentinel2`:

```yaml
collection: byoc-5460de54-082e-473a-b6ea-d5cbe3c17cca
product: quarterly_mosaic
max_image_side: 1024
shared_unit_id: region-peten
shared_bbox: [-91.443759, 15.844419, -89.139843, 17.819454]
catalog_cache_hours: 24
max_new_mosaics_per_day: 6
```

Reiniciar el servidor tras cambiar parámetros. No escribir credenciales en este
archivo; se reutilizan las variables CDSE de `.env`. No hacen falta nuevas
dependencias Conda.

- Motor: `scripts/mosaic_service.py`, con el motor de imagen común.
- Rutas: `/api/sentinel2/search`, `/render`, `/jobs/<id>` e `/images/<hash>.png`
  o `.json`. Período se solicita como `mode: period`, `year` y `quarter`.
- Resultados: `runtime/sentinel2/<hash>/`; las escenas L2A anteriores se conservan
  y sus enlaces de descarga siguen disponibles.
- Catálogo: `runtime/sentinel2/catalog/`.
- Bloqueos: `runtime/sentinel2/locks/` y `.budget.lock`.
- Consumo: `runtime/sentinel2/usage.json`, con intentos, preparaciones completadas
  y PU reportadas por día; conserva hasta 90 días de contadores.

El contador no sustituye el panel de cuotas de CDSE. Solo registra las
preparaciones del nuevo motor, no todas las consultas históricas, otros programas
que usan la cuenta, llamadas de catálogo ni posibles cargos no reportados.
Un reintento de autenticación pertenece al mismo intento lógico de preparación.

Los metadatos de la vista general describen el mosaico regional, con `coverage_by_unit`.
Si hay un detalle activo, las descargas corresponden a ese recorte y su cobertura.
La respuesta del trabajo añade unidad solicitada y su cobertura. La identidad
incluye colección, trimestre, revisión de teselas/límites, bbox, resolución y
bandas. No hay archivos secretos en los resultados.

La retención sigue **dry_run**: no se activó ninguna eliminación. Consulta
[retencion.md](retencion.md). El PDF térmico sigue sin incrustar imágenes RGB.

## Medición real del 19 de octubre

Antes del cambio se observaron aproximadamente 4,69 MiB de caché OLCI y 10,83 MiB
de Sentinel-2 (15,52 MiB en conjunto), y unos 457,65 MiB de snapshots FIRMS. Son
tamaños en disco, no consumo de RAM. Las seis escenas L2A guardadas registraban
8,6731 PU cada una; no se extrapolan a una factura ni al consumo total de cuenta.

El catálogo oficial devolvió abril–junio de 2026 como último disponible para Petén.
El mosaico de prueba fue 1024 × 918, con cobertura con datos de 100 % en la
estimación por centros de píxel y **3,5859375 PU**. Frente a la vista anterior
1600 × 1421 de **8,673095703125 PU**, equivale a **58,65 % menos** en esta
comparación específica.

La prueba de navegador comprobó que el zoom no genera nuevos POST y que cargar el
mismo trimestre en el municipio de San Luis retorna el mismo URL con `cached: true`,
sin incrementar el presupuesto de preparación. Se revisaron también móvil,
selección trimestral y conservación de datos térmicos.

Evidencia: [verificación real](../runtime/mosaics-qa/live-verification.json),
[mapa](../runtime/mosaics-qa/localhost-desktop.png),
[selector trimestral](../runtime/mosaics-qa/localhost-quarter.png),
[móvil](../runtime/mosaics-qa/localhost-mobile.png).

## Si falla y cómo volver atrás

- Sin producto: elegir otro trimestre o Último publicado; puede existir retraso
  de publicación. Un catálogo vacío se guarda durante el TTL configurado.
- Cuota diaria local alcanzada: usar mosaicos guardados o esperar al día UTC
  siguiente. Cambiar el límite requiere valorar la cuota real de CDSE.
- 401/403: comprobar credenciales y permisos CDSE como en la integración anterior.
- 429: revisar la cuota de la cuenta; la caché local sigue siendo utilizable.
- Mosaico oscuro/parcial: revisar trimestre y metadatos; la composición oficial
  no elimina todos los huecos ni garantiza ausencia absoluta de nubes.

`respaldos/ultimo-respaldo-mosaicos.json` identifica el respaldo anterior al
cambio. Verificar su SHA-256 contra el manifiesto, detener el visor, extraer en
una carpeta separada con filtro `data`, copiar las rutas del manifiesto y volver
a iniciar. Conservar `.env` y `runtime/`: el respaldo es de código/documentación,
no sustituye las detecciones actuales. La [guía L2A anterior](sentinel2-visor.md)
se conserva como registro de esa versión.
