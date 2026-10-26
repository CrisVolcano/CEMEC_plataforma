"""Servidor de QA aislado. Simula FIRMS y nunca publica datos de prueba reales."""
import argparse
from datetime import datetime, timezone, timedelta
import io
from http.server import ThreadingHTTPServer
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import yaml

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'scripts'))
from firms_backend import Store, atomic_json, handler_for

parser = argparse.ArgumentParser()
parser.add_argument('--ready-file', type=Path, required=True)
parser.add_argument('--eumetsat', action='store_true')
parser.add_argument('--eumetsat-empty', action='store_true')
parser.add_argument('--olci', action='store_true')
parser.add_argument('--sentinel2', action='store_true')
args = parser.parse_args()
with tempfile.TemporaryDirectory(prefix='cemec-firms-ui-') as directory:
    base = Path(directory)
    config = yaml.safe_load((PROJECT / 'config.yaml').read_text())
    config['server']['root'] = str(PROJECT / 'cemec-sitio-estatico')
    config['firms']['storage'] = str(base / 'data')
    config['firms']['key_env'] = 'CEMEC_FIXTURE_KEY'
    config['eumetsat']['cache'] = str(base / 'eumetsat')
    config['eumetsat']['consumer_key_env'] = 'CEMEC_FIXTURE_EUM_KEY'
    config['eumetsat']['consumer_secret_env'] = 'CEMEC_FIXTURE_EUM_SECRET'
    config['olci']['cache'] = str(base / 'olci')
    config['sentinel2']['cache'] = str(base / 'sentinel2')
    config['sentinel2']['max_image_side'] = 128
    if args.eumetsat:
        os.environ['CEMEC_FIXTURE_EUM_KEY'] = 'synthetic-key'
        os.environ['CEMEC_FIXTURE_EUM_SECRET'] = 'synthetic-secret'
    os.environ['CEMEC_FIXTURE_KEY'] = 'a' * 32
    config_file = base / 'config.yaml'
    config_file.write_text(yaml.safe_dump(config))
    store = Store(config_file)
    def download(key, product, bbox, days, start=None):
        row = {'latitude':'17.04416','longitude':'-90.58102',
            'acq_date':start or datetime.now(timezone.utc).date().isoformat(), 'acq_time':'0724',
            'satellite':'N', 'confidence':'h', 'frp':'12.5', 'daynight':'N','version':'QA'}
        return [row], b'SYNTHETIC QA ONLY'
    store.client.download = download
    if args.eumetsat:
        instant = datetime.now(timezone.utc) - timedelta(hours=1)
        class Product:
            entries = ['FRP_MWIR1km_standard.csv']
            sensing_start = instant
            sensing_end = instant + timedelta(minutes=3)
            def __init__(self, index):
                self.index = index
                self.satellite = 'S3A' if index < 8 else 'S3B'
            def __str__(self):
                return f'{self.satellite}_SL_2_FRP____SYNTHETIC_QA_{self.index}.SEN3'
            def open(self, entry):
                clock = (instant + timedelta(seconds=self.index)).strftime('%H:%M:%S')
                return io.BytesIO(('#processing_baseline = SYNTHETIC-QA\n#number_of_detected_fires = 1\n'
                    'lat(deg),lon(deg),day,time,D/N,FRP(MW),confidence(%),confidence_class(lower=0;nominal=1;higher=2),satellite\n'
                    f'17.04416,{"-100" if args.eumetsat_empty else "-90.58102"},{instant.date().isoformat()},{clock},N,12.5,90,{self.index%3},{self.satellite}\n').encode())
        products = [Product(index) for index in range(17)]
        store.eumetsat_client.search = lambda *args: (iter(products), len(products))
    token = secrets.token_hex(32)
    server = ThreadingHTTPServer(('127.0.0.1',0),handler_for(store,token))
    if args.olci or args.sentinel2:
        os.environ['CDSE_CLIENT_ID']='synthetic-id';os.environ['CDSE_CLIENT_SECRET']='synthetic-secret'
        import json
        from test_olci import png
        def olci_post(url,payload,accept):
            from olci_service import CATALOG
            if url==CATALOG:
                if payload['collections']==['byoc-5460de54-082e-473a-b6ea-d5cbe3c17cca']:
                    now=datetime.now(timezone.utc);first=datetime(now.year,1+3*((now.month-1)//3),1,tzinfo=timezone.utc)
                    previous=first-timedelta(days=1);stamp=datetime(previous.year,1+3*((previous.month-1)//3),1,tzinfo=timezone.utc)
                    if payload['datetime'].startswith('2024-01-01') and '/2024-03-31' in payload['datetime']: return b'{"features":[]}',{}
                    return json.dumps({'features':[{'id':'MOSAIC_SYNTHETIC_QA','geometry':{'type':'Polygon','coordinates':[[[-92,15],[-88,15],[-88,19],[-92,19],[-92,15]]]},'properties':{'datetime':stamp.isoformat()}}]}).encode(),{}
                day=(datetime.now(timezone.utc)-timedelta(days=1)).date().isoformat() if payload['datetime'].startswith(str(datetime.now(timezone.utc).year)) else '2024-01-01'
                if payload['datetime'].startswith('2024-01-01'): return b'{"features":[]}',{}
                is_s2=payload['collections']==['sentinel-2-l2a']
                return json.dumps({'features':[{'id':'S2C_MSIL2A_SYNTHETIC_QA' if is_s2 else 'S3B_OL_SYNTHETIC_QA','geometry':{'type':'Polygon','coordinates':[[[-92,15],[-88,15],[-88,19],[-92,19],[-92,15]]]},'properties':{'datetime':day+'T16:00:00Z','eo:cloud_cover':42.3}}]}).encode(),{}
            return png(payload['output']['width'],payload['output']['height']),{}
        store.olci.post=olci_post
        store.sentinel2.post=olci_post
    threading.Thread(target=server.serve_forever,daemon=True).start()
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
    env={**os.environ,'CEMEC_BACKEND_PORT':str(server.server_port),'CEMEC_INTERNAL_TOKEN':token}
    process=subprocess.Popen([str(Path(sys.executable).parent/'node'),str(PROJECT/'serve.js'),
        '--root',str(store.site),'--port',str(port)],env=env,stdout=subprocess.DEVNULL)
    done=threading.Event()
    for sig in (signal.SIGTERM,signal.SIGINT):
        signal.signal(sig,lambda *args: done.set())
    atomic_json(args.ready_file,{'port':port})
    try:
        done.wait()
    finally:
        store.executor.shutdown(wait=True)
        store.olci.executor.shutdown(wait=True)
        store.sentinel2.executor.shutdown(wait=True)
        process.terminate();process.wait(timeout=5)
        server.shutdown();server.server_close()
