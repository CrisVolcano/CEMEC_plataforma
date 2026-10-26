"""Sentinel-2: selección de colección, nubes, resolución, caché y referencia temporal."""
import json
import unittest
from unittest.mock import patch
import test_olci
from test_olci import png
from olci_service import Sentinel2Service,PROCESS

class Sentinel2Tests(unittest.TestCase):
    def setUp(self):
        test_olci.OlciTests.setUp(self)
        store=self.service.store
        store.config['sentinel2']={'enabled':True,'max_image_side':128}
        self.service=Sentinel2Service(store)
        self.addCleanup(self.service.executor.shutdown)
    def test_s2c_catalog_and_cloud_metadata(self):
        features=[{'id':'S2C_MSIL2A_QA','geometry':self.geometry,'properties':{'datetime':'2026-10-18T16:00:00Z','eo:cloud_cover':37.2}}]
        def catalog(url,payload,accept):
            self.assertEqual(payload['collections'],['sentinel-2-l2a'])
            return json.dumps({'features':features}).encode(),{}
        with patch.object(self.service,'post',side_effect=catalog):
            result=self.service.search({'unit':self.unit,'mode':'period','start':'2026-10-17T00:00:00Z','end':'2026-10-19T23:59:59Z'})
        self.assertEqual(result['products'][0]['satellite'],'Sentinel-2C')
        self.assertEqual(result['products'][0]['cloud_cover_catalog'],37.2)
    def test_rgb_preview_scale_cache_and_independent_storage(self):
        params={'unit':self.unit,'product':{'id':'S2B_MSIL2A_QA','time_utc':'2026-10-18T16:00:00Z','satellite':'Sentinel-2B','cloud_cover_catalog':12.3}}
        def process(url,payload,accept):
            self.assertEqual(url,PROCESS)
            self.assertEqual(payload['input']['data'][0]['type'],'sentinel-2-l2a')
            self.assertIn('B04',payload['evalscript']);self.assertIn('B03',payload['evalscript']);self.assertIn('B02',payload['evalscript'])
            self.assertNotIn('B08',payload['evalscript'])
            return png(payload['output']['width'],payload['output']['height']),{}
        with patch.object(self.service,'post',side_effect=process) as post:
            first=self.service.render(params);second=self.service.render(params)
            self.assertEqual(post.call_count,1);self.assertTrue(second['cached'])
            self.assertEqual(first['nominal_resolution_m'],10)
            self.assertLessEqual(max(first['dimensions']),128)
            self.assertGreater(first['output_pixel_size_m_at_center'],10)
            self.assertTrue(first['url'].startswith('/api/sentinel2/'))
            self.assertEqual(first['cloud_cover_catalog'],12.3)
            self.assertIn('sentinel2',str(self.service.root))
            self.service.settings['max_image_side']=256
            resized=self.service.render(params)
            self.assertNotEqual(first['id'],resized['id']);self.assertEqual(post.call_count,2)
