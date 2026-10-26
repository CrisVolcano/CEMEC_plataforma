"""API FIRMS y snapshots CEMEC. No altera los archivos de origen ni el visor."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import csv
from datetime import date, datetime, timedelta, timezone
from email.parser import BytesParser
from email.policy import default as email_policy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import math
import os
from pathlib import Path
import re
import secrets
import shutil
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit, unquote
from urllib.request import Request, urlopen
import uuid

import pyarrow as pa
import pyarrow.parquet as pq
from shapely.geometry import Point, shape
from shapely import make_valid
from shapely.strtree import STRtree
import yaml
from eumetsat_client import EumetsatClient, EumetsatError, read_csv, normalize_detection
from olci_service import OlciService
from mosaic_service import QuarterlyMosaicService

SOURCES = {
    'VIIRS_NOAA20_NRT': ('VIIRS', 'NOAA-20'),
    'VIIRS_NOAA21_NRT': ('VIIRS', 'NOAA-21'),
    'VIIRS_SNPP_NRT': ('VIIRS', 'S-NPP'),
    'MODIS_NRT': ('MODIS', None),
}

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    os.replace(temp, path)

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))

def load_environment(project):
    # Solo asignaciones KEY=value; nunca se ejecuta el contenido de .env.
    env_file = project / '.env'
    if env_file.is_file():
        for line in env_file.read_text(encoding='utf-8').splitlines():
            if line.strip() and not line.lstrip().startswith('#'):
                key, sep, value = line.partition('=')
                if sep and re.fullmatch(r'[A-Z_][A-Z0-9_]*', key.strip()):
                    os.environ.setdefault(key.strip(), value.strip().strip('"\''))

def validate_key(key):
    if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9]{32}', key):
        raise ValueError('Se requiere una MAP_KEY de FIRMS de 32 caracteres.')
    return key

def normalize_row(row, product=None, source=None):
    row = {str(k).strip().lower(): v for k, v in row.items() if k is not None}
    lat = float(row.get('latitude', row.get('lat', '')))
    lon = float(row.get('longitude', row.get('lon', row.get('lng', ''))))
    if not math.isfinite(lat + lon) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError('Coordenadas inválidas')
    day = str(row.get('acq_date', row.get('date', row.get('fecha', ''))))[:10]
    if re.fullmatch(r'\d{8}', day):
        day = f'{day[:4]}-{day[4:6]}-{day[6:]}'
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
        raise ValueError('Fecha inválida')
    date.fromisoformat(day)
    clock = str(row.get('acq_time', row.get('time', '0000'))).split('.')[0].replace(':', '').zfill(4)
    if not re.fullmatch(r'\d{4}', clock) or int(clock[:2]) > 23 or int(clock[2:]) > 59:
        raise ValueError('Hora inválida')
    sat = str(row.get('satellite', row.get('satelite', 'Desconocido'))).strip()
    sat = {'N': 'S-NPP', 'N20': 'NOAA-20', 'N21': 'NOAA-21', '1': 'NOAA-20',
           '2': 'NOAA-21', 'Suomi NPP': 'S-NPP', 'T': 'Terra', 'A': 'Aqua'}.get(sat, sat)
    instrument = str(row.get('instrument') or ('MODIS' if sat in ('Terra', 'Aqua') else 'VIIRS')).upper()
    if product:
        instrument, expected = SOURCES[product]
        sat = expected or sat
        if product == 'MODIS_NRT' and sat not in ('Terra', 'Aqua'):
            raise ValueError('Satélite MODIS desconocido')
    if not sat:
        raise ValueError('Satélite ausente')
    confidence = str(row.get('confidence') or 'unknown').lower()
    confidence = {'high': 'h', 'nominal': 'n', 'low': 'l'}.get(confidence, confidence)
    if re.fullmatch(r'\d+(\.\d+)?', confidence):
        value = float(confidence)
        if not 0 <= value <= 100:
            raise ValueError('Confianza fuera de rango')
        confidence = 'h' if value >= 80 else 'n' if value >= 30 else 'l'
    if confidence not in ('h', 'n', 'l', 'unknown'):
        raise ValueError('Confianza inválida')
    value = row.get('frp')
    frp = None if value is None or value == '' else float(value)
    if frp is not None and (not math.isfinite(frp) or frp < 0):
        raise ValueError('FRP inválida')
    daynight = str(row.get('daynight', '')).upper()
    if daynight not in ('D', 'N', ''):
        raise ValueError('Paso diurno/nocturno inválido')
    identity = f'{lat:.6f}|{lon:.6f}|{day}|{clock}|{sat}|{instrument}'
    return {'id': hashlib.sha256(identity.encode()).hexdigest()[:20], 'lat': lat, 'lon': lon,
            'date': day, 'time': clock, 'satellite': sat, 'instrument': instrument,
            'confidence': confidence, 'frp': frp, 'daynight': daynight,
            'source': source or f'NASA FIRMS · {product}',
            'product_version': str(row.get('version', row.get('product_version', ''))), 'units': []}

class FirmsClient:
    def __init__(self, settings):
        self.settings = settings

    def download(self, key, product, bbox, days, start=None):
        validate_key(key)
        area = ','.join(str(x) for x in bbox)
        endpoint = f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/{quote(key, safe="")}/{product}/{area}/{days}'
        if start:
            endpoint += '/' + start
        for attempt in range(self.settings.get('retries', 2) + 1):
            try:
                request = Request(endpoint, headers={'User-Agent': 'CEMEC-FIRMS/1.0'})
                with urlopen(request, timeout=self.settings.get('timeout_seconds', 60)) as response:
                    content = response.read(30 * 1024 * 1024 + 1)
                    if len(content) > 30 * 1024 * 1024:
                        raise ValueError('La respuesta de FIRMS excede el límite de descarga.')
                reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig')))
                if not reader.fieldnames or not {'latitude', 'longitude', 'acq_date', 'acq_time'}.issubset(reader.fieldnames):
                    raise ValueError('FIRMS no devolvió un CSV de detecciones válido. Verifica MAP_KEY, cuota y disponibilidad del producto.')
                return list(reader), content
            except HTTPError as error:
                if error.code in (429, 500, 502, 503, 504) and attempt < self.settings.get('retries', 2):
                    time.sleep(2 ** attempt)
                    continue
                # No divulgar la URL del error: contiene la credencial.
                raise ValueError(f'FIRMS respondió HTTP {error.code}; revisa la clave, cuota o disponibilidad.') from None
            except (URLError, TimeoutError, OSError):
                if attempt < self.settings.get('retries', 2):
                    time.sleep(2 ** attempt)
                    continue
                raise ValueError('No se pudo conectar con FIRMS. Revisa la conexión de red.') from None

class Store:
    def __init__(self, config_path):
        self.config_path = Path(config_path).resolve()
        self.base = self.config_path.parent
        self.config = yaml.safe_load(self.config_path.read_text())
        self.site = (self.base / self.config['server']['root']).resolve()
        self.runtime = (self.base / self.config['firms']['storage']).resolve()
        self.settings = self.config['firms']
        self.original = read_json(self.site / 'data/catalog.json')
        self.client = FirmsClient(self.settings)
        self.eumetsat_settings = self.config.get('eumetsat', {})
        self.eumetsat_client = EumetsatClient(self.eumetsat_settings,
            self.base / self.eumetsat_settings.get('cache', 'runtime/eumetsat'))
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='firms')
        self.lock = threading.RLock()
        self.busy = False
        self.jobs = {}
        self.runtime.mkdir(parents=True, exist_ok=True)
        for file in (self.runtime / 'jobs').glob('*.json'):
            job = read_json(file)
            if job['status'] in ('pending', 'running'):
                job.update(status='failed', error='La aplicación se detuvo antes de completar esta tarea.')
                atomic_json(file, job)
            self.jobs[job['id']] = job
        self.geometries = None

    def catalog(self):
        active = self.runtime / 'active.json'
        return read_json(active)['catalog'] if active.is_file() else deepcopy(self.original)

    def resolve_url(self, url):
        if url.startswith('/live-data/'):
            root, relative = self.runtime / 'snapshots', url[len('/live-data/'):]
        elif url.startswith('/data/'):
            root, relative = self.site, url.lstrip('/')
        else:
            raise ValueError('Ruta de datos inválida')
        target = (root / relative).resolve()
        if not target.is_relative_to(root.resolve()) or target == root.resolve():
            raise ValueError('Ruta de datos inválida')
        return target

    def key(self):
        return os.environ.get(self.settings.get('key_env', 'FIRMS_MAP_KEY'), '').strip()

    def status(self):
        active = self.runtime / 'active.json'
        with self.lock:
            jobs = sorted(self.jobs.values(), key=lambda x: x['created_at'], reverse=True)[:20]
            return {'firms_configured': bool(re.fullmatch(r'[A-Za-z0-9]{32}', self.key())), 'interval_minutes': 0,
                    'last_sync': read_json(active).get('last_sync') if active.is_file() else None,
                    'eumetsat_configured': self.eumetsat_settings.get('enabled', False) and all(self.eumetsat_credentials()),
                    'last_eumetsat_sync': read_json(active).get('last_eumetsat_sync') if active.is_file() else None,
                    'eumetsat': {'collection': self.eumetsat_settings.get('collection'),
                        'days': self.eumetsat_settings.get('days', 3),
                        'max_days_per_sync': self.eumetsat_settings.get('max_days_per_sync', 31),
                        'bbox': self.eumetsat_settings.get('bbox'), 'product_limit': None},
                    'firms': {'max_days_per_sync': self.settings.get('max_days_per_sync', 30),
                              'max_days_per_request': 5},
                    'jobs': deepcopy(jobs), 'sources': list(SOURCES),
                    'dataset': self.catalog()['version'], 'busy': self.busy,
                    'import_formats': ['csv', 'geojson', 'json']}

    def update_job(self, job_id, **fields):
        with self.lock:
            self.jobs[job_id].update(fields)
            atomic_json(self.runtime / 'jobs' / f'{job_id}.json', self.jobs[job_id])

    def validate_sync(self, request):
        key = validate_key(request.get('key') or self.key())
        days = request.get('days', self.settings['days'])
        maximum = self.settings.get('max_days_per_sync', 30)
        if type(maximum) is not int or not 1 <= maximum <= 30:
            raise ValueError('Configura firms.max_days_per_sync entre 1 y 30.')
        if type(days) is not int or not 1 <= days <= maximum:
            raise ValueError(f'La ventana de FIRMS debe ser de 1 a {maximum} días.')
        sources = request.get('sources', self.settings['sources'])
        if not isinstance(sources, list) or not sources or any(not isinstance(x, str) or x not in SOURCES for x in sources):
            raise ValueError('Selecciona productos VIIRS o MODIS admitidos.')
        start = request.get('start')
        if start is not None:
            if not isinstance(start, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', start):
                raise ValueError('Fecha inicial inválida; usa YYYY-MM-DD.')
            if date.fromisoformat(start) + timedelta(days=days-1) > datetime.now(timezone.utc).date():
                raise ValueError('No se pueden consultar fechas futuras.')
        return key, days, list(dict.fromkeys(sources)), start

    def submit(self, request):
        params = self.validate_sync(request)
        return self.new_job('sync', self.sync, params)

    def eumetsat_credentials(self):
        return tuple(os.environ.get(self.eumetsat_settings.get(name + '_env', 'EUMETSAT_' + name.upper()), '').strip()
                     for name in ('consumer_key', 'consumer_secret'))

    def submit_eumetsat(self, request):
        if not self.eumetsat_settings.get('enabled', False):
            raise ValueError('La integración EUMETSAT está deshabilitada en config.yaml.')
        if not all(self.eumetsat_credentials()):
            raise ValueError('Configura las credenciales EUMETSAT en el .env del servidor.')
        days = request.get('days', self.eumetsat_settings.get('days', 3))
        maximum = self.eumetsat_settings.get('max_days_per_sync', 31)
        if type(days) is not int or not 1 <= days <= maximum:
            raise ValueError(f'La ventana EUMETSAT debe ser de 1 a {maximum} días.')
        now = datetime.now(timezone.utc)
        if request.get('start') is not None:
            start_text = request['start']
            if not isinstance(start_text, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', start_text):
                raise ValueError('Fecha inicial inválida; usa YYYY-MM-DD.')
            start = datetime.combine(date.fromisoformat(start_text), datetime.min.time(), tzinfo=timezone.utc)
            if start > now:
                raise ValueError('No se pueden consultar fechas futuras.')
            end = min(start + timedelta(days=days), now)
        else:
            start, end = now - timedelta(days=days), now
        bbox = self.eumetsat_settings.get('bbox', [])
        if len(bbox) != 4 or not (-180 <= bbox[0] < bbox[2] <= 180 and -90 <= bbox[1] < bbox[3] <= 90):
            raise ValueError('Extensión EUMETSAT inválida en config.yaml.')
        if self.eumetsat_settings.get('product_limit') is not None or self.eumetsat_settings.get('variant') != 'MWIR1km_standard':
            raise ValueError('EUMETSAT requiere product_limit: null y variant: MWIR1km_standard.')
        return self.new_job('eumetsat', self.sync_eumetsat, (start, end))

    def sync_eumetsat(self, job_id, start, end):
        bbox = self.eumetsat_settings['bbox']
        provenance = {'provider': 'eumetsat', 'collection': self.eumetsat_settings['collection'],
            'variant': 'MWIR1km_standard', 'job_id': job_id, 'start': start.isoformat(),
            'end': end.isoformat(), 'bbox': bbox, 'products_found': 0, 'products_processed': 0,
            'received': 0, 'rejected': 0, 'outside_bbox': 0, 'outside_period': 0, 'downloads': [], 'at': utc_now()}
        manifest = self.runtime / 'downloads' / job_id / 'eumetsat.json'
        points = []
        try:
            self.update_job(job_id, stage='Autenticando y buscando productos Sentinel-3')
            results, total = self.eumetsat_client.search(self.eumetsat_credentials(), start, end, bbox)
            provenance['products_found'] = total
            self.update_job(job_id, products_found=total, products_processed=0)
            for product in self.eumetsat_client.products(results):
                self.update_job(job_id, stage=f'Descargando Sentinel-3: {provenance["products_processed"] + 1}/{total}')
                content, download = self.eumetsat_client.fetch(product)
                rows, metadata = read_csv(content)
                provenance['downloads'].append({**download, 'rows': len(rows)})
                provenance['received'] += len(rows)
                for row in rows:
                    point = normalize_detection(row, download['product'], download['entry'], metadata)
                    if not (bbox[0] <= point['lon'] <= bbox[2] and bbox[1] <= point['lat'] <= bbox[3]):
                        provenance['outside_bbox'] += 1
                        continue
                    instant = datetime.fromisoformat(point['observation_utc'])
                    if not start <= instant < end:
                        provenance['outside_period'] += 1
                        continue
                    self.assign_units(point)
                    points.append(point)
                provenance['products_processed'] += 1
                self.update_job(job_id, products_processed=provenance['products_processed'], received=provenance['received'], in_area=len(points))
                atomic_json(manifest, {**provenance, 'complete': False})
            if provenance['products_processed'] != total:
                raise ValueError('La búsqueda EUMETSAT cambió durante la descarga o quedó incompleta. Reintenta; se conserva el catálogo publicado.')
            provenance.update(complete=True, in_area=len(points), at=utc_now())
            if total == 0:
                provenance['notice'] = 'Sin productos disponibles en este periodo; no demuestra ausencia de fuego.'
            self.update_job(job_id, stage='Integrando Sentinel-3 y preparando el catálogo')
            result = self.publish(points, provenance, kind='eumetsat')
            atomic_json(manifest, result)
            return result
        except Exception as error:
            atomic_json(manifest, {**provenance, 'complete': False, 'failure_type': type(error).__name__})
            raise

    def new_job(self, kind, worker, params):
        with self.lock:
            if self.busy:
                raise RuntimeError('Ya hay una tarea en ejecución. Espera a que termine.')
            self.busy = True
            job = {'id': uuid.uuid4().hex, 'kind': kind, 'status': 'pending', 'created_at': utc_now()}
            self.jobs[job['id']] = job
            self.update_job(job['id'])
            self.executor.submit(self.run_job, job['id'], worker, params)
            return deepcopy(job)

    def run_job(self, job_id, worker, params):
        self.update_job(job_id, status='running', started_at=utc_now())
        try:
            result = worker(job_id, *params)
            self.update_job(job_id, status='completed', finished_at=utc_now(), result=result)
        except Exception as error:
            # Los errores de red se convierten en textos sin URL/credenciales.
            message = str(error) if isinstance(error, (ValueError, RuntimeError)) else 'No se pudo procesar la tarea; el conjunto publicado se conserva.'
            if params and isinstance(params[0], str) and len(params[0]) == 32:
                message = message.replace(params[0], '[clave omitida]')
            fields = {'error_code': error.code, 'http_status': error.http_status} if isinstance(error, EumetsatError) else {}
            self.update_job(job_id, status='failed', finished_at=utc_now(), error=message, **fields)
        finally:
            with self.lock:
                self.busy = False

    def assign_units(self, point):
        if self.geometries is None:
            features = read_json(self.site / self.original['territories_url'].lstrip('/'))['features']
            self.unit_ids = [f['properties']['id'] for f in features]
            self.geometries = STRtree([make_valid(shape(f['geometry'])) for f in features])
        indices = self.geometries.query(Point(point['lon'], point['lat']), predicate='covered_by')
        point['units'] = sorted(self.unit_ids[int(idx)] for idx in indices)

    def sync(self, job_id, key, days, sources, start):
        bbox = self.settings['bbox']
        if len(bbox) != 4 or not (-180 <= bbox[0] < bbox[2] <= 180 and -90 <= bbox[1] < bbox[3] <= 90):
            raise ValueError('Extensión geográfica inválida en config.yaml')
        first = date.fromisoformat(start) if start else datetime.now(timezone.utc).date() - timedelta(days=days-1)
        last = first + timedelta(days=days-1)
        points, rejected, received, downloads = [], 0, 0, []
        raw_root = self.runtime / 'downloads' / job_id
        blocks = [(first + timedelta(days=offset), min(5, days-offset)) for offset in range(0, days, 5)]
        for product in sources:
            for index, (block_start, block_days) in enumerate(blocks, 1):
                block_end = block_start + timedelta(days=block_days-1)
                self.update_job(job_id, stage=f'Descargando {product} · bloque {index}/{len(blocks)} · {block_start} — {block_end}')
                # Una ventana larga usa fechas explícitas; una consulta corta
                # conserva el contrato de descarga reciente ya existente.
                request_start = block_start.isoformat() if start or len(blocks) > 1 else None
                rows, content = self.client.download(key, product, bbox, block_days, request_start)
                raw_root.mkdir(parents=True, exist_ok=True)
                filename = f'{product}_{block_start}_{block_end}.csv' if len(blocks) > 1 else f'{product}.csv'
                (raw_root / filename).write_bytes(content)
                downloads.append({'product': product, 'start': block_start.isoformat(), 'end': block_end.isoformat(),
                                  'days': block_days, 'file': filename, 'rows': len(rows), 'sha256': hashlib.sha256(content).hexdigest()})
                received += len(rows)
                for row in rows:
                    try:
                        point = normalize_row(row, product)
                        if not block_start.isoformat() <= point['date'] <= block_end.isoformat():
                            raise ValueError('Detección fuera del bloque solicitado')
                        if not (bbox[0] <= point['lon'] <= bbox[2] and bbox[1] <= point['lat'] <= bbox[3]):
                            raise ValueError('Detección fuera del área solicitada')
                        self.assign_units(point)
                        points.append(point)
                    except (ValueError, TypeError, OverflowError):
                        rejected += 1
        if received and not points:
            raise ValueError('FIRMS devolvió registros, pero ninguno pasó la validación; no se publicó una versión.')
        self.update_job(job_id, stage='Integrando registros y preparando el catálogo')
        result = self.publish(points, {'job_id': job_id, 'received': received, 'rejected': rejected,
            'products': sources, 'start': first.isoformat(), 'end': last.isoformat(), 'bbox': bbox,
            'downloads': downloads, 'at': utc_now()}, kind='sync')
        return result

    def publish(self, incoming, provenance, kind='sync'):
        catalog = self.catalog()
        baseline = []
        for partition in catalog['partitions']:
            baseline.extend(read_json(self.resolve_url(partition['url'])))
        # El rectángulo de consulta puede contener detecciones fuera de las
        # jurisdicciones originales. Es una unidad de consulta, no un límite legal.
        provider = 'EUMETSAT' if kind == 'eumetsat' else 'FIRMS'
        query_id = 'region-eumetsat-area' if kind == 'eumetsat' else 'region-firms-area'
        bbox = self.eumetsat_settings['bbox'] if kind == 'eumetsat' else self.settings['bbox']
        existing_query = next((u for u in catalog['units'] if u['id'] == query_id), None)
        query_enabled = bool(incoming) or existing_query is not None
        query_changed = False
        if query_enabled:
            for index, point in enumerate(baseline + incoming):
                units = set(point['units'])
                if bbox[0] <= point['lon'] <= bbox[2] and bbox[1] <= point['lat'] <= bbox[3]:
                    units.add(query_id)
                else:
                    units.discard(query_id)
                updated = sorted(units)
                if updated != point['units']:
                    point['units'] = updated
                    if index < len(baseline):
                        query_changed = True
            query_changed = query_changed or existing_query is None or existing_query['bbox'] != bbox
        merged = {p['id']: p for p in baseline}
        added, duplicates, changed = 0, 0, query_changed
        for point in incoming:
            # Las unidades de consulta ya publicadas siguen aplicando al añadir
            # puntos de otro proveedor; no perder su pertenencia al actualizar.
            for unit in catalog['units']:
                if unit['id'] in ('region-firms-area', 'region-eumetsat-area') and unit['id'] != query_id:
                    other_bbox = unit['bbox']
                    if other_bbox[0] <= point['lon'] <= other_bbox[2] and other_bbox[1] <= point['lat'] <= other_bbox[3]:
                        point['units'] = sorted(set(point['units']) | {unit['id']})
            previous = merged.get(point['id'])
            if previous is None:
                added += 1
            else:
                duplicates += 1
            # Preserva INAB como origen del histórico y agrega observaciones nuevas
            # una sola vez. Las detecciones FIRMS existentes reciben revisiones NRT.
            if previous and (not previous['source'].startswith(('NASA FIRMS', 'EUMETSAT'))
                             or previous['source'] != point['source']):
                continue
            if previous != point:
                merged[point['id']] = point
                changed = True
        result = {**provenance, 'added': added, 'duplicates': duplicates,
                  'total_points': len(merged), 'dataset': catalog['version'], 'published': changed}
        if not changed:
            self.record_active(catalog, result, kind)
            return result
        points = sorted(merged.values(), key=lambda p: (p['date'], p['time'], p['id']))
        signature = hashlib.sha256(json.dumps(points, sort_keys=True, separators=(',', ':')).encode()).hexdigest()[:16]
        version = 'v-' + signature
        target = self.runtime / 'snapshots' / version
        staging = self.runtime / 'snapshots' / ('.building-' + uuid.uuid4().hex)
        staging.mkdir(parents=True)
        url = '/live-data/' + version
        try:
            if query_enabled:
                west, south, east, north = bbox
                area_ha = (6371008.8 ** 2 * math.radians(east-west)
                           * (math.sin(math.radians(north))-math.sin(math.radians(south))) / 10000)
                unit = {'id': query_id, 'name': f'Área de consulta {provider}', 'kind': 'region',
                    'category': 'Área de consulta (rectángulo)',
                    'source': f'Configuración CEMEC · {provider}; área aproximada',
                    'area_ha': round(area_ha, 2), 'bbox': bbox,
                    'center': [(west+east)/2, (south+north)/2],
                    'geometry_url': url + '/units/' + query_id + '.geojson'}
                catalog['units'] = [u for u in catalog['units'] if u['id'] != query_id] + [unit]
                atomic_json(staging / 'units' / (query_id+'.geojson'), {
                    'type': 'Feature', 'properties': unit,
                    'geometry': {'type': 'Polygon', 'coordinates': [
                        [[west,south],[east,south],[east,north],[west,north],[west,south]]]}})
            days, months = defaultdict(list), defaultdict(list)
            stats = {}
            for point in points:
                days[point['date']].append(point)
                months[point['date'][:7]].append(point)
                for unit in point['units']:
                    key = (unit, point['date'], point['satellite'], point['confidence'])
                    entry = stats.setdefault(key, {'unit': unit, 'date': point['date'], 'satellite': point['satellite'],
                        'confidence': point['confidence'], 'count': 0, 'frp_sum': 0., 'frp_count': 0})
                    entry['count'] += 1
                    if point['frp'] is not None:
                        entry['frp_sum'] += point['frp']
                        entry['frp_count'] += 1
            catalog['partitions'] = []
            for day, rows in sorted(days.items()):
                atomic_json(staging / 'points' / f'{day}.json', rows)
                parquet = f'parquet/{day[:4]}/{day[5:7]}/{day}.parquet'
                self.write_parquet(staging / parquet, rows)
                catalog['partitions'].append({'date': day, 'count': len(rows),
                    'url': f'{url}/points/{day}.json', 'parquet_url': f'{url}/{parquet}'})
            catalog['web_partitions'] = []
            for month, rows in sorted(months.items()):
                atomic_json(staging / 'web' / f'{month}.json', rows)
                unit_rows = defaultdict(list)
                for row in rows:
                    for unit in row['units']:
                        unit_rows[unit].append(row)
                for unit, subset in unit_rows.items():
                    atomic_json(staging / 'web' / unit / f'{month}.json', subset)
                catalog['web_partitions'].append({'month': month, 'start': rows[0]['date'], 'end': rows[-1]['date'],
                    'count': len(rows), 'url': f'{url}/web/{month}.json',
                    'unit_counts': {unit: len(subset) for unit, subset in unit_rows.items()}})
            atomic_json(staging / 'statistics.json', list(stats.values()))
            catalog.update(version=version, generated_at=utc_now(), total_points=len(points),
                date_min=points[0]['date'], date_max=points[-1]['date'],
                satellites=sorted({p['satellite'] for p in points}), statistics_url=url+'/statistics.json',
                note=f'Actualización CEMEC. Nuevas: {added}; repetidas: {duplicates}; rechazadas: {provenance["rejected"]}.')
            atomic_json(staging / 'catalog.json', catalog)
            result.update(dataset=version, published=True)
            atomic_json(staging / 'manifest.json', {'parent_dataset': self.catalog()['version'],
                'boundary_version': catalog['boundary_version'], 'result': result})
            if target.exists():
                shutil.rmtree(staging)
            else:
                os.replace(staging, target)
            # La publicación se realiza solo después de escribir todo el snapshot.
            self.record_active(catalog, result, kind)
            return result
        finally:
            if staging.exists():
                shutil.rmtree(staging)

    @staticmethod
    def write_parquet(path, rows):
        path.parent.mkdir(parents=True, exist_ok=True)
        keys = set().union(*(row.keys() for row in rows))
        table = pa.Table.from_pylist([{**{key: row.get(key) for key in sorted(keys)},
            'geometry': Point(row['lon'], row['lat']).wkb} for row in rows])
        metadata = dict(table.schema.metadata or {})
        metadata[b'geo'] = json.dumps({'version': '1.0.0', 'primary_column': 'geometry', 'columns': {
            'geometry': {'encoding': 'WKB', 'geometry_types': ['Point']}}}).encode()
        pq.write_table(table.replace_schema_metadata(metadata), path, compression='zstd')

    def record_active(self, catalog, result, kind):
        active = self.runtime / 'active.json'
        state = read_json(active) if active.is_file() else {}
        state['catalog'] = catalog
        state.setdefault('last_sync', None)
        state.setdefault('last_eumetsat_sync', None)
        if kind in ('sync', 'eumetsat'):
            state['last_sync' if kind == 'sync' else 'last_eumetsat_sync'] = result
        atomic_json(active, state)

    def submit_import(self, filename, content):
        suffix = Path(filename).suffix.lower()
        if suffix not in ('.csv', '.json', '.geojson'):
            raise ValueError('El servicio local admite CSV y GeoJSON de puntos. Para otros formatos usa primero una conversión a GeoJSON.')
        return self.new_job('import', self.import_points, (Path(filename).name, content))

    def import_points(self, job_id, filename, content):
        text = content.decode('utf-8-sig')
        if filename.lower().endswith('.csv'):
            rows = list(csv.DictReader(io.StringIO(text)))
        else:
            document = json.loads(text)
            if document.get('type') != 'FeatureCollection':
                raise ValueError('Se requiere un GeoJSON FeatureCollection en WGS84.')
            crs = document.get('crs')
            if crs and not any(x in json.dumps(crs).upper() for x in ('4326', 'CRS84')):
                raise ValueError('Convierte el GeoJSON a WGS84 (EPSG:4326) antes de importarlo.')
            rows = [{**(f.get('properties') or {}), 'longitude': f['geometry']['coordinates'][0],
                     'latitude': f['geometry']['coordinates'][1]} for f in document['features']
                    if f.get('geometry') and f['geometry']['type'] == 'Point']
        points, rejected = [], 0
        for row in rows:
            try:
                point = normalize_row(row, source='Archivo · ' + filename)
                self.assign_units(point)
                points.append(point)
            except (ValueError, TypeError, OverflowError):
                rejected += 1
        if not points:
            raise ValueError('El archivo no contiene detecciones válidas.')
        return self.publish(points, {'job_id': job_id, 'received': len(rows), 'rejected': rejected,
                            'at': utc_now(), 'filename': filename}, kind='import')

def handler_for(store, token):
    olci = OlciService(store)
    store.olci = olci
    sentinel2 = QuarterlyMosaicService(store)
    store.sentinel2 = sentinel2
    imagery_services = {'olci':olci, 'sentinel2':sentinel2}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Evita registrar cuerpos o credenciales.

        def send_json(self, status, data):
            content = json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(content)

        def authorized(self):
            if not secrets.compare_digest(self.headers.get('X-CEMEC-Token', ''), token):
                self.send_json(403, {'detail': 'Acceso interno no autorizado'})
                return False
            return True

        def do_GET(self):
            if not self.authorized():
                return
            path = unquote(urlsplit(self.path).path)
            parts = path.split('/')
            imagery = imagery_services.get(parts[2]) if len(parts)>2 and parts[1]=='api' else None
            if imagery and path == f'{imagery.api_prefix}/status':
                status={'configured': imagery.configured(), 'busy': imagery.busy()}
                if imagery is sentinel2:
                    status['detail_limits']={
                        'enabled':imagery.settings.get('detail_enabled',True),
                        'max_area_km2':imagery.settings.get('detail_max_area_km2',400),
                        'max_width_km':imagery.settings.get('detail_max_width_km',30),
                        'max_image_side':imagery.settings.get('detail_max_image_side',1024),
                        'grid_m':imagery.settings.get('detail_grid_m',200)}
                return self.send_json(200,status)
            if imagery and path.startswith(f'{imagery.api_prefix}/jobs/'):
                job = imagery.job(path.rsplit('/', 1)[-1])
                return self.send_json(200 if job else 404, job or {'detail': 'Consulta no encontrada'})
            if imagery and path.startswith(f'{imagery.api_prefix}/images/'):
                try:
                    file = imagery.image_file(path.rsplit('/', 1)[-1])
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/png' if file.suffix == '.png' else 'application/json; charset=utf-8')
                    self.send_header('Content-Length', str(file.stat().st_size))
                    self.send_header('Cache-Control', 'public, max-age=31536000, immutable')
                    self.end_headers()
                    if self.command != 'HEAD':
                        with file.open('rb') as stream: shutil.copyfileobj(stream, self.wfile)
                    return
                except (ValueError, OSError):
                    return self.send_json(404, {'detail': 'Imagen no encontrada'})
            if path == '/api/status':
                return self.send_json(200, store.status())
            if path == '/data/catalog.json':
                return self.send_json(200, store.catalog())
            if path.startswith('/api/jobs/'):
                with store.lock:
                    job = deepcopy(store.jobs.get(path.rsplit('/', 1)[-1]))
                return self.send_json(200 if job else 404, job or {'detail': 'Tarea no encontrada'})
            if path.startswith('/live-data/'):
                try:
                    file = store.resolve_url(path)
                    if not file.is_file() or any(part.startswith('.') for part in Path(path).parts):
                        raise ValueError('Archivo no encontrado')
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8' if file.suffix == '.json' else 'application/octet-stream')
                    self.send_header('Content-Length', str(file.stat().st_size))
                    self.send_header('Cache-Control', 'public, max-age=31536000, immutable')
                    self.end_headers()
                    if self.command != 'HEAD':
                        with file.open('rb') as stream:
                            shutil.copyfileobj(stream, self.wfile)
                    return
                except (ValueError, OSError):
                    return self.send_json(404, {'detail': 'Archivo no encontrado'})
            self.send_json(404, {'detail': 'Ruta no disponible'})

        do_HEAD = do_GET

        def do_POST(self):
            if not self.authorized():
                return
            path = urlsplit(self.path).path
            try:
                limit = 20 * 1024 * 1024 if path == '/api/import' else 16384
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= limit:
                    return self.send_json(413, {'detail': 'Tamaño de solicitud inválido; importaciones hasta 20 MB.'})
                content = self.rfile.read(length)
                parts = path.split('/')
                imagery = imagery_services.get(parts[2]) if len(parts)>2 and parts[1]=='api' else None
                if imagery and (path in (f'{imagery.api_prefix}/search', f'{imagery.api_prefix}/render') or imagery is sentinel2 and path==f'{imagery.api_prefix}/detail'):
                    if not self.headers.get('Content-Type', '').startswith('application/json'):
                        return self.send_json(415, {'detail': 'Se requiere application/json'})
                    return self.send_json(202, imagery.submit(path.rsplit('/', 1)[-1], json.loads(content)))
                if path in ('/api/sync', '/api/eumetsat/sync'):
                    if not self.headers.get('Content-Type', '').startswith('application/json'):
                        return self.send_json(415, {'detail': 'Se requiere application/json'})
                    request = json.loads(content)
                    if not isinstance(request, dict):
                        raise ValueError('Solicitud inválida')
                    return self.send_json(202, store.submit_eumetsat(request) if path == '/api/eumetsat/sync' else store.submit(request))
                if path == '/api/import':
                    content_type = self.headers.get('Content-Type', '')
                    if not content_type.startswith('multipart/form-data;'):
                        raise ValueError('Se requiere un archivo multipart/form-data')
                    document = BytesParser(policy=email_policy).parsebytes(
                        f'Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n'.encode() + content)
                    for part in document.iter_parts():
                        if part.get_param('name', header='content-disposition') == 'file' and part.get_filename():
                            return self.send_json(202, store.submit_import(part.get_filename(), part.get_payload(decode=True)))
                    raise ValueError('Falta el archivo de importación')
                return self.send_json(404, {'detail': 'Ruta no disponible'})
            except RuntimeError as error:
                self.send_json(409, {'detail': str(error)})
            except (ValueError, TypeError, UnicodeError, KeyError):
                # Los mensajes de ValueError propios no contienen la clave.
                import sys
                error = sys.exception()
                detail = str(error) if type(error) is ValueError else 'Solicitud inválida'
                self.send_json(400, {'detail': detail})
    return Handler

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--ready-file', type=Path, required=True)
    args = parser.parse_args()
    load_environment(args.config.resolve().parent)
    token = os.environ['CEMEC_INTERNAL_TOKEN']
    store = Store(args.config)
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(store, token))
    atomic_json(args.ready_file, {'port': server.server_port})
    try:
        server.serve_forever()
    finally:
        server.server_close()
        store.executor.shutdown(wait=True)
        if hasattr(store, 'olci'): store.olci.executor.shutdown(wait=True)
        if hasattr(store, 'sentinel2'): store.sentinel2.executor.shutdown(wait=True)

if __name__ == '__main__':
    main()
