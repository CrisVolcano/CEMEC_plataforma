"""Lanzador: lee config.yaml y usa Node.js del mismo entorno Conda."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import threading
import secrets
import tempfile
import time
import urllib.request
import webbrowser
import yaml

PROJECT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=PROJECT / 'config.yaml')
    parser.add_argument('--open-browser', action='store_true')
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = yaml.safe_load(config_path.read_text())
    if config.get('schema_version') != 1:
        raise ValueError('schema_version debe ser 1')
    settings = config['server']
    if settings.get('http_range') is not True:
        raise ValueError('PMTiles requiere server.http_range: true')
    root = (config_path.parent / settings['root']).resolve()
    if not (root / 'index.html').is_file():
        raise ValueError(f'Falta {root / "index.html"}. Ejecuta ./Setup-CEMEC.sh')
    node = Path(sys.executable).parent / 'node'
    if not node.is_file():
        raise ValueError('Node.js no está en este entorno. Ejecuta ./Setup-CEMEC.sh')
    host = os.environ.get('HOST', settings['host'])
    port = int(os.environ.get('PORT', settings['port']))
    if not 1 <= port <= 65535:
        raise ValueError('Puerto inválido')
    url = f'http://{"localhost" if host == "0.0.0.0" else host}:{port}'
    backend = None
    env = dict(os.environ)
    ready_dir = None
    layout = config.get('interface', {}).get('layout', 'modern')
    if layout not in ('modern', 'legacy'):
        raise ValueError('interface.layout debe ser modern o legacy')
    env.setdefault('CEMEC_LEGACY_UI', '1' if layout == 'legacy' else '0')
    if any(config.get(name, {}).get('enabled', False) for name in ('firms', 'eumetsat', 'olci', 'sentinel2')):
        env['CEMEC_INTERNAL_TOKEN'] = secrets.token_hex(32)
        ready_dir = tempfile.TemporaryDirectory(prefix='cemec-api-')
        ready_file = Path(ready_dir.name) / 'ready.json'
        backend = subprocess.Popen([sys.executable, str(PROJECT / 'scripts/firms_backend.py'),
            '--config', str(config_path), '--ready-file', str(ready_file)], env=env)
        try:
            for _ in range(300):
                if backend.poll() is not None:
                    raise ValueError('No se pudo iniciar el backend FIRMS. Ejecuta ./Setup-CEMEC.sh para instalar dependencias.')
                if ready_file.is_file():
                    import json
                    env['CEMEC_BACKEND_PORT'] = str(json.loads(ready_file.read_text())['port'])
                    break
                time.sleep(0.1)
            else:
                raise ValueError('El backend FIRMS no inició a tiempo.')
        except BaseException:
            backend.terminate()
            backend.wait()
            ready_dir.cleanup()
            raise
    try:
        process = subprocess.Popen([str(node), str(PROJECT / 'serve.js'), '--root', str(root), '--host', host, '--port', str(port)], env=env)
    except BaseException:
        if backend:
            backend.terminate()
            backend.wait()
            ready_dir.cleanup()
        raise
    def open_when_ready():
        for _ in range(30):
            if process.poll() is not None:
                return
            try:
                with urllib.request.urlopen(url, timeout=1) as response:
                    if response.status == 200:
                        webbrowser.open(url)
                        return
            except OSError:
                threading.Event().wait(0.2)
    if args.open_browser or settings.get('open_browser', False):
        threading.Thread(target=open_when_ready, daemon=True).start()
    try:
        return process.wait()
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=4)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        return 0
    finally:
        if backend:
            backend.terminate()
            try:
                backend.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend.kill()
                backend.wait()
            ready_dir.cleanup()

if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, yaml.YAMLError) as error:
        sys.exit(f'Error: {error}')
