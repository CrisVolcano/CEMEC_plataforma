"""Sentinel-3 SLSTR FRP: EUMDAC, CSV estándar y credenciales solo en servidor."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import re
import time


class EumetsatError(ValueError):
    def __init__(self, message, code='eumetsat_unavailable', http_status=None):
        super().__init__(message)
        self.code, self.http_status = code, http_status


def service_error(error):
    info = getattr(error, 'extra_info', None) or {}
    status = info.get('status')
    response = getattr(getattr(error, '__cause__', None), 'response', None)
    if status is None and response is not None:
        status = response.status_code
    # No incluir str(error), URLs ni el cuerpo de la respuesta en registros públicos.
    if status == 403 and 'copernicus license required' in json.dumps(info.get('exceptions', [])).lower():
        return EumetsatError('El servicio de descarga EUMETSAT respondió HTTP 403 indicando que requiere la licencia Copernicus. Si ya figura activa en tu cuenta, revisa su vinculación con las credenciales API o contacta con soporte EUMETSAT. El catálogo publicado se conserva.', 'copernicus_license_required', 403)
    if status == 401:
        return EumetsatError('EUMETSAT rechazó la autenticación; revisa las credenciales del servidor.', 'authentication_failed', 401)
    return EumetsatError(f'EUMETSAT no pudo completar la descarga/búsqueda{f" (HTTP {status})" if status else ""}. El catálogo publicado se conserva.', http_status=status)


def field_name(value):
    return re.sub(r'[^a-z0-9]', '', value.lower())


LAT = {'latdeg', 'latitude', 'lat', 'latitudemwir', 'latitudemwir1km'}
LON = {'londeg', 'longitude', 'lon', 'longitudemwir', 'longitudemwir1km'}


def read_csv(content):
    text = content.decode('utf-8-sig')
    metadata = {}
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.lstrip().startswith('#'):
            key, sep, value = line.lstrip()[1:].partition('=')
            if sep:
                metadata[key.strip()] = value.strip()
        header = line.lstrip().lstrip('#').strip()
        for delimiter in (',', ';', '\t'):
            columns = next(csv.reader([header], delimiter=delimiter))
            names = {field_name(c.strip()) for c in columns}
            if names & LAT and names & LON:
                reader = csv.DictReader(io.StringIO('\n'.join([header] + [l for l in lines[index+1:] if not l.lstrip().startswith('#')])), delimiter=delimiter)
                raw_rows = list(reader)
                if any(None in row or any(value is None for value in row.values()) for row in raw_rows):
                    raise ValueError('CSV EUMETSAT incompleto.')
                rows = [{str(k).strip(): v for k, v in r.items()} for r in raw_rows]
                declared = metadata.get('number_of_detected_fires')
                if declared is not None and (not declared.isdigit() or int(declared) != len(rows)):
                    raise ValueError('El número de detecciones declarado no coincide con el CSV EUMETSAT.')
                return rows, metadata
    if metadata.get('number_of_detected_fires') == '0':
        return [], metadata
    raise ValueError('CSV EUMETSAT sin encabezado reconocido; no equivale a ausencia de detecciones.')


def normalize_detection(row, product_id, entry, metadata):
    values = {field_name(k): v.strip() if isinstance(v, str) else v for k, v in row.items()}

    def get(aliases, required=True):
        keys = [k for k in values if k in aliases]
        if len(keys) != 1:
            if not keys and not required:
                return None
            raise ValueError('Campos del CSV EUMETSAT ausentes o ambiguos.')
        return values[keys[0]]

    lat, lon = float(get(LAT)), float(get(LON))
    frp = float(get({'frpmw', 'frp', 'frpmwir', 'frpmwir1km'}))
    if not math.isfinite(lat + lon + frp) or not (-90 <= lat <= 90 and -180 <= lon <= 180) or frp < 0:
        raise ValueError('Coordenadas o FRP inválidas en Sentinel-3.')
    day = get({'day', 'date', 'acqdate'})
    clock = get({'time', 'acqtime', 'timeutc'})
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day) or not re.fullmatch(r'\d{2}:\d{2}:\d{2}(?:\.\d+)?', clock):
        raise ValueError('Fecha/hora UTC del CSV EUMETSAT no reconocida.')
    instant = datetime.fromisoformat(day + 'T' + clock).replace(tzinfo=timezone.utc)
    mission = 'Sentinel-3A' if product_id.startswith('S3A_') else 'Sentinel-3B' if product_id.startswith('S3B_') else None
    if mission is None:
        raise ValueError('Satélite Sentinel-3 desconocido.')
    raw_sat = get({'satellite'}, required=False)
    if raw_sat and raw_sat not in (product_id[:3], mission):
        raise ValueError('El satélite del CSV no corresponde al producto.')
    # Collection 3.2 declara la clasificación en el propio encabezado. No usar
    # los umbrales porcentuales de MODIS/VIIRS para SLSTR.
    class_key = 'confidenceclasslower0nominal1higher2'
    raw_class = values.get(class_key)
    confidence = {'0': 'l', '1': 'n', '2': 'h'}.get(raw_class, 'unknown')
    identity = f'EUMETSAT|{mission}|SLSTR|MWIR1km_standard|{instant.isoformat()}|{lat:.6f}|{lon:.6f}'
    return {'id': hashlib.sha256(identity.encode()).hexdigest()[:20], 'lat': lat, 'lon': lon,
            'date': day, 'time': instant.strftime('%H%M'), 'observation_utc': instant.isoformat(),
            'satellite': mission, 'instrument': 'SLSTR', 'confidence': confidence,
            'confidence_class': raw_class, 'confidence_scheme': 'SLSTR · clasificación original del producto',
            'frp': frp, 'daynight': values.get('dn') if values.get('dn') in ('D', 'N') else '',
            'source': 'EUMETSAT · Sentinel-3 SLSTR FRP · MWIR estándar',
            'product_version': metadata.get('processing_baseline', ''), 'product_id': product_id,
            'entry': entry, 'raw_fields': json.dumps(row, ensure_ascii=False, sort_keys=True), 'units': []}


class EumetsatClient:
    def __init__(self, settings, cache):
        self.settings, self.cache = settings, Path(cache)

    def search(self, credentials, start, end, bbox):
        import eumdac
        import eumdac.request
        from eumdac.logging import logger
        # El SDK puede registrar URLs de descarga con parámetros sensibles.
        logger.disabled = True
        original = getattr(eumdac.request._request, '_cemec_original', eumdac.request._request)

        def bounded_request(method, url, **kwargs):
            kwargs.setdefault('timeout', self.settings.get('timeout_seconds', 60))
            kwargs.setdefault('max_retries', self.settings.get('retries', 2))
            return original(method, url, **kwargs)

        bounded_request._cemec_original = original
        eumdac.request._request = bounded_request
        try:
            token = eumdac.AccessToken(credentials)
            str(token)  # Validar OAuth antes de una búsqueda que podría ser pública.
            collection = eumdac.DataStore(token).get_collection(self.settings['collection'])
            results = collection.search(dtstart=start, dtend=end, bbox=','.join(map(str, bbox)))
            return results, len(results)
        except Exception as error:
            raise service_error(error) from None

    def products(self, results):
        try:
            yield from results  # EUMDAC recorre todas las páginas; sin islice/límite.
        except Exception as error:
            raise service_error(error) from None

    def fetch(self, product):
        try:
            entries = [entry for entry in product.entries if Path(entry).name.lower() == 'frp_mwir1km_standard.csv']
        except Exception as error:
            raise service_error(error) from None
        if len(entries) != 1:
            raise ValueError('El producto EUMETSAT no tiene un único CSV MWIR estándar. No se publicó una actualización parcial.')
        product_id, entry = str(product), entries[0]
        # Identificador derivado: los nombres remotos nunca se convierten en rutas.
        identifier = hashlib.sha256((product_id + '|' + entry).encode()).hexdigest()
        directory = self.cache / 'products' / identifier
        destination, manifest = directory / 'original.csv', directory / 'manifest.json'
        if destination.is_file() and manifest.is_file():
            cached = json.loads(manifest.read_text())
            content = destination.read_bytes()
            if cached.get('product') == product_id and cached.get('entry') == entry and cached.get('sha256') == hashlib.sha256(content).hexdigest():
                return content, {**cached, 'cached': True}
        directory.mkdir(parents=True, exist_ok=True)
        temporary = directory / 'original.csv.part'
        for attempt in range(self.settings.get('retries', 2) + 1):
            try:
                size = 0
                with product.open(entry=entry) as source, temporary.open('wb') as target:
                    while block := source.read(1024 * 1024):
                        size += len(block)
                        if size > 30 * 1024 * 1024:
                            raise ValueError('CSV EUMETSAT supera 30 MB.')
                        target.write(block)
                content = temporary.read_bytes()
                read_csv(content)  # No almacenar como válido un documento HTML/erróneo.
                info = {'product': product_id, 'entry': entry, 'bytes': size,
                        'sha256': hashlib.sha256(content).hexdigest(), 'cached': False,
                        'downloaded_at': datetime.now(timezone.utc).isoformat(),
                        'sensing_start': product.sensing_start.isoformat(), 'sensing_end': product.sensing_end.isoformat()}
                temporary.replace(destination)
                temp_manifest = directory / 'manifest.json.tmp'
                temp_manifest.write_text(json.dumps(info, ensure_ascii=False))
                temp_manifest.replace(manifest)
                return content, info
            except Exception as error:
                temporary.unlink(missing_ok=True)
                if isinstance(error, ValueError) and not hasattr(error, 'extra_info'):
                    raise
                safe = service_error(error)
                if safe.http_status in (401, 403, 404) or attempt == self.settings.get('retries', 2):
                    raise safe from None
                time.sleep(2 ** attempt)
