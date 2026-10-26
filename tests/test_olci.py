"""OLCI sin Internet: filtros PNG, catálogo, períodos, caché y errores privados."""
import io,json,os,struct,sys,tempfile,time,unittest,zlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from olci_service import OlciService,png_alpha,CATALOG,PROCESS

def png(width,height,method=0):
    def chunk(kind,data): return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
    previous=bytearray(width*4);rows=[]
    for y in range(height):
        row=bytearray(v for x in range(width) for v in (x%256,y%256,123,255 if x<width//2 else 0));encoded=bytearray(len(row))
        for x,value in enumerate(row):
            a=row[x-4] if x>=4 else 0;b=previous[x];c=previous[x-4] if x>=4 else 0
            p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c)
            predictor=[0,a,b,(a+b)//2,a if pa<=pb and pa<=pc else b if pb<=pc else c][method]
            encoded[x]=(value-predictor)&255
        rows.append(bytes([method])+encoded);previous=row
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b'')

class OlciTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        base=Path(self.temp.name)
        self.unit={'id':'region-test','name':'Prueba','bbox':[0,0,.02,.02],'geometry_url':'/unit.geojson'}
        self.geometry={'type':'Polygon','coordinates':[[[0,0],[.02,0],[.02,.02],[0,.02],[0,0]]]}
        (base/'unit.geojson').write_text(json.dumps({'type':'Feature','geometry':self.geometry}))
        store=SimpleNamespace(base=base,config={'olci':{'enabled':True}},catalog=lambda:{'units':[self.unit]},resolve_url=lambda _:base/'unit.geojson')
        self.service=OlciService(store);self.addCleanup(self.service.executor.shutdown)
        self.env=patch.dict(os.environ,{'CDSE_CLIENT_ID':'QA-ID','CDSE_CLIENT_SECRET':'QA-SECRET'});self.env.start();self.addCleanup(self.env.stop)
    def product(self,name,time='2026-10-10T16:00:00Z'):
        return {'id':name,'geometry':self.geometry,'properties':{'datetime':time}}
    def test_all_png_filters_and_partial_coverage(self):
        for method in range(5):
            with self.subTest(method=method):
                alpha=png_alpha(png(8,4,method));self.assertEqual(alpha.shape,(4,8));self.assertEqual(float((alpha>0).mean()),.5)
        with self.assertRaises(ValueError):png_alpha(b'not PNG')
    def test_catalog_pagination_sorting_and_empty(self):
        responses=[{'features':[self.product('S3A-old')],'context':{'next':123}},
            {'features':[self.product('S3B-new','2026-10-11T16:00:00Z'),self.product('S3A-old')]}]
        params={'unit':self.unit,'mode':'period','start':'2026-10-09T00:00:00Z','end':'2026-10-12T23:59:59Z'}
        with patch.object(self.service,'post',side_effect=lambda *a:(json.dumps(responses.pop(0)).encode(),{})) as post:
            result=self.service.search(params)
            self.assertEqual([p['id'] for p in result['products']],['S3B-new','S3A-old'])
            self.assertEqual(post.call_args.args[1]['next'],123)
        with patch.object(self.service,'post',return_value=(b'{"features":[]}',{})):
            self.assertEqual(self.service.search(params)['products'],[])
    def test_projected_render_cache_and_private_paths(self):
        params={'unit':self.unit,'product':{'id':'S3B-QA','time_utc':'2026-10-10T16:00:00Z','satellite':'Sentinel-3B'}}
        def process(url,payload,accept):
            self.assertEqual(url,PROCESS);self.assertIn('3857',payload['input']['bounds']['properties']['crs'])
            return png(payload['output']['width'],payload['output']['height'],4),{}
        with patch.object(self.service,'post',side_effect=process) as post:
            first=self.service.render(params);second=self.service.render(params)
            self.assertEqual(post.call_count,1);self.assertTrue(second['cached']);self.assertFalse(first['cached'])
            self.assertAlmostEqual(first['territory_fraction_with_data'],.5)
            self.assertTrue(self.service.image_file(first['id']+'.png').is_file())
        for name in ('../.env','a.png','a'*64+'.txt'):
            with self.assertRaises(ValueError):self.service.image_file(name)
    def test_invalid_period_unit_and_reference(self):
        for request in ({'unit_id':'missing'},{'unit_id':'region-test','mode':'period','start':'2026-10-11','end':'2026-10-10'},
                        {'unit_id':'region-test','mode':'period','start':'2024-01-01','end':'2026-10-10'}):
            with self.assertRaises(ValueError):self.service.submit('search',request)
        with self.assertRaises(ValueError):self.service.submit('render',{'unit_id':'region-test','search_id':'unknown'})
    def test_401_refresh_and_429_sanitized(self):
        unauthorized=HTTPError(PROCESS,401,'private QA-SECRET',{},io.BytesIO())
        with patch.object(self.service,'_token',return_value='TOKEN'),patch.object(self.service,'_http',side_effect=[unauthorized,(b'ok',{})]) as call:
            self.assertEqual(self.service.post(PROCESS,{},'image/png')[0],b'ok');self.assertEqual(call.call_count,2)
        rate=HTTPError(PROCESS,429,'private QA-SECRET',{},io.BytesIO())
        with patch.object(self.service,'_token',return_value='TOKEN'),patch.object(self.service,'_http',side_effect=rate):
            with self.assertRaises(RuntimeError) as error:self.service.post(PROCESS,{},'image/png')
            self.assertNotIn('QA-SECRET',str(error.exception));self.assertIn('429',str(error.exception))

    def finished(self,job,expected='completed'):
        for _ in range(500):
            result=self.service.job(job['id'])
            if result['status'] not in ('pending','running'):break
            time.sleep(.01)
        self.assertEqual(result['status'],expected,result)
        return result.get('result',result)
    def test_detail_same_time_native_scale_cache_and_budget(self):
        self.service.settings['max_new_details_per_day']=1
        params={'unit':self.unit,'product':{'id':'S3A-QA','time_utc':'2026-10-10T16:00:00Z','satellite':'Sentinel-3A'}}
        payloads=[]
        def response(url,payload,accept):
            payloads.append(payload)
            return png(payload['output']['width'],payload['output']['height']),{'X-ProcessingUnits-Spent':'0.1'}
        with patch.object(self.service,'post',side_effect=response) as provider:
            parent=self.service.render(params)
            # Las primeras imágenes OLCI guardadas no incluían collection.
            legacy={**parent,'reference':'S3A_OL_1_EFR_LEGACY_QA'};legacy.pop('collection')
            (self.service.root/parent['id']/'metadata.json').write_text(json.dumps(legacy))
            parent=legacy
            request={'unit_id':self.unit['id'],'image_id':parent['id'],'bbox':[.004,.004,.012,.012]}
            detail=self.finished(self.service.submit('detail',request))
            self.assertEqual(detail['kind'],'olci_detail')
            self.assertEqual(detail['reference'],parent['reference'])
            self.assertEqual(detail['processing_interval_utc'],parent['processing_interval_utc'])
            self.assertEqual(payloads[0]['input']['data'][0]['dataFilter']['timeRange'],payloads[1]['input']['data'][0]['dataFilter']['timeRange'])
            self.assertEqual(detail['nominal_resolution_m'],300)
            self.assertGreater(detail['output_pixel_size_m_at_center'],240)
            self.assertEqual(detail['coverage_scope'],'visible_crop');self.assertIsNone(detail['territory_fraction_with_data'])
            reused=self.finished(self.service.submit('detail',request));self.assertTrue(reused['cached'])
            self.assertEqual(detail['url'],reused['url']);self.assertEqual(provider.call_count,2)
            self.finished(self.service.submit('detail',{**request,'bbox':[.012,.012,.019,.019]}),expected='failed')
            self.assertEqual(provider.call_count,2)
            usage=json.loads((self.service.root/'detail-usage.json').read_text())
            self.assertEqual(next(iter(usage['days'].values()))['processing_units'],.1)
            marker=self.service.root/parent['id']/'.last_used';before=marker.stat().st_mtime_ns
            self.service.image_file(detail['id']+'.json');self.assertGreaterEqual(marker.stat().st_mtime_ns,before)
    def test_detail_rejects_invalid_bbox_and_disabled_service(self):
        params={'unit':self.unit,'product':{'id':'S3A-QA','time_utc':'2026-10-10T16:00:00Z','satellite':'Sentinel-3A'}}
        with patch.object(self.service,'post',side_effect=lambda u,p,a:(png(p['output']['width'],p['output']['height']),{})):
            parent=self.service.render(params)
        for bbox in (None,[0,0,1,float('nan')],[1,1,2,2],[True,0,.01,.01]):
            with self.assertRaises(ValueError):self.service.submit('detail',{'unit_id':self.unit['id'],'image_id':parent['id'],'bbox':bbox})
        self.service.settings['detail_enabled']=False
        with self.assertRaises(ValueError):self.service.submit('detail',{'unit_id':self.unit['id'],'image_id':parent['id'],'bbox':[0,0,.01,.01]})
