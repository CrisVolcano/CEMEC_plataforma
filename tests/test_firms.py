"""Pruebas deterministas; ninguna necesita MAP_KEY ni conexión a NASA."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
import http.client
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import pyarrow.parquet as pq
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from firms_backend import Store, FirmsClient, handler_for, normalize_row, atomic_json

KEY = 'a' * 32
TODAY = datetime.now(timezone.utc).date().isoformat()
ROW = {'latitude': '1', 'longitude': '1', 'acq_date': TODAY, 'acq_time': '815',
       'satellite': 'N', 'confidence': 'n', 'frp': '4.5', 'daynight': 'D', 'version': '2.0NRT'}

def polygon(x1, y1, x2, y2):
    return {'type': 'Polygon', 'coordinates': [[[x1,y1],[x2,y1],[x2,y2],[x1,y2],[x1,y1]]]}

class NormalizationTests(unittest.TestCase):
    def test_viirs_and_modis_fields(self):
        point = normalize_row(ROW, 'VIIRS_SNPP_NRT')
        self.assertEqual(point['satellite'], 'S-NPP')
        self.assertEqual(point['time'], '0815')
        self.assertEqual(point['frp'], 4.5)
        modis = normalize_row({**ROW, 'satellite': 'A', 'confidence': '85'}, 'MODIS_NRT')
        self.assertEqual(modis['satellite'], 'Aqua')
        self.assertEqual(modis['confidence'], 'h')
        self.assertEqual(modis['instrument'], 'MODIS')

    def test_invalid_records_rejected(self):
        for field, value in [('latitude', 'nan'), ('longitude', '181'), ('frp', '-1'),
                             ('acq_date', '2026-02-30'), ('acq_time', '2501'), ('confidence', '150')]:
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    normalize_row({**ROW, field: value}, 'VIIRS_SNPP_NRT')

    def test_api_contract_and_key_not_in_errors(self):
        payload = b'latitude,longitude,acq_date,acq_time\n'
        with patch('firms_backend.urlopen', return_value=io.BytesIO(payload)) as opened:
            rows, content = FirmsClient({'retries': 0}).download(KEY, 'VIIRS_SNPP_NRT', [0,0,2,2], 3)
            self.assertEqual(rows, [])
            self.assertIn('/VIIRS_SNPP_NRT/0,0,2,2/3', opened.call_args.args[0].full_url)
        from urllib.error import URLError
        with patch('firms_backend.urlopen', side_effect=URLError('https://example/' + KEY)):
            with self.assertRaises(ValueError) as error:
                FirmsClient({'retries': 0}).download(KEY, 'VIIRS_SNPP_NRT', [0,0,2,2], 1)
            self.assertNotIn(KEY, str(error.exception))

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.site = self.base / 'site'
        self.original = normalize_row({**ROW, 'latitude':'0.5', 'longitude':'0.5'}, 'VIIRS_SNPP_NRT')
        self.original.update(source='INAB · puntos de calor', units=['region-peten'])
        atomic_json(self.site / 'data/original/points.json', [self.original])
        features = [
            {'type':'Feature', 'properties':{'id':'region-peten'}, 'geometry':polygon(0,0,2,2)},
            {'type':'Feature', 'properties':{'id':'mun-test'}, 'geometry':polygon(.8,.8,1.2,1.2)},
        ]
        atomic_json(self.site / 'data/original/territories.geojson', {'type':'FeatureCollection','features':features})
        self.catalog = {'version':'original', 'boundary_version':'boundaries', 'units':[],
            'total_points':1, 'date_min':TODAY, 'date_max':TODAY,
            'territories_url':'/data/original/territories.geojson',
            'pmtiles_url':'/data/original/territories.pmtiles',
            'partitions':[{'date':TODAY,'count':1,'url':'/data/original/points.json'}]}
        atomic_json(self.site / 'data/catalog.json', self.catalog)
        config = {'server':{'root':'site'}, 'firms':{'storage':'runtime', 'bbox':[0,0,2,2],
                   'days':1,'sources':['VIIRS_SNPP_NRT'],'key_env':'CEMEC_TEST_KEY'}}
        (self.base / 'config.yaml').write_text(yaml.safe_dump(config))
        self.store = Store(self.base / 'config.yaml')
        self.addCleanup(lambda: self.store.executor.shutdown(wait=True))

    def fake_download(self, key, product, bbox, days, start=None):
        duplicate = {**ROW, 'latitude':'0.5','longitude':'0.5'}
        invalid = {**ROW, 'latitude':'nan'}
        return [ROW, duplicate, invalid], b'test-fixture-not-from-NASA'

    def wait_job(self, job_id):
        for _ in range(200):
            job = deepcopy(self.store.jobs[job_id])
            if job['status'] in ('completed','failed'):
                return job
            time.sleep(.025)
        self.fail('La tarea no terminó')

    def test_full_sync_dedup_spatial_downloads_and_repeat(self):
        self.store.client.download = self.fake_download
        submitted = self.store.submit({'key':KEY, 'days':1,'sources':['VIIRS_SNPP_NRT']})
        job = self.wait_job(submitted['id'])
        self.assertEqual(job['status'],'completed', job)
        result = job['result']
        self.assertEqual((result['received'],result['added'],result['duplicates'],result['rejected']),(3,1,1,1))
        catalog = self.store.catalog()
        self.assertEqual(catalog['total_points'],2)
        points = json.loads(self.store.resolve_url(catalog['partitions'][0]['url']).read_text())
        incoming = next(p for p in points if p['lat']==1)
        self.assertEqual(incoming['units'], ['mun-test','region-firms-area','region-peten'])
        query = next(u for u in catalog['units'] if u['id']=='region-firms-area')
        self.assertTrue(self.store.resolve_url(query['geometry_url']).is_file())
        self.assertEqual(next(p for p in points if p['lat']==.5)['source'], self.original['source'])
        parquet = pq.read_table(self.store.resolve_url(catalog['partitions'][0]['parquet_url']))
        self.assertEqual(parquet.num_rows,2)
        self.assertIn(b'geo',parquet.schema.metadata)
        web = catalog['web_partitions'][0]
        municipal = web['url'].replace('/web/','/web/mun-test/')
        self.assertEqual(len(json.loads(self.store.resolve_url(municipal).read_text())),1)
        self.assertEqual(json.loads((self.site/'data/catalog.json').read_text()),self.catalog)
        version = catalog['version']
        repeated = self.wait_job(self.store.submit({'key':KEY})['id'])
        self.assertEqual(repeated['status'],'completed',repeated)
        self.assertEqual(self.store.catalog()['version'],version)
        self.assertEqual(repeated['result']['added'],0)
        serialized = json.dumps(self.store.status())
        self.assertNotIn(KEY,serialized)
        for file in (self.base/'runtime/jobs').glob('*.json'):
            self.assertNotIn(KEY,file.read_text())

    def test_point_outside_legal_territories_visible_in_query_area(self):
        self.store.client.download = lambda *args: ([{**ROW,'latitude':'3','longitude':'3'}],b'outside-legal-bounds')
        self.store.settings['bbox']=[0,0,4,4]
        job=self.wait_job(self.store.submit({'key':KEY})['id'])
        self.assertEqual(job['status'],'completed',job)
        catalog=self.store.catalog()
        rows=json.loads(self.store.resolve_url(catalog['partitions'][0]['url']).read_text())
        point=next(p for p in rows if p['lat']==3)
        self.assertEqual(point['units'],['region-firms-area'])
        url=catalog['web_partitions'][0]['url'].replace('/web/','/web/region-firms-area/')
        self.assertEqual(len(json.loads(self.store.resolve_url(url).read_text())),2)

    def test_failed_product_keeps_catalog(self):
        def download(key, product, *args):
            if product=='MODIS_NRT':
                raise ValueError('Producto temporalmente no disponible')
            return [ROW],b'valid-first-product'
        self.store.client.download = download
        job = self.wait_job(self.store.submit({'key':KEY,'sources':['VIIRS_SNPP_NRT','MODIS_NRT']})['id'])
        self.assertEqual(job['status'],'failed')
        self.assertEqual(self.store.catalog(),self.catalog)
        self.assertFalse((self.base/'runtime/active.json').exists())

    def test_empty_csv_preserves_history(self):
        self.store.client.download = lambda *args: ([],b'headers')
        job = self.wait_job(self.store.submit({'key':KEY})['id'])
        self.assertEqual(job['status'],'completed')
        self.assertFalse(job['result']['published'])
        self.assertEqual(self.store.catalog()['total_points'],1)

    def test_invalid_requests_and_concurrent_job(self):
        for request in [{'key':'bad'}, {'key':KEY,'days':31}, {'key':KEY,'days':True},
                        {'key':KEY,'sources':['UNKNOWN']},{'key':KEY,'start':'bad'}]:
            with self.assertRaises(ValueError):
                self.store.submit(request)
        block = threading.Event()
        self.addCleanup(block.set)
        self.store.client.download = lambda *args: (block.wait(timeout=3) and [],b'')
        self.store.submit({'key':KEY})
        with self.assertRaises(RuntimeError):
            self.store.submit({'key':KEY})
        block.set()

    def test_thirty_days_partitioned_without_gaps_and_repeat(self):
        calls = []
        def download(key, product, bbox, days, start=None):
            calls.append((start, days))
            self.assertTrue(1 <= days <= 5)
            self.assertIsNotNone(start)
            return [{**ROW, 'acq_date': start}], b'synthetic-block'
        self.store.client.download = download
        first = (datetime.now(timezone.utc).date()-timedelta(days=29)).isoformat()
        job = self.wait_job(self.store.submit({'key':KEY,'days':30})['id'])
        self.assertEqual(job['status'], 'completed', job)
        self.assertEqual(len(calls), 6)
        covered = [datetime.fromisoformat(start).date()+timedelta(days=i) for start,days in calls for i in range(days)]
        self.assertEqual(len(set(covered)), 30)
        self.assertEqual(covered, [datetime.fromisoformat(first).date()+timedelta(days=i) for i in range(30)])
        self.assertEqual(job['result']['start'], first)
        self.assertEqual(job['result']['end'], TODAY)
        self.assertEqual(job['result']['received'], 6)
        self.assertEqual(job['result']['added'], 6)
        self.assertEqual(len(job['result']['downloads']), 6)
        for block in job['result']['downloads']:
            self.assertTrue((self.base/'runtime/downloads'/job['id']/block['file']).is_file())
        repeated = self.wait_job(self.store.submit({'key':KEY,'days':30})['id'])
        self.assertEqual(repeated['status'], 'completed', repeated)
        self.assertEqual(repeated['result']['added'], 0)

    def test_partial_last_block_and_failure_preserve_catalog(self):
        calls = []
        def download(key, product, bbox, days, start=None):
            calls.append((start, days))
            if len(calls) == 3:
                raise ValueError('FIRMS no disponible')
            return [{**ROW, 'acq_date':start}], b'synthetic-block'
        self.store.client.download = download
        before = (self.site/'data/catalog.json').read_bytes()
        job = self.wait_job(self.store.submit({'key':KEY,'days':12})['id'])
        self.assertEqual(job['status'], 'failed')
        self.assertEqual([days for _, days in calls], [5,5,2])
        self.assertEqual((self.site/'data/catalog.json').read_bytes(), before)
        self.assertFalse((self.base/'runtime/active.json').exists())

    def test_configurable_window_limit(self):
        self.store.settings['max_days_per_sync'] = 10
        self.assertEqual(self.store.validate_sync({'key':KEY,'days':10})[1],10)
        with self.assertRaises(ValueError):
            self.store.validate_sync({'key':KEY,'days':11})

    def test_publication_failure_rolls_back(self):
        self.store.client.download=self.fake_download
        with patch.object(self.store,'write_parquet',side_effect=OSError('disk full')):
            job=self.wait_job(self.store.submit({'key':KEY})['id'])
        self.assertEqual(job['status'],'failed')
        self.assertEqual(self.store.catalog(),self.catalog)
        self.assertFalse(list((self.base/'runtime/snapshots').glob('.building-*')))

    def test_node_proxy_and_backend_http(self):
        self.store.client.download=self.fake_download
        token='internal-test-token'
        server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(self.store,token))
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
        env={**os.environ,'CEMEC_BACKEND_PORT':str(server.server_port),'CEMEC_INTERNAL_TOKEN':token}
        project=Path(__file__).resolve().parents[1]
        process=subprocess.Popen([str(Path(sys.executable).parent/'node'),str(project/'serve.js'),
             '--root',str(self.site),'--port',str(port)],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        def stop():
            process.terminate();process.wait(timeout=5)
        self.addCleanup(stop)
        def request(method,url,body=None,headers=None,target_port=port):
            conn=http.client.HTTPConnection('127.0.0.1',target_port,timeout=5)
            try:
                conn.request(method,url,body,headers or {})
                res=conn.getresponse();return res.status,res.read()
            finally:
                conn.close()
        for _ in range(100):
            try:
                status,body=request('GET','/api/status');break
            except OSError:time.sleep(.02)
        self.assertEqual(status,200)
        self.assertFalse(json.loads(body)['firms_configured'])
        self.assertEqual(request('GET','/api/status',target_port=server.server_port)[0],403)
        headers={'Content-Type':'application/json'}
        self.assertEqual(request('POST','/api/sync',json.dumps({'key':KEY}),{**headers,'Origin':'https://other.test'})[0],403)
        status,body=request('POST','/api/sync',json.dumps({'key':KEY}),headers)
        self.assertEqual(status,202,body)
        job=self.wait_job(json.loads(body)['id'])
        self.assertEqual(job['status'],'completed',job)
        status,body=request('GET','/data/catalog.json')
        self.assertEqual(status,200)
        catalog=json.loads(body)
        self.assertEqual(catalog['total_points'],2)
        self.assertEqual(request('GET',catalog['partitions'][0]['url'])[0],200)
        self.assertEqual(request('GET','/live-data/..%2fjobs/secret.json')[0],404)

if __name__ == '__main__':
    unittest.main()
