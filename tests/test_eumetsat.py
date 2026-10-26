"""Descargas paginadas, calidad propia de SLSTR, caché y publicación atómica."""
from copy import deepcopy
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from eumetsat_client import EumetsatClient, read_csv, normalize_detection
import test_firms as fixtures
TODAY = fixtures.TODAY


HEADER = 'lat(deg),lon(deg),day,time,D/N,FRP(MW),confidence(%),confidence_class(lower=0;nominal=1;higher=2),satellite\n'


def csv_data(clock='08:15:12', lat='1', sat='S3A'):
    return ('#processing_baseline = FRP_NRT.003.02.00\n#number_of_detected_fires = 1\n' + HEADER +
            f'{lat},1,{TODAY},{clock},D,4.5,99.9,0,{sat}\n').encode()


class Product:
    entries = ['folder/FRP_MWIR1km_alternative.csv', 'folder/FRP_MWIR1km_standard.csv', 'folder/FRP_SWIR500m.csv']
    sensing_start = datetime.now(timezone.utc)
    sensing_end = sensing_start

    def __init__(self, index=0, payload=None, failure=None):
        self.index, self.payload, self.failure, self.opens = index, payload, failure, 0

    def __str__(self):
        return f'S3A_SL_2_FRP____test_{self.index}.SEN3'

    def open(self, entry):
        assert entry == 'folder/FRP_MWIR1km_standard.csv'
        self.opens += 1
        if self.failure:
            raise self.failure
        return io.BytesIO(self.payload or csv_data(clock=f'08:15:{self.index:02d}'))


class EumetsatTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.StoreTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.store = self.fixture.store
        settings = {'enabled': True, 'collection': 'EO:EUM:DAT:0417', 'bbox': [0,0,2,2],
            'days': 3, 'max_days_per_sync': 31, 'variant': 'MWIR1km_standard', 'product_limit': None,
            'consumer_key_env': 'CEMEC_EUM_TEST_KEY', 'consumer_secret_env': 'CEMEC_EUM_TEST_SECRET', 'retries': 0}
        self.store.eumetsat_settings = settings
        self.store.eumetsat_client = EumetsatClient(settings, self.fixture.base / 'cache')
        self.environment = patch.dict(os.environ, CEMEC_EUM_TEST_KEY='fixture-key', CEMEC_EUM_TEST_SECRET='fixture-secret')
        self.environment.start()
        self.addCleanup(self.environment.stop)
        class FixedClock(datetime):
            @classmethod
            def now(cls, tz=None):
                value=datetime.fromisoformat(TODAY+'T18:00:00+00:00')
                return value if tz is not None else value.replace(tzinfo=None)
        clock=patch('firms_backend.datetime',FixedClock)
        clock.start()
        self.addCleanup(clock.stop)

    def sync(self, products, count=None):
        # Generator representa todas las páginas del catálogo; no se limita a 12.
        self.store.eumetsat_client.search = lambda *args: (iter(products), len(products) if count is None else count)
        job = self.store.submit_eumetsat({'start': TODAY, 'days': 1})
        return self.fixture.wait_job(job['id'])

    def test_real_format_seconds_and_class_not_percent(self):
        rows, meta = read_csv(csv_data())
        point = normalize_detection(rows[0], str(Product()), 'standard.csv', meta)
        self.assertEqual(point['confidence'], 'l')  # Clase 0, aunque porcentaje sea 99.9.
        self.assertEqual(point['confidence_class'], '0')
        self.assertEqual(point['frp'], 4.5)
        self.assertEqual(point['time'], '0815')
        self.assertIn('08:15:12', point['observation_utc'])
        self.assertEqual(point['satellite'], 'Sentinel-3A')
        self.assertEqual(point['product_version'], 'FRP_NRT.003.02.00')
        self.assertIn('confidence(%)', json.loads(point['raw_fields']))

    def test_all_17_products_inab_preserved_cache_and_parquet(self):
        products = [Product(i) for i in range(17)]
        job = self.sync(products)
        self.assertEqual(job['status'], 'completed', job)
        result = job['result']
        self.assertEqual(result['products_processed'], 17)
        self.assertEqual(result['added'], 17)
        self.assertTrue(result['complete'])
        catalog = self.store.catalog()
        rows = []
        for partition in catalog['partitions']:
            rows.extend(json.loads(self.store.resolve_url(partition['url']).read_text()))
        original = next(row for row in rows if row['id'] == self.fixture.original['id'])
        self.assertEqual(original['source'], 'INAB · puntos de calor')
        table = pq.read_table(self.store.resolve_url(catalog['partitions'][0]['parquet_url'])).to_pylist()
        self.assertIn('observation_utc', table[0])
        self.assertEqual(len([row for row in table if row['product_id']]), 17)
        again = self.sync(products)
        self.assertEqual(again['result']['added'], 0)
        self.assertEqual(again['result']['duplicates'], 17)
        self.assertFalse(again['result']['published'])
        self.assertTrue(all(p.opens == 1 for p in products))
        self.assertTrue(all(d['cached'] for d in again['result']['downloads']))

    def test_license_failure_no_partial_publish_and_no_secrets(self):
        from eumdac.product import ProductError
        error = ProductError('secret URL fixture-secret', {'status':403, 'exceptions':[{'exceptionText':'Copernicus license required to access this collection'}]})
        job = self.sync([Product(), Product(1, failure=error)])
        self.assertEqual(job['status'], 'failed')
        self.assertEqual(job['error_code'], 'copernicus_license_required')
        self.assertNotIn('fixture-secret', json.dumps(job))
        self.assertEqual(self.store.catalog()['version'], 'original')
        self.assertFalse((self.store.runtime / 'active.json').exists())
        self.assertEqual(job['products_processed'], 1)

    def test_outside_bbox_and_empty_query_keep_history(self):
        job = self.sync([Product(payload=csv_data(lat='3'))])
        self.assertEqual(job['status'], 'completed', job)
        self.assertEqual(job['result']['outside_bbox'], 1)
        self.assertEqual(job['result']['added'], 0)
        empty = self.sync([])
        self.assertEqual(empty['result']['products_found'], 0)
        self.assertEqual(self.store.catalog()['total_points'], 1)
        self.assertIn('no demuestra', empty['result']['notice'])

    def test_incomplete_query_and_csv_stop_publication(self):
        job = self.sync([Product()], count=2)
        self.assertEqual(job['status'], 'failed')
        self.assertEqual(self.store.catalog()['version'], 'original')
        for index, payload in enumerate([b'<html>failure</html>', HEADER.encode(), csv_data().replace(b'fires = 1', b'fires = 2'),
                        csv_data().replace(b',S3A\n', b'\n')]):
            if payload == HEADER.encode():
                continue  # Un CSV con encabezado válido y cero filas sí es válido.
            with self.subTest(payload=payload):
                job = self.sync([Product(index+10, payload=payload)])
                self.assertEqual(job['status'], 'failed')
                self.assertEqual(self.store.catalog()['version'], 'original')

    def test_validation_separate_sync_state_and_cache_integrity(self):
        for request in [{'days':0}, {'days':32}, {'days':True}, {'start':'tomorrow'}, {'start':'2099-01-01'}]:
            with self.assertRaises(ValueError):
                self.store.submit_eumetsat(request)
        original_sync = {'provider': 'firms', 'at': 'prior'}
        self.store.record_active(deepcopy(self.store.catalog()), original_sync, 'sync')
        product = Product()
        self.sync([product])
        self.assertEqual(self.store.status()['last_sync'], original_sync)
        self.assertEqual(self.store.status()['last_eumetsat_sync']['products_processed'], 1)
        cached_file = next(self.store.eumetsat_client.cache.glob('products/*/original.csv'))
        cached_file.write_text('corrupt')
        self.sync([product])
        self.assertEqual(product.opens, 2)


if __name__ == '__main__':
    unittest.main()
