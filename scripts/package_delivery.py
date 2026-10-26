"""Construye entregas ZIP; las claves solo se incluyen con opción explícita."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
ROOT = 'CEMEC_plataforma'


def refs(value):
    if isinstance(value, dict):
        return set().union(set(), *(refs(v) for v in value.values()))
    if isinstance(value, list):
        return set().union(set(), *(refs(v) for v in value))
    if isinstance(value, str):
        match = re.match(r'^/live-data/(v-[A-Za-z0-9_-]+)/', value)
        return {match[1]} if match else set()
    return set()


def credential_values():
    values = {}
    env = PROJECT / '.env'
    if env.is_file():
        for line in env.read_text().splitlines():
            key, sep, value = line.partition('=')
            value = value.strip().strip('\"\'')
            if sep and key.strip() in {'FIRMS_MAP_KEY', 'EUMETSAT_CONSUMER_KEY',
                    'EUMETSAT_CONSUMER_SECRET', 'CDSE_CLIENT_ID', 'CDSE_CLIENT_SECRET'} and value:
                values[key.strip()] = value
    return values


def private_patterns():
    values = credential_values()
    patterns = {v.encode() for v in values.values()}
    for key, secret in [('EUMETSAT_CONSUMER_KEY', 'EUMETSAT_CONSUMER_SECRET'),
                        ('CDSE_CLIENT_ID', 'CDSE_CLIENT_SECRET')]:
        if key in values and secret in values:
            patterns.add(base64.b64encode((values[key] + ':' + values[secret]).encode()))
    return patterns


def scan(data, name, patterns, depth=0):
    if depth > 8:
        raise ValueError('Anidación excesiva: ' + name)
    if any(pattern in data for pattern in patterns):
        raise ValueError('Credencial privada detectada; no se empaqueta: ' + name)
    if re.search(rb'-----BEGIN (?:RSA )?PRIVATE KEY-----\s+[A-Za-z0-9+/]{40,}', data):
        raise ValueError('Clave privada detectada: ' + name)
    if name.endswith(('.zip', '.docx')):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for entry in archive.infolist():
                if not entry.is_dir():
                    if Path(entry.filename).name == '.env':
                        raise ValueError('Archivo .env anidado: ' + name)
                    scan(archive.read(entry), name + '!' + entry.filename, patterns, depth + 1)
    elif name.endswith(('.tar.gz', '.tgz')):
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
            for entry in archive:
                if entry.isfile():
                    if Path(entry.name).name == '.env':
                        raise ValueError('Archivo .env anidado: ' + name)
                    scan(archive.extractfile(entry).read(), name + '!' + entry.name, patterns, depth + 1)


VERIFIER = '''"""Verifica los archivos originales de esta entrega, sin acceder a Internet."""
from pathlib import Path
import hashlib
import json
import sys
base = Path(__file__).resolve().parent
manifest = json.loads((base / 'MANIFIESTO-SHA256.json').read_text(encoding='utf-8'))
errors = []
for entry in manifest['files']:
    path = (base / entry['path']).resolve()
    if not path.is_relative_to(base) or not path.is_file():
        errors.append(entry['path'])
        continue
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if path.stat().st_size != entry['bytes'] or digest != entry['sha256']:
        errors.append(entry['path'])
if errors:
    print('Archivos ausentes o modificados:', *errors, sep='\\n')
    sys.exit(1)
print(f"Entrega íntegra: {len(manifest['files'])} archivos comprobados.")
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-credentials', action='store_true',
        help='Entrega privada autorizada: incluye las cinco credenciales de API en .env.')
    args = parser.parse_args()
    credentials = credential_values() if args.include_credentials else {}
    if args.include_credentials and len(credentials) != 5:
        raise ValueError('La entrega privada requiere las cinco variables de API configuradas.')
    files = {}
    def add(path):
        if path.is_symlink():
            raise ValueError('No se admiten enlaces simbólicos: ' + str(path))
        if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
            files[path.relative_to(PROJECT).as_posix()] = path
    for folder in ('cemec-sitio-estatico', 'ui', 'scripts', 'tests', 'docs', 'origen', 'respaldos'):
        for path in (PROJECT / folder).rglob('*'):
            add(path)
    for name in ('README.md', 'LEEME-PRIMERO.md', 'Setup-CEMEC.sh', 'Start-CEMEC.sh',
                 'serve.js', 'config.yaml', 'environment.yml', 'environment-linux-64.lock.txt',
                 '.env.example', '.gitignore'):
        add(PROJECT / name)
    active_bytes = (PROJECT / 'runtime/firms/active.json').read_bytes()
    active = json.loads(active_bytes)
    versions, pending = set(), refs(active) | {active['catalog']['version']}
    while pending:
        version = pending.pop()
        if version in versions:
            continue
        folder = PROJECT / 'runtime/firms/snapshots' / version
        catalog = folder / 'catalog.json'
        if not catalog.is_file():
            raise ValueError('Snapshot requerido ausente: ' + version)
        versions.add(version)
        pending.update(refs(json.loads(catalog.read_text())) - versions)
        for path in folder.rglob('*'):
            add(path)
    now = datetime.now(timezone.utc)
    metadata = {'created_at_utc': now.isoformat(), 'dataset': active['catalog']['version'],
        'total_points': active['catalog']['total_points'], 'date_min': active['catalog']['date_min'],
        'date_max': active['catalog']['date_max'], 'snapshot_versions': sorted(versions),
        'credentials_included': args.include_credentials, 'installed_environment_included': False,
        'windows_native_adaptation_pending': True,
        'excluded': ([] if args.include_credentials else ['.env']) + ['.conda-env', '.conda-pkgs', 'image caches', 'temporary downloads',
                     'task logs', 'visual QA artifacts', 'unreferenced operational snapshots'],
        'start_here': 'LEEME-PRIMERO.md'}
    virtual = {'runtime/firms/active.json': active_bytes,
        'ENTREGA.json': (json.dumps(metadata, ensure_ascii=False, indent=2) + '\n').encode(),
        'verificar-entrega.py': VERIFIER.encode()}
    if args.include_credentials:
        virtual['.env'] = ('# Entrega privada autorizada para pruebas con credenciales compartidas.\n' +
            '\n'.join(key + '=' + value for key, value in credentials.items()) + '\n').encode()
        readme = (PROJECT / 'LEEME-PRIMERO.md').read_text()
        readme = readme.replace('# Entrega de CEMEC Plataforma',
            '# Entrega PRIVADA de CEMEC Plataforma con APIs configuradas\n\n'
            'Esta edición incluye las credenciales compartidas del responsable, con su '
            'autorización para pruebas entre colegas. No hace falta crear ni modificar '
            '`.env` para probar las APIs. Los accesos y el consumo corresponden a la '
            'misma cuenta de origen. Entrega exclusiva al grupo acordado; no publicar '
            'este ZIP ni `.env`. El responsable reemplazará las claves después de las pruebas.\n\n'
            'Los manuales describen la entrega general sin secretos. En esta edición '
            'privada, sus instrucciones para crear `.env` o aportar claves propias '
            'solo son necesarias al reemplazar las credenciales incluidas. '
            'La instalación de Conda y las consideraciones de Windows siguen vigentes.')
        readme = readme.replace('## Credenciales propias', '## Credenciales incluidas para pruebas')
        readme = readme.replace('La entrega **no contiene claves personales**. El histórico y las detecciones\nincluidas se pueden consultar sin credenciales. Para sincronizar datos nuevos o\nsolicitar imágenes, cree `.env` a partir de `.env.example` en el equipo servidor:',
            'Las cinco variables siguientes ya están configuradas en `.env`. '
            'El servidor las carga al arrancar. Para reemplazarlas, edite ese archivo '
            'en el equipo servidor; `.env.example` conserva una plantilla vacía:')
        readme = readme.replace('y solicitar las credenciales propias del nuevo responsable.',
            'y utilizar las credenciales ya incluidas durante las pruebas autorizadas.')
        virtual['LEEME-PRIMERO.md'] = readme.encode()
    output_dir = PROJECT / 'entregas'
    output_dir.mkdir(exist_ok=True)
    prefix = 'CEMEC_Plataforma_PRIVADA_con_APIs_' if args.include_credentials else 'CEMEC_Plataforma_colegas_'
    output = output_dir / (prefix + now.strftime('%Y%m%d_%H%M%S') + '.zip')
    patterns, entries = private_patterns(), []
    partial = output.with_suffix('.zip.partial')
    with zipfile.ZipFile(partial, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in sorted(files.keys() | virtual.keys()):
            data = virtual[name] if name in virtual else files[name].read_bytes()
            if name != '.env':
                scan(data, name, patterns)
            entry = zipfile.ZipInfo(ROOT + '/' + name, now.timetuple()[:6])
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = (0o100600 if name == '.env' else 0o100755 if name.endswith('.sh') else 0o100644) << 16
            archive.writestr(entry, data)
            entries.append({'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        manifest = {'algorithm': 'SHA-256', 'files': entries,
                    'note': 'El manifiesto no se incluye a sí mismo; el SHA-256 del ZIP se entrega por separado.'}
        archive.writestr(ROOT + '/MANIFIESTO-SHA256.json',
                         json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    with zipfile.ZipFile(partial) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP corrupto')
    partial.rename(output)
    with output.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    output.with_suffix('.zip.sha256').write_text(digest + '  ' + output.name + '\n')
    summary = {**metadata, 'archive': str(output.relative_to(PROJECT)), 'sha256': digest,
        'archive_bytes': output.stat().st_size, 'uncompressed_bytes': sum(x['bytes'] for x in entries),
        'file_count': len(entries) + 1, 'zip_crc_verified': True,
        'known_private_credentials_scan_including_nested_archives':
            'passed_except_explicitly_authorized_root_env' if args.include_credentials else 'passed'}
    output.with_suffix('.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    pointer = 'ultima-entrega-privada.json' if args.include_credentials else 'ultima-entrega.json'
    (output_dir / pointer).write_text(json.dumps({'archive': summary['archive']}, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
