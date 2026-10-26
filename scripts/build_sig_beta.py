"""Construye un ejercicio SIG estático y reproducible, sin API ni credenciales."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'cemec-sitio-estatico/data/v-79544d8e805b0b1d'
DEST = ROOT / 'ui/sig-beta/data'


def build():
    DEST.mkdir(parents=True, exist_ok=True)
    territories = json.loads((SOURCE / 'territories.geojson').read_text())['features']
    records = json.loads((SOURCE / 'web/2026-03.json').read_text())
    # Selección regional explícita. No deduplicar observaciones científicas
    # mediante una tolerancia espacial/temporal implícita.
    rows = [r for r in records if r['instrument'] == 'VIIRS' and 'region-peten' in r['units']]
    points = [{'type': 'Feature', 'id': r['id'],
               'geometry': {'type': 'Point', 'coordinates': [r['lon'], r['lat']]},
               'properties': {k: v for k, v in r.items() if k not in ('lat', 'lon', 'units')}} for r in rows]
    layers = [
        ('municipios', 'Municipios de Petén', [f for f in territories if f['properties']['kind'] == 'municipio'],
         'geoBoundaries · CONRED/OCHA · CC BY 3.0 IGO', 'Límites de referencia; verificar vigencia y adecuación a la escala del análisis.'),
        ('areas-protegidas', 'Áreas protegidas', [f for f in territories if f['properties']['kind'] == 'protegida'],
         'CEMEC · zonificación 2025', 'Son geometrías del catálogo, incluidos fragmentos. Pueden existir solapamientos. Condiciones de redistribución por confirmar con CEMEC.'),
        ('viirs-marzo-2026', 'Detecciones VIIRS · marzo de 2026', points,
         'INAB · puntos de calor; instrumento VIIRS', 'Detecciones, no incendios individuales ni superficie quemada. No interpretar ausencia de registros como ausencia de fuego. No se aplicó deduplicación científica adicional.'),
    ]
    manifest = {'schema_version': 1, 'edition': 'beta-2026-03-v1', 'source_catalog': SOURCE.name,
                'source_boundary_version': json.loads((SOURCE / 'catalog.json').read_text())['boundary_version'],
                'period': {'start': '2026-03-01', 'end': '2026-03-31', 'time_zone': 'UTC'},
                'coordinates': 'OGC:CRS84 · longitud, latitud WGS84',
                'publication_status': 'Prueba local. Publicación institucional pendiente de revisión.',
                'sources_sha256': {n: hashlib.sha256((SOURCE / n).read_bytes()).hexdigest()
                                   for n in ['territories.geojson', 'web/2026-03.json', 'catalog.json']},
                'point_sources': dict(Counter(r['source'] for r in rows)), 'layers': []}
    for key, title, features, source, limitations in layers:
        payload = (json.dumps({'type': 'FeatureCollection', 'name': key, 'features': features},
                              ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()
        filename = key + '.geojson'
        (DEST / filename).write_bytes(payload)
        manifest['layers'].append({'id': key, 'title': title, 'file': filename, 'count': len(features),
                                   'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(),
                                   'source': source, 'limitations': limitations})
    (DEST / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'edition': manifest['edition'], 'layers': {l['id']: l['count'] for l in manifest['layers']}}, ensure_ascii=False))


if __name__ == '__main__':
    build()
