"""Mosaicos trimestrales oficiales: caché regional compartida y presupuesto acotado."""
import fcntl
import hashlib
import json
import math
import re
from pathlib import Path
import secrets
import time
from datetime import datetime,timedelta,timezone
import numpy as np
from shapely import contains_xy
from shapely.geometry import shape
from olci_service import Sentinel2Service,CATALOG,PROCESS,iso,parse,project

COLLECTION='byoc-5460de54-082e-473a-b6ea-d5cbe3c17cca'
def quarter_dates(year,quarter):
    if type(year) is not int or type(quarter) is not int or not 2015<=year<=datetime.now(timezone.utc).year or not 1<=quarter<=4:
        raise ValueError('Elige un año y un trimestre válidos, desde 2015')
    start=datetime(year,1+3*(quarter-1),1,tzinfo=timezone.utc)
    stop=datetime(year+int(quarter==4),1 if quarter==4 else 1+3*quarter,1,tzinfo=timezone.utc)
    return start,stop

class QuarterlyMosaicService(Sentinel2Service):
    collection=COLLECTION
    max_side=1024
    value_scale=.0001 # Mosaicos BYOC expresados en DN: reflectancia = DN / 10000.
    def region(self):
        unit=self.unit(self.settings.get('shared_unit_id','region-peten'))
        bbox=self.settings.get('shared_bbox') or self.store.config.get('firms',{}).get('bbox') or unit['bbox']
        return {**unit,'bbox':bbox}
    def submit(self,action,request):
        if action=='detail':
            if not self.configured():raise ValueError('Falta configurar CDSE en el servidor')
            if not isinstance(request,dict):raise ValueError('Solicitud inválida')
            unit=self.unit(request.get('unit_id'))
            if self.settings.get('detail_enabled',True) is not True:raise ValueError('El detalle está deshabilitado en el servidor')
            image_id=request.get('image_id')
            if not isinstance(image_id,str) or not re.fullmatch(r'[0-9a-f]{64}',image_id):raise ValueError('Carga primero un mosaico regional válido')
            parent=json.loads(self.image_file(image_id+'.json').read_text())
            if parent.get('kind')=='quarterly_mosaic_detail':
                image_id=parent['regional_image_id'];parent=json.loads(self.image_file(image_id+'.json').read_text())
            if parent.get('kind')!='quarterly_mosaic' or parent.get('collection')!=self.collection:raise ValueError('El detalle requiere un mosaico trimestral regional')
            view=self.detail_view(request.get('bbox'),parent['bbox_crs84'])
            product={'id':f"{parent['year']}-Q{parent['quarter']}",'time_utc':parent['reference_time_utc'],
                'year':parent['year'],'quarter':parent['quarter'],'satellite':parent['satellite'],
                'mosaic_period_utc':parent['mosaic_period_utc'],'tile_ids':parent['tile_ids'],
                'revision':hashlib.sha256(json.dumps([parent['tile_ids'],self.store.catalog().get('boundary_version')]).encode()).hexdigest()}
            return self.enqueue('detail',{'unit':unit,'product':product,'detail':{'regional_image_id':image_id,**view}})
        if action=='search' and isinstance(request,dict) and request.get('mode')=='period':
            start,stop=quarter_dates(request.get('year'),request.get('quarter'))
            if stop>datetime.now(timezone.utc): raise ValueError('El trimestre todavía no ha terminado. Elige uno completo.')
            request={**request,'start':start.date().isoformat(),'end':(stop-timedelta(days=1)).date().isoformat()}
        return super().submit(action,request)
    def search(self,p):
        region=self.region();now=datetime.now(timezone.utc)
        current_start,_=quarter_dates(now.year,(now.month-1)//3+1)
        end=current_start-timedelta(seconds=1)
        if p['mode']=='period': start=parse(p['start']);end=parse(p['end'])
        else: start=datetime(max(2015,end.year-2),1,1,tzinfo=timezone.utc)
        identity={'collection':self.collection,'bbox':region['bbox'],'start':iso(start),'end':iso(end)}
        key=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
        folder=self.root/'catalog';folder.mkdir(exist_ok=True)
        cached=folder/(key+'.json');ttl=int(self.settings.get('catalog_cache_hours',24))*3600
        if cached.is_file() and time.time()-cached.stat().st_mtime<ttl:
            data=json.loads(cached.read_text());products=data['products'];catalog_cached=True
        else:
            query={'collections':[self.collection],'bbox':region['bbox'],'datetime':iso(start)+'/'+iso(end),'limit':100}
            grouped={};geometry=shape(json.loads(self.store.resolve_url(region['geometry_url']).read_text())['geometry'])
            for _ in range(100):
                raw,_=self.post(CATALOG,query,'application/geo+json');response=json.loads(raw)
                for feature in response.get('features',[]):
                    if not feature.get('geometry') or not shape(feature['geometry']).intersects(geometry):continue
                    stamp=parse(feature['properties'].get('datetime') or feature['properties']['start_datetime'])
                    year,quarter=stamp.year,(stamp.month-1)//3+1;first,stop=quarter_dates(year,quarter)
                    if stop>now:continue
                    label=f'{year}-Q{quarter}'
                    product=grouped.setdefault(label,{'id':label,'time_utc':iso(first),'satellite':'Sentinel-2 · L3',
                        'year':year,'quarter':quarter,'mosaic_period_utc':[iso(first),iso(stop-timedelta(seconds=1))],
                        'cloud_cover_catalog':None,'tile_ids':[]})
                    product['tile_ids'].append(feature['id'])
                nxt=response.get('context',{}).get('next')
                if nxt is None:break
                query['next']=nxt
            else:raise RuntimeError('Catálogo de mosaicos incompleto. Reduce el período.')
            products=sorted(grouped.values(),key=lambda v:v['time_utc'],reverse=True)
            for product in products:
                product['tile_ids']=sorted(set(product['tile_ids']))
                product['revision']=hashlib.sha256(json.dumps([product['tile_ids'],self.store.catalog().get('boundary_version')]).encode()).hexdigest()
            temp=cached.with_suffix('.tmp');temp.write_text(json.dumps({'products':products}));temp.replace(cached);catalog_cached=False
        search_id=secrets.token_hex(16)
        result={'search_id':search_id,'unit':p['unit'],'products':products,'mode':p['mode'],
            'catalog_complete':True,'catalog_cached':catalog_cached,'search_interval_utc':[iso(start),iso(end)]}
        with self.lock:
            self.searches[search_id]=result
            for key in list(self.searches)[:-30]:self.searches.pop(key,None)
        return result
    def time_window(self,product):
        # La fecha del catálogo identifica el inicio del trimestre, no una pasada.
        start=parse(product['time_utc']);return start,start+timedelta(days=1)
    def post(self,url,payload,accept):
        if url!=PROCESS:return super().post(url,payload,accept)
        limit=int(self.settings.get('max_new_mosaics_per_day',6))
        if limit<1:raise RuntimeError('La preparación de mosaicos nuevos está deshabilitada; usa los guardados.')
        ledger=self.root/'usage.json';day=datetime.now(timezone.utc).date().isoformat()
        with (self.root/'.budget.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            usage=json.loads(ledger.read_text()) if ledger.is_file() else {'days':{}}
            record=usage['days'].setdefault(day,{'attempts':0,'completed':0,'processing_units':0})
            if record['attempts']>=limit:raise RuntimeError('Se alcanzó el límite diario de mosaicos nuevos. Los guardados siguen disponibles; vuelve a intentar mañana UTC.')
            record['attempts']+=1;self._write_usage(ledger,usage)
            raw,headers=super().post(url,payload,accept)
            units=next((v for k,v in headers.items() if k.lower()=='x-processingunits-spent'),0)
            record['completed']+=1;record['processing_units']+=float(units or 0)
            self._write_usage(ledger,usage)
            return raw,headers
    def _write_usage(self,path,usage):
        usage['days']=dict(sorted(usage['days'].items())[-90:])
        temp=path.with_suffix('.tmp');temp.write_text(json.dumps(usage));temp.replace(path)
    def decorate_result(self,result,alpha,p):
        product=p['product'];bbox=result['bbox_crs84'];west,south,east,north=result['output_bbox'];width,height=result['dimensions']
        if p.get('detail'):
            return {**result,'kind':'quarterly_mosaic_detail','year':product['year'],'quarter':product['quarter'],
                'mosaic_period_utc':product['mosaic_period_utc'],'tile_ids':product['tile_ids'],
                'regional_image_id':p['detail']['regional_image_id'],'cache_scope':'viewport_detail_shared',
                'territory_fraction_with_data':None,'coverage_scope':'visible_crop','source_value_scale':self.value_scale,
                'area_km2':p['detail']['area_km2'],'detail_grid_m':p['detail']['grid_m'],
                'note':'Detalle del mismo mosaico trimestral. Cobertura referida al recorte, no a todo el territorio. Sin descargas automáticas al mover el mapa.'}
        lon=np.degrees((west+(np.arange(width)+.5)*(east-west)/width)/6378137)
        lat=np.degrees(2*np.arctan(np.exp((north-(np.arange(height)+.5)*(north-south)/height)/6378137))-np.pi/2)
        coverages={}
        for unit in self.store.catalog()['units']:
            b=unit['bbox']
            # Tolerancia de redondeo submétrica del bbox configurado, no un recorte arbitrario.
            if b[0]<bbox[0]-1e-6 or b[1]<bbox[1]-1e-6 or b[2]>bbox[2]+1e-6 or b[3]>bbox[3]+1e-6:
                coverages[unit['id']]=None;continue
            xs=np.flatnonzero((lon>=b[0])&(lon<=b[2]));ys=np.flatnonzero((lat>=b[1])&(lat<=b[3]))
            if not len(xs) or not len(ys):coverages[unit['id']]=None;continue
            geom=shape(json.loads(self.store.resolve_url(unit['geometry_url']).read_text())['geometry'])
            mask=contains_xy(geom,lon[xs][None,:],lat[ys][:,None])
            values=alpha[np.ix_(ys,xs)]>0
            coverages[unit['id']]=float(values[mask].mean()) if mask.any() else None
        return {**result,'kind':'quarterly_mosaic','year':product['year'],'quarter':product['quarter'],
            'mosaic_period_utc':product['mosaic_period_utc'],'coverage_by_unit':coverages,'tile_ids':product['tile_ids'],
            'cache_scope':'regional_shared','source_value_scale':self.value_scale,
            'note':'Mosaico trimestral oficial L3; combina fechas y aplica selección de píxeles para reducir nubes. Puede conservar huecos. No es una escena de un día.'}
    def render(self,p):
        if p.get('detail'):return self.render_detail(p)
        requested=p['unit'];region=self.region()
        # Unidades externas requieren su propio recorte; nunca atribuir cobertura regional a otra zona.
        b=requested['bbox'];r=region['bbox']
        shared=r[0]-1e-6<=b[0] and r[1]-1e-6<=b[1] and r[2]+1e-6>=b[2] and r[3]+1e-6>=b[3]
        scope=region if shared else requested
        lock_key=hashlib.sha256(json.dumps([scope['bbox'],p['product']['id'],self.settings.get('max_image_side',self.max_side)]).encode()).hexdigest()
        locks=self.root/'locks';locks.mkdir(exist_ok=True)
        with (locks/(lock_key+'.lock')).open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            result=super().render({'unit':scope,'product':p['product']})
        return {**result,'requested_unit_id':requested['id'],'requested_unit_name':requested['name'],
            'territory_fraction_with_data':result.get('coverage_by_unit',{}).get(requested['id']),
            'cache_scope':'regional_shared' if shared else 'outside_region'}
    def render_detail(self,p):
        detail=p['detail'];self.image_file(detail['regional_image_id']+'.json')
        scope={**p['unit'],'id':'mosaic-visible-detail','name':'Recorte de la zona visible','bbox':detail['bbox']}
        side=int(self.settings.get('detail_max_image_side',1024))
        key=hashlib.sha256(json.dumps([detail['bbox'],p['product']['id'],p['product']['revision'],side]).encode()).hexdigest()
        locks=self.root/'locks';locks.mkdir(exist_ok=True)
        with (locks/(key+'.lock')).open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            result=super().render({'unit':scope,'product':p['product'],'detail':detail,
                'max_image_side':side,'projected_pixel':detail['projected_pixel']})
        return {**result,'requested_unit_id':p['unit']['id'],'requested_unit_name':p['unit']['name']}
    def image_file(self,name):
        file=super().image_file(name)
        metadata=file.parent/'metadata.json'
        if metadata.is_file():
            parent=json.loads(metadata.read_text()).get('regional_image_id')
            if isinstance(parent,str) and re.fullmatch(r'[0-9a-f]{64}',parent) and (self.root/parent).is_dir():
                (self.root/parent/'.last_used').touch()
        return file
