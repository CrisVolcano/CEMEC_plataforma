"""Verifica entradas, extrae sin sobreescribir cambios y audita la copia."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
import yaml

PROJECT = Path(__file__).resolve().parents[1]

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=PROJECT / 'config.yaml')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = yaml.safe_load(config_path.read_text())
    base = config_path.parent
    artifacts = config['artifacts']
    for key in ('archive', 'manual'):
        src = base / artifacts[key]
        # Un checkout contiene la compilación descomprimida y su manifiesto.
        # Los originales privados son opcionales; si se aportan se verifican.
        if src.is_file() and digest(src) != artifacts[key + '_sha256']:
            raise ValueError(f'Checksum incorrecto: {src.name}')
    root = (base / config['server']['root']).resolve()
    manifest = json.loads((base / artifacts['original_manifest']).read_text())['files']
    archive_path = base / artifacts['archive']
    if not args.verify_only and not archive_path.is_file():
        missing = [item['path'] for item in manifest if not (root / item['path']).is_file()]
        if missing:
            raise ValueError('Faltan archivos del sitio y el ZIP original para reconstruirlos. Restaura el checkout completo o proporciona artifacts.archive.')
    if not args.verify_only and archive_path.is_file():
        with zipfile.ZipFile(base / artifacts['archive']) as archive:
            for item in manifest:
                dest = (root / item['path']).resolve()
                if not dest.is_relative_to(root) or dest == root:
                    raise ValueError(f'Ruta insegura: {item["path"]}')
                if dest.exists():
                    if digest(dest) != item['sha256']:
                        raise ValueError(f'Archivo modificado, no se sobreescribe: {dest}')
                else:
                    content = archive.read(item['path'])
                    if hashlib.sha256(content).hexdigest() != item['sha256']:
                        raise ValueError(f'ZIP no coincide con manifiesto: {item["path"]}')
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(content)
    for item in manifest:
        dest = (root / item['path']).resolve()
        if not dest.is_relative_to(root) or not dest.is_file() or digest(dest) != item['sha256']:
            raise ValueError(f'Copia distinta al original: {item["path"]}')
    catalog = json.loads((root / 'data/catalog.json').read_text())
    for key in ('version', 'boundary_version', 'total_points', 'date_min', 'date_max'):
        if catalog[key] != config['dataset'][key]:
            raise ValueError(f'Catálogo y config.yaml no coinciden: {key}')
    if len(catalog['units']) != config['dataset']['territory_count']:
        raise ValueError('Número de territorios no coincide')
    # Comprueba todas las referencias locales declaradas en ambos catálogos.
    def check_urls(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if isinstance(child, str) and (key.endswith('_url') or key == 'url') and child.startswith('/'):
                    dest = (root / child.lstrip('/')).resolve()
                    if not dest.is_relative_to(root) or not dest.is_file():
                        raise ValueError(f'Recurso del catálogo ausente: {child}')
                else:
                    check_urls(child)
        elif isinstance(value, list):
            for child in value:
                check_urls(child)
    check_urls(catalog)
    check_urls(json.loads((root / 'products/catalog.json').read_text()))
    print(f'Copia íntegra: {len(manifest)} archivos; {catalog["total_points"]} detecciones; {len(catalog["units"])} territorios.')

if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, yaml.YAMLError) as error:
        raise SystemExit(f'Error: {error}')
