"""Mosaicos oficiales: escala DN, catálogo compartido, deduplicación y presupuesto."""
import json
import time
import unittest
from unittest.mock import patch
import test_olci
from test_olci import png
from olci_service import PROCESS
from mosaic_service import QuarterlyMosaicService,COLLECTION

class MosaicTests(unittest.TestCase):
    def setUp(self):
        test_olci.OlciTests.setUp(self)
        store=self.service.store;store.config['sentinel2']={'enabled':True,'max_image_side':128,'shared_unit_id':self.unit['id'],'catalog_cache_hours':24,'max_new_mosaics_per_day':1}
        store.config['firms']={'bbox':self.unit['bbox']}
        self.municipality={**self.unit,'id':'municipality','name':'Municipio'}
        store.catalog=lambda:{'units':[self.unit,self.municipality],'boundary_version':'qa'}
        self.service=QuarterlyMosaicService(store);self.addCleanup(self.service.executor.shutdown)
        self.product={'id':'2026-Q2','time_utc':'2026-04-01T00:00:00Z','year':2026,'quarter':2,'satellite':'Sentinel-2 · L3',
            'mosaic_period_utc':['2026-04-01T00:00:00Z','2026-06-30T23:59:59Z'],'tile_ids':['tile-a'],'revision':'qa'}
    def test_catalog_quarters_and_persistent_cache(self):
        features=[{'id':name,'geometry':self.geometry,'properties':{'datetime':date}} for name,date in
                  [('tile-a','2026-04-01T00:00:00Z'),('tile-b','2026-04-01T00:00:00Z'),('tile-old','2026-01-01T00:00:00Z')]]
        params={'unit':self.unit,'mode':'latest','start':'2026-10-01T00:00:00Z','end':'2026-10-19T00:00:00Z'}
        def catalog(url,payload,accept):
            self.assertEqual(payload['collections'],[COLLECTION]);return json.dumps({'features':features}).encode(),{}
        with patch.object(self.service,'post',side_effect=catalog) as post:
            first=self.service.search(params);second=self.service.search({**params,'unit':self.municipality})
            self.assertEqual(post.call_count,1);self.assertTrue(second['catalog_cached'])
            self.assertEqual([p['id'] for p in first['products']],['2026-Q2','2026-Q1'])
            self.assertEqual(first['products'][0]['tile_ids'],['tile-a','tile-b'])
    def test_shared_render_across_units_and_dn_scaling(self):
        self.municipality['bbox']=[0,-.000000375,.02,.02] # Redondeo submétrico, como San Luis.
        def process(url,payload,accept):
            self.assertEqual(payload['input']['data'][0]['type'],COLLECTION)
            self.assertIn('*0.0001',payload['evalscript'])
            self.assertEqual(payload['input']['data'][0]['dataFilter']['timeRange']['from'],'2026-04-01T00:00:00Z')
            return png(payload['output']['width'],payload['output']['height']),{}
        with patch.object(self.service,'post',side_effect=process) as post:
            first=self.service.render({'unit':self.unit,'product':self.product})
            second=self.service.render({'unit':self.municipality,'product':self.product})
            self.assertEqual(post.call_count,1);self.assertEqual(first['url'],second['url']);self.assertTrue(second['cached'])
            self.assertEqual(second['requested_unit_id'],'municipality');self.assertAlmostEqual(second['territory_fraction_with_data'],.5)
            self.assertEqual(second['mosaic_period_utc'][1],'2026-06-30T23:59:59Z')
    def test_daily_budget_persists_and_cache_is_available_after_limit(self):
        payload={'output':{'width':8,'height':8}}
        def provider_response(url,payload,accept):
            return png(payload['output']['width'],payload['output']['height']),{'x-processingunits-spent':'0.25'}
        with patch('olci_service.OlciService.post',side_effect=provider_response) as provider:
            params={'unit':self.unit,'product':self.product}
            first=self.service.render(params);second=self.service.render(params)
            self.assertEqual(first['url'],second['url']);self.assertTrue(second['cached'])
            with self.assertRaises(RuntimeError):self.service.post(PROCESS,payload,'image/png')
            self.assertEqual(provider.call_count,1)
        usage=json.loads((self.service.root/'usage.json').read_text());record=next(iter(usage['days'].values()))
        self.assertEqual(record['attempts'],1);self.assertEqual(record['processing_units'],.25)
    def test_empty_catalog_cached_and_invalid_quarter(self):
        params={'unit':self.unit,'mode':'period','start':'2025-01-01T00:00:00Z','end':'2025-03-31T23:59:59Z'}
        with patch.object(self.service,'post',return_value=(b'{"features":[]}',{})) as post:
            self.assertEqual(self.service.search(params)['products'],[])
            self.assertEqual(self.service.search(params)['products'],[]);self.assertEqual(post.call_count,1)
        for request in ({'year':2026,'quarter':5},{'year':2010,'quarter':1},{'year':3000,'quarter':1}):
            with self.assertRaises(ValueError):self.service.submit('search',{'unit_id':self.unit['id'],'mode':'period',**request})
    def finished(self,job):
        for _ in range(500):
            result=self.service.job(job['id'])
            if result['status'] not in ('pending','running'):break
            time.sleep(.01)
        self.assertEqual(result['status'],'completed',result.get('error'))
        return result['result']
    def test_detail_keeps_quarter_and_reuses_aligned_crop_between_units(self):
        def response(url,payload,accept):return png(payload['output']['width'],payload['output']['height']),{}
        with patch.object(self.service,'post',side_effect=response) as post:
            parent=self.service.render({'unit':self.unit,'product':self.product})
            request={'unit_id':self.unit['id'],'image_id':parent['id'],'bbox':[.004,.004,.012,.012]}
            detail=self.finished(self.service.submit('detail',request))
            self.assertEqual(detail['kind'],'quarterly_mosaic_detail')
            self.assertEqual(detail['mosaic_period_utc'],parent['mosaic_period_utc'])
            self.assertEqual(detail['regional_image_id'],parent['id'])
            self.assertEqual(detail['coverage_scope'],'visible_crop');self.assertIsNone(detail['territory_fraction_with_data'])
            self.assertLess(detail['output_pixel_size_m_at_center'],parent['output_pixel_size_m_at_center'])
            self.assertLessEqual(max(detail['dimensions']),1024)
            reused=self.finished(self.service.submit('detail',{**request,'unit_id':'municipality','bbox':[.0041,.0041,.0119,.0119]}))
            self.assertTrue(reused['cached']);self.assertEqual(reused['url'],detail['url'])
            self.assertEqual(post.call_count,2,'Solo una consulta regional y una de detalle')
            self.service.image_file(detail['id']+'.png')
            self.assertTrue((self.service.root/parent['id']/'.last_used').exists())
    def test_detail_validates_area_coordinates_source_and_switch(self):
        with patch.object(self.service,'post',side_effect=lambda url,payload,accept:(png(payload['output']['width'],payload['output']['height']),{})):
            parent=self.service.render({'unit':self.unit,'product':self.product})
        request={'unit_id':self.unit['id'],'image_id':parent['id'],'bbox':[.004,.004,.012,.012]}
        for bbox in ([float('nan'),0,1,1],[1,1,2,2],[0,0,0,1],None,[True,0,1,1]):
            with self.subTest(bbox=bbox),self.assertRaises(ValueError):self.service.submit('detail',{**request,'bbox':bbox})
        with self.assertRaises(ValueError):self.service.submit('detail',{**request,'image_id':'../.env'})
        self.service.settings['detail_max_area_km2']=.1
        with self.assertRaises(ValueError):self.service.submit('detail',{**request,'bbox':self.unit['bbox']})
        self.service.settings['detail_enabled']=False
        with self.assertRaises(ValueError):self.service.submit('detail',request)
