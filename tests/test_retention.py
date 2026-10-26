"""Retención: proteger referencias transitivas y generar inventario sin borrar."""
import json,os,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from retention import plan

class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.now=1800000000
        self.config={'firms':{'storage':'runtime/firms'},'olci':{'cache':'runtime/olci'},'retention':{
            'olci_unused_days':30,'temporary_hours':24,'snapshot_days':30,'keep_previous_snapshots':3,'job_log_days':90,'preserve_history':True}}
    def write(self,relative,doc,age=50):
        p=self.root/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(doc));os.utime(p,(self.now-age*86400,)*2);os.utime(p.parent,(self.now-age*86400,)*2);return p
    def test_transitive_reference_and_last_three(self):
        self.write('runtime/firms/active.json',{'catalog':{'version':'v-active','url':'/live-data/v-active/web.json'}})
        for name,age,related in [('active',1,'old'),('one',40,None),('two',41,None),('three',42,None),('old',70,None),('unused',80,None)]:
            self.write(f'runtime/firms/snapshots/v-{name}/catalog.json',{'url':f'/live-data/v-{related}/geometry.json'} if related else {},age)
        result=plan(self.root,self.config,self.now)
        self.assertEqual([p['path'] for p in result['candidates']],['runtime/firms/snapshots/v-unused'])
        self.assertTrue((self.root/'runtime/firms/snapshots/v-unused/catalog.json').exists())
    def test_missing_reference_stops_plan(self):
        self.write('runtime/firms/active.json',{'catalog':{'version':'v-missing'},'url':'/live-data/v-missing/a.json'})
        with self.assertRaises(ValueError):plan(self.root,self.config,self.now)
    def test_old_cache_recent_usage_and_active_job(self):
        for key in ('a'*64,'b'*64):
            self.write(f'runtime/olci/{key}/metadata.json',{},50);self.write(f'runtime/olci/{key}/image.png',{},50)
        self.write('runtime/olci/'+('b'*64)+'/.last_used',{},1)
        self.write('runtime/firms/jobs/active.json',{'status':'running','created_at':'2020-01-01T00:00:00Z'},200)
        result=plan(self.root,self.config,self.now)
        self.assertEqual([p['path'] for p in result['candidates']],['runtime/olci/'+'a'*64])
        self.assertTrue(any('Tarea pendiente' in p['reason'] for p in result['protected']))
        self.assertTrue(result['notes'])
    def test_sentinel2_cache_uses_its_retention_and_access_marker(self):
        self.config['sentinel2']={'cache':'runtime/sentinel2'}
        self.config['retention']['sentinel2_unused_days']=30
        for key in ('c'*64,'d'*64):
            self.write(f'runtime/sentinel2/{key}/metadata.json',{},50);self.write(f'runtime/sentinel2/{key}/image.png',{},50)
        self.write('runtime/sentinel2/'+('d'*64)+'/.last_used',{},1)
        result=plan(self.root,self.config,self.now)
        self.assertEqual([p['path'] for p in result['candidates']],['runtime/sentinel2/'+'c'*64])
