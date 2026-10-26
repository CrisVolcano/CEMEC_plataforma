"""Prepara una copia Git revisable y audita archivos; nunca publica ni hace commits."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = ('scripts', 'ui', 'tests', 'docs', 'cemec-sitio-estatico', '.github', '.githooks')
FILES = ('README.md', 'LEEME-PRIMERO.md', 'NOTICE.md', 'SECURITY.md', 'CONTRIBUTING.md',
         'Setup-CEMEC.sh', 'Start-CEMEC.sh', 'serve.js', 'config.yaml', 'environment.yml',
         'environment-linux-64.lock.txt', '.env.example', '.gitignore', '.gitattributes')
PRIVATE_DIRS = {'.git', '.conda-env', '.conda-pkgs', 'node_modules', '__pycache__',
                'runtime', 'respaldos', '.respaldos', 'entregas', 'origen', 'output',
                '.aws', '.codex', '.agents', 'repositorio-github', '.github-preparacion'}
TOKEN = re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,})\b')
ASSIGNMENT = re.compile(rb'''(?i)\b(?:FIRMS_MAP_KEY|EUMETSAT_CONSUMER_(?:KEY|SECRET)|CDSE_CLIENT_(?:ID|SECRET))["']?[ \t]*[:=][ \t]*["']?([A-Za-z0-9_-]{20,})''')


def blocked(name):
    p = Path(name)
    return (p.is_absolute() or '..' in p.parts or bool(set(p.parts) & PRIVATE_DIRS)
            or (p.name.startswith('.env') and p.name != '.env.example')
            or p.suffix in {'.pyc', '.log', '.pem', '.key', '.p12'})


def candidates():
    paths = [ROOT / name for name in FILES if (ROOT / name).is_file()]
    for name in FOLDERS:
        paths.extend(p for p in (ROOT / name).rglob('*') if p.is_file())
    # Texto extraído del documento de origen: no es necesario para instalar.
    return sorted(p for p in paths if not blocked(p.relative_to(ROOT))
                  and p.relative_to(ROOT).as_posix() != 'docs/manual-extraido.txt')


def known_patterns():
    env = ROOT / '.env'
    values = {}
    if env.is_file():
        for line in env.read_text().splitlines():
            key, sep, value = line.partition('=')
            if sep and key.strip() in {'FIRMS_MAP_KEY', 'EUMETSAT_CONSUMER_KEY', 'EUMETSAT_CONSUMER_SECRET', 'CDSE_CLIENT_ID', 'CDSE_CLIENT_SECRET'}:
                value = value.strip().strip('"\'')
                if value:
                    values[key.strip()] = value
    patterns = {v.encode() for v in values.values()}
    for prefix in ('EUMETSAT_CONSUMER', 'CDSE_CLIENT'):
        key = prefix + ('_KEY' if prefix.startswith('EUMETSAT') else '_ID')
        secret = prefix + '_SECRET'
        if key in values and secret in values:
            patterns.add(base64.b64encode((values[key]+':'+values[secret]).encode()))
    return patterns


def inspect_blob(data, name, patterns, depth=0):
    if depth > 6:
        raise ValueError('Archivo comprimido con demasiados niveles: ' + name)
    if len(data) >= 100 * 1024 * 1024:
        raise ValueError('Archivo de 100 MiB o más: ' + name)
    if any(value in data for value in patterns):
        raise ValueError('Credencial local detectada en ' + name)
    if TOKEN.search(data) or re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', data):
        raise ValueError('Token o clave privada detectada en ' + name)
    if ASSIGNMENT.search(data):
        raise ValueError('Valor de credencial incrustado en ' + name)
    if name.endswith(('.docx', '.zip')):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for item in archive.infolist():
                if item.is_dir():
                    continue
                if item.file_size >= 100 * 1024 * 1024 or blocked(item.filename):
                    raise ValueError('Contenido privado o excesivo en ' + name)
                inspect_blob(archive.read(item), name+'!'+item.filename, patterns, depth+1)


def git(*args, cwd=None, **kwargs):
    return subprocess.run(['git', '-C', str(cwd or ROOT), *args], check=True, capture_output=True, **kwargs)


def audit(staged=False):
    patterns = known_patterns()
    if staged:
        names = git('ls-files', '-z').stdout.decode().split('\0')
        entries = ((name, git('show', ':'+name).stdout) for name in names if name)
    else:
        entries = ((p.relative_to(ROOT).as_posix(), p.read_bytes()) for p in candidates())
    count, total, largest = 0, 0, []
    for name, data in entries:
        if blocked(name):
            raise ValueError('Archivo excluido presente en el índice: ' + name)
        inspect_blob(data, name, patterns)
        count += 1
        total += len(data)
        largest.append((len(data), name))
    if not count:
        raise ValueError('No hay archivos para revisar')
    return {'files': count, 'bytes': total, 'largest': [{'path': n, 'bytes': s} for s,n in sorted(largest, reverse=True)[:5]],
            'credential_findings': 0, 'scope': 'index' if staged else 'allowlist',
            'note': 'Busca credenciales locales conocidas, patrones de tokens y claves privadas; no garantiza detectar cualquier secreto.'}


def prepare(destination):
    report = audit()
    if destination.exists():
        raise ValueError('La carpeta destino ya existe; no se sobrescribe: '+str(destination))
    destination.mkdir(parents=True)
    for src in candidates():
        if src.is_symlink():
            raise ValueError('No se copian enlaces simbólicos: '+str(src.relative_to(ROOT)))
        target = destination / src.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    git('init', '-b', 'main', cwd=destination)
    git('config', 'core.filemode', 'false', cwd=destination)
    git('config', 'core.hooksPath', '.githooks', cwd=destination)
    git('add', '--all', cwd=destination)
    names = git('ls-files', '-z', cwd=destination).stdout.decode().split('\0')
    git('update-index', '--chmod=-x', '--', *(n for n in names if n), cwd=destination)
    git('update-index', '--chmod=+x', '--', 'Start-CEMEC.sh', 'Setup-CEMEC.sh', '.githooks/pre-commit', cwd=destination)
    report.update({'destination': str(destination), 'branch': 'main', 'commit_created': False, 'remote_configured': False,
                   'source_static_manifest': hashlib.sha256((ROOT/'docs/original-manifest.json').read_bytes()).hexdigest()})
    subprocess.run([sys.executable, str(destination/'scripts/github_repository.py'), 'audit', '--staged'], check=True, stdout=subprocess.DEVNULL)
    output = ROOT / '.github-preparacion'
    output.mkdir(exist_ok=True)
    (output/'preparacion.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    review = subs.add_parser('audit')
    review.add_argument('--staged', action='store_true', help='Revisa los bytes del índice de Git, no solo el directorio de trabajo')
    build = subs.add_parser('prepare')
    build.add_argument('--destination', type=Path, default=ROOT/'repositorio-github')
    args = parser.parse_args()
    result = audit(args.staged) if args.command == 'audit' else prepare(args.destination.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        # Nunca imprimir stdout/stderr de Git ni fragmentos que puedan contener claves.
        print('Error: '+(str(exc) if not isinstance(exc, subprocess.CalledProcessError) else 'Falló una operación local de Git.'), file=sys.stderr)
        sys.exit(1)
