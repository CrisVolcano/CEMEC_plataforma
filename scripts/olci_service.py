"""RGB CDSE bajo demanda: OLCI y Sentinel-2, con credenciales internas y cachés separadas."""
import fcntl
import hashlib
import json
import math
import os
import re
from pathlib import Path
import secrets
import struct
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import numpy as np
from shapely import contains_xy
from shapely.geometry import shape

TOKEN='https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token'
CATALOG='https://sh.dataspace.copernicus.eu/catalog/v1/search'
PROCESS='https://sh.dataspace.copernicus.eu/process/v1'
def iso(t): return t.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
def parse(s): return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc)
def project(lon,lat): return [6378137*math.radians(lon),6378137*math.log(math.tan(math.pi/4+math.radians(lat)/2))]

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

def png_alpha(content):
    """Lee alpha PNG RGBA 8 bits sin nuevas dependencias de imagen."""
    if content[:8]!=b'\x89PNG\r\n\x1a\n': raise ValueError('CDSE no devolvió una imagen PNG')
    at=8;compressed=[];size=None
    while at<len(content):
        length=struct.unpack('>I',content[at:at+4])[0];kind=content[at+4:at+8];data=content[at+8:at+8+length];at+=length+12
        if kind==b'IHDR':
            w,h,depth,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',data)
            if depth!=8 or color!=6 or interlace!=0 or max(w,h)>2500: raise ValueError('PNG con formato no compatible')
            size=(w,h)
        if kind==b'IDAT': compressed.append(data)
        if kind==b'IEND': break
    if size is None: raise ValueError('PNG incompleto')
    w,h=size;stride=w*4
    decoder=zlib.decompressobj();raw=decoder.decompress(b''.join(compressed),(stride+1)*h+1)
    if len(raw)!=(stride+1)*h: raise ValueError('PNG con tamaño inválido')
    previous=bytearray(stride);alpha=np.zeros((h,w),dtype=np.uint8)
    for y in range(h):
        start=y*(stride+1);method=raw[start];row=bytearray(raw[start+1:start+1+stride])
        if method not in range(5): raise ValueError('Filtro PNG inválido')
        if method:
            for x in range(stride):
                a=row[x-4] if x>=4 else 0;b=previous[x];c=previous[x-4] if x>=4 else 0
                if method==1: predictor=a
                elif method==2: predictor=b
                elif method==3: predictor=(a+b)//2
                else:
                    p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c)
                    predictor=a if pa<=pb and pa<=pc else b if pb<=pc else c
                row[x]=(row[x]+predictor)&255
        alpha[y]=np.frombuffer(row,dtype=np.uint8)[3::4];previous=row
    return alpha

class OlciService:
    config_key='olci'
    collection='sentinel-3-olci'
    api_prefix='/api/olci'
    bands=('B08','B06','B04')
    nominal_resolution=300
    projected_pixel=315
    max_side=2400
    value_scale=1
    def __init__(self,store):
        self.store=store;self.settings=store.config.get(self.config_key,{})
        self.root=store.base/self.settings.get('cache','runtime/'+self.config_key);self.root.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock();self.auth_lock=threading.Lock();self.jobs={};self.searches={}
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix=self.config_key)
        self.token=None;self.expires=0;self.opener=urllib.request.build_opener(NoRedirect())
    def configured(self):
        return bool(self.settings.get('enabled',False) and all(self.credentials().values()))
    def busy(self):
        with self.lock: return any(j['status'] in ('pending','running') for j in self.jobs.values())
    def satellite(self,product):
        return 'Sentinel-3A' if product['id'].startswith('S3A') else 'Sentinel-3B'
    def time_window(self,product):
        if product.get('processing_interval_utc'):
            return tuple(parse(t) for t in product['processing_interval_utc'])
        hour=parse(product['time_utc'])
        return hour-timedelta(minutes=10),min(hour+timedelta(minutes=10),datetime.now(timezone.utc))
    def decorate_result(self,result,alpha,p):
        if p.get('detail'):
            return {**result,'kind':'olci_detail','regional_image_id':p['detail']['regional_image_id'],
                'cache_scope':'viewport_detail_shared','coverage_scope':'visible_crop',
                'territory_fraction_with_data':None,'area_km2':p['detail']['area_km2'],
                'detail_grid_m':p['detail']['grid_m'],
                'note':'Recorte de la misma ventana OLCI. Resolución nominal de 300 m; no añade detalle físico al sensor. Cobertura referida al recorte, no al territorio.'}
        return result
    def credentials(self):
        return {name:os.environ.get(self.settings.get(name+'_env','CDSE_'+name.upper()),'').strip() for name in ('client_id','client_secret')}
    def _http(self,url,body,headers):
        try:
            with self.opener.open(urllib.request.Request(url,data=body,headers=headers),timeout=60) as r:
                data=r.read(20*1024*1024+1)
                if len(data)>20*1024*1024: raise ValueError('Respuesta CDSE demasiado grande')
                return data,dict(r.headers)
        except (urllib.error.URLError,TimeoutError) as e:
            if isinstance(e,urllib.error.HTTPError): raise
            raise RuntimeError('No se pudo conectar a CDSE. Intenta de nuevo; se conserva la imagen guardada.') from None
    def _token(self):
        with self.auth_lock:
            if self.token and time.monotonic()<self.expires: return self.token
            try:
                raw,_=self._http(TOKEN,urllib.parse.urlencode({'grant_type':'client_credentials',**self.credentials()}).encode(),
                    {'Content-Type':'application/x-www-form-urlencoded'})
            except urllib.error.HTTPError as e: raise RuntimeError(f'Autenticación CDSE HTTP {e.code}. Revisa las credenciales del servidor.') from None
            result=json.loads(raw);self.token=result['access_token'];self.expires=time.monotonic()+max(0,int(result.get('expires_in',300))-30)
            return self.token
    def post(self,url,payload,accept):
        for attempt in range(2):
            try: return self._http(url,json.dumps(payload).encode(),{'Authorization':'Bearer '+self._token(),'Content-Type':'application/json','Accept':accept})
            except urllib.error.HTTPError as e:
                if e.code==401 and attempt==0: self.expires=0;continue
                message={403:'La cuenta no tiene acceso a este servicio.',429:'Se alcanzó la cuota o frecuencia permitida; espera y vuelve a intentar.'}.get(e.code,'No se pudo completar la consulta.')
                raise RuntimeError(f'CDSE HTTP {e.code}. {message}') from None
    def unit(self,unit_id):
        unit=next((u for u in self.store.catalog()['units'] if u['id']==unit_id),None)
        if not unit: raise ValueError('Selecciona una unidad de análisis válida')
        return unit
    def submit(self,action,request):
        if not self.configured(): raise ValueError('Falta configurar CDSE en el servidor')
        if not isinstance(request,dict): raise ValueError('Solicitud inválida')
        unit=self.unit(request.get('unit_id'))
        if action=='detail':
            if self.settings.get('detail_enabled',True) is not True:raise ValueError('El detalle está deshabilitado en el servidor')
            image_id=request.get('image_id')
            if not isinstance(image_id,str) or not re.fullmatch(r'[0-9a-f]{64}',image_id):raise ValueError('Carga primero una imagen OLCI válida')
            parent=json.loads(self.image_file(image_id+'.json').read_text())
            if parent.get('kind')=='olci_detail':
                image_id=parent['regional_image_id'];parent=json.loads(self.image_file(image_id+'.json').read_text())
            legacy_olci=parent.get('collection') is None and re.match(r'^S3[AB]_OL_1_EFR_',parent.get('reference',''))
            if parent.get('collection')!=self.collection and not legacy_olci:raise ValueError('El recorte requiere una imagen OLCI')
            view=self.detail_view(request.get('bbox'),parent['bbox_crs84'])
            product={'id':parent['reference'],'time_utc':parent['reference_time_utc'],
                'satellite':parent['satellite'],'processing_interval_utc':parent['processing_interval_utc'],
                'cloud_cover_catalog':parent.get('cloud_cover_catalog')}
            return self.enqueue('detail',{'unit':unit,'product':product,'detail':{'regional_image_id':image_id,**view}})
        if action=='search':
            mode=request.get('mode','latest')
            if mode not in ('latest','period'): raise ValueError('Modo de búsqueda inválido')
            if mode=='period':
                start=parse(str(request.get('start',''))+'T00:00:00Z');end=parse(str(request.get('end',''))+'T23:59:59Z')
                if start>end or (end-start).days>365: raise ValueError('Elige un período válido de hasta 366 días')
                if start>datetime.now(timezone.utc): raise ValueError('No hay imágenes futuras disponibles')
            else: end=datetime.now(timezone.utc);start=end-timedelta(days=7)
            parameters={'unit':unit,'mode':mode,'start':iso(start),'end':iso(min(end,datetime.now(timezone.utc)))}
        elif action=='render':
            with self.lock: search=self.searches.get(request.get('search_id'))
            if not search or search['unit']['id']!=unit['id']: raise ValueError('Repite la búsqueda para este territorio')
            product=next((p for p in search['products'] if p['id']==request.get('product_id')),None)
            if not product: raise ValueError('Selecciona una imagen de la búsqueda')
            parameters={'unit':unit,'product':product}
        else: raise ValueError('Acción no disponible')
        return self.enqueue(action,parameters)
    def enqueue(self,action,parameters):
        with self.lock:
            if any(j['status'] in ('pending','running') for j in self.jobs.values()): raise RuntimeError('Ya hay una consulta de imágenes en curso; espera a que termine')
            identifier=secrets.token_hex(16);job={'id':identifier,'status':'pending','action':action}
            self.jobs[identifier]=job
        self.executor.submit(self._run,identifier,parameters)
        return dict(job)
    def job(self,identifier):
        with self.lock: return dict(self.jobs[identifier]) if identifier in self.jobs else None
    def _run(self,identifier,parameters):
        with self.lock: self.jobs[identifier]['status']='running'
        try:
            result=self.search(parameters) if self.jobs[identifier]['action']=='search' else self.render(parameters)
            with self.lock: self.jobs[identifier].update(status='completed',result=result)
        except Exception as error:
            message=str(error) if isinstance(error,(ValueError,RuntimeError)) else 'No se pudo procesar la imagen. Intenta de nuevo.'
            with self.lock: self.jobs[identifier].update(status='failed',error=message)
        finally:
            with self.lock:
                for key in list(self.jobs)[:-50]: self.jobs.pop(key,None)
    def detail_view(self,bbox,footprint):
        if not isinstance(bbox,list) or len(bbox)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in bbox):
            raise ValueError('La zona visible no tiene coordenadas válidas')
        w,s,e,n=bbox
        if not (-180<=w<e<=180 and -85<s<n<85):raise ValueError('La zona visible no tiene coordenadas válidas')
        w,s,e,n=max(w,footprint[0]),max(s,footprint[1]),min(e,footprint[2]),min(n,footprint[3])
        if w>=e or s>=n:raise ValueError('La vista está fuera de la imagen. Vuelve a la zona cubierta.')
        west,south=project(w,s);east,north=project(e,n)
        grid=float(self.settings.get('detail_grid_m',200))
        if not 10<=grid<=1000:raise ValueError('Configuración de cuadrícula de detalle inválida')
        fw,fs=project(*footprint[:2]);fe,fn=project(*footprint[2:])
        west=max(fw,math.floor(west/grid)*grid);south=max(fs,math.floor(south/grid)*grid)
        east=min(fe,math.ceil(east/grid)*grid);north=min(fn,math.ceil(north/grid)*grid)
        unproject=lambda x,y:[math.degrees(x/6378137),math.degrees(2*math.atan(math.exp(y/6378137))-math.pi/2)]
        w,s=unproject(west,south);e,n=unproject(east,north)
        scale=math.cos(math.radians((s+n)/2));width=(east-west)*scale;height=(north-south)*scale
        area=width*height/1e6
        max_area=float(self.settings.get('detail_max_area_km2',400));max_width=float(self.settings.get('detail_max_width_km',30))
        if area>max_area or max(width,height)>max_width*1000:
            raise ValueError(f'Acércate más: el detalle admite hasta {max_area:g} km² y {max_width:g} km por lado.')
        if min(width,height)<50:raise ValueError('La zona solicitada es demasiado pequeña. Aleja ligeramente el mapa.')
        return {'bbox':[w,s,e,n],'area_km2':area,'grid_m':grid,'projected_pixel':self.nominal_resolution/scale}
    def search(self,p):
        unit=p['unit'];end=parse(p['end']);start=parse(p['start'])
        for interval in ([7,30] if p['mode']=='latest' else [None]):
            if interval: start=end-timedelta(days=interval)
            query={'bbox':unit['bbox'],'datetime':iso(start)+'/'+iso(end),'collections':[self.collection],'limit':100};products={}
            geom=shape(json.loads(self.store.resolve_url(unit['geometry_url']).read_text())['geometry'])
            for _ in range(100):
                raw,_=self.post(CATALOG,query,'application/geo+json');data=json.loads(raw)
                for feature in data.get('features',[]):
                    if feature.get('geometry') and shape(feature['geometry']).intersects(geom):
                        props=feature['properties'];products[feature['id']]={'id':feature['id'],
                            'time_utc':props.get('datetime') or props['start_datetime'],
                            'satellite':self.satellite(feature),
                            'cloud_cover_catalog':props.get('eo:cloud_cover')}
                nxt=data.get('context',{}).get('next')
                if nxt is None: break
                query['next']=nxt
            else: raise RuntimeError('La búsqueda excede el límite de páginas. Reduce las fechas; no se determinó la más reciente.')
            if products or p['mode']=='period': break
        identifier=secrets.token_hex(16)
        result={'search_id':identifier,'unit':unit,'products':sorted(products.values(),key=lambda x:parse(x['time_utc']),reverse=True),
            'search_interval_utc':[iso(start),iso(end)],'catalog_complete':True,'mode':p['mode']}
        with self.lock:
            self.searches[identifier]=result
            for key in list(self.searches)[:-30]: self.searches.pop(key,None)
        return result
    def render_olci_detail(self,p):
        detail=p['detail'];self.image_file(detail['regional_image_id']+'.json')
        scope={**p['unit'],'id':'olci-visible-detail','name':'Recorte de la zona visible','bbox':detail['bbox']}
        side=int(self.settings.get('detail_max_image_side',1024))
        key=hashlib.sha256(json.dumps([detail['bbox'],p['product'],side,detail['regional_image_id']]).encode()).hexdigest()
        locks=self.root/'locks';locks.mkdir(exist_ok=True)
        with (locks/(key+'.lock')).open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            result=self.render({**p,'unit':scope,'detail_prepared':True,
                'max_image_side':side,'projected_pixel':detail['projected_pixel']})
        return {**result,'requested_unit_id':p['unit']['id'],'requested_unit_name':p['unit']['name']}
    def process_image(self,payload,p):
        if self.config_key!='olci' or not p.get('detail'):return self.post(PROCESS,payload,'image/png')
        # El límite de OLCI cubre recortes nuevos; no modifica el motor de mosaicos S2.
        with (self.root/'.detail-budget.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            path=self.root/'detail-usage.json';usage=json.loads(path.read_text()) if path.exists() else {'days':{}}
            day=iso(datetime.now(timezone.utc))[:10]
            row=usage['days'].setdefault(day,{'attempts':0,'completed':0,'processing_units':0})
            limit=int(self.settings.get('max_new_details_per_day',6))
            if row['attempts']>=limit:raise ValueError('Se alcanzó el límite diario de detalles OLCI. Usa un recorte guardado o espera al siguiente día UTC.')
            def save():
                usage['days']=dict(sorted(usage['days'].items())[-90:])
                tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(usage));tmp.replace(path)
            row['attempts']+=1;save()
            result=self.post(PROCESS,payload,'image/png')
            row['completed']+=1
            pu=next((v for k,v in result[1].items() if k.lower()=='x-processingunits-spent'),None)
            if pu is not None:
                try:row['processing_units']+=float(pu)
                except (ValueError,TypeError):pass
            save();return result
    def render(self,p):
        if self.config_key=='olci' and p.get('detail') and not p.get('detail_prepared'):return self.render_olci_detail(p)
        unit=p['unit'];product=p['product'];hour=parse(product['time_utc'])
        lower,upper=self.time_window(product)
        bbox=unit['bbox'];west,south=project(*bbox[:2]);east,north=project(*bbox[2:])
        side=int(p.get('max_image_side',self.settings.get('max_image_side',self.max_side)))
        if not 128<=side<=2400: raise ValueError('max_image_side debe estar entre 128 y 2400')
        pixel=max(p.get('projected_pixel',self.projected_pixel),(east-west)/side,(north-south)/side)
        width=math.ceil((east-west)/pixel);height=math.ceil((north-south)/pixel)
        identity={'unit':unit['id'],'bbox':bbox,'reference':product['id'],'window':[iso(lower),iso(upper)],'gain':2.5,'crs':3857}
        if self.config_key!='olci' or p.get('detail'): identity.update(collection=self.collection,dimensions=[width,height],bands=self.bands)
        if self.config_key=='olci' and p.get('detail'):identity['parent_image']=p['detail']['regional_image_id']
        if product.get('revision'): identity['revision']=product['revision']
        key=hashlib.sha256(json.dumps(identity).encode()).hexdigest()
        folder=self.root/key;meta=folder/'metadata.json';pngfile=folder/'image.png'
        if meta.is_file() and pngfile.is_file():
            (folder/'.last_used').touch()
            return {**json.loads(meta.read_text()),'cached':True}
        red,green,blue=self.bands
        script='//VERSION=3\nfunction setup(){return {input:[{bands:'+json.dumps([*self.bands,'dataMask'])+'}],output:{bands:4,sampleType:"AUTO"}}}\n'+f'function evaluatePixel(s){{return [2.5*s.{red}*{self.value_scale},2.5*s.{green}*{self.value_scale},2.5*s.{blue}*{self.value_scale},s.dataMask]}}'
        payload={'input':{'bounds':{'bbox':[west,south,east,north],'properties':{'crs':'http://www.opengis.net/def/crs/EPSG/0/3857'}},
            'data':[{'type':self.collection,'dataFilter':{'timeRange':{'from':iso(lower),'to':iso(upper)},'mosaickingOrder':'mostRecent'},'processing':{'upsampling':'NEAREST','downsampling':'NEAREST'}}]},
            'output':{'width':width,'height':height,'responses':[{'identifier':'default','format':{'type':'image/png'}}]},'evalscript':script}
        png,headers=self.process_image(payload,p);alpha=png_alpha(png)
        if alpha.shape!=(height,width): raise ValueError('Dimensiones de imagen inesperadas')
        geometry=shape(json.loads(self.store.resolve_url(unit['geometry_url']).read_text())['geometry'])
        x=west+(np.arange(width)+.5)*(east-west)/width;y=north-(np.arange(height)+.5)*(north-south)/height
        lon=np.degrees(x/6378137);lat=np.degrees(2*np.arctan(np.exp(y/6378137))-np.pi/2)
        inside=contains_xy(geometry,lon[None,:],lat[:,None]);valid=alpha>0
        result={'id':key,'unit_id':unit['id'],'unit_name':unit['name'],'reference':product['id'],'satellite':product['satellite'],
            'reference_time_utc':iso(hour),'processing_interval_utc':[iso(lower),iso(upper)],
            'bbox_crs84':bbox,'output_crs':'EPSG:3857','output_bbox':[west,south,east,north],'dimensions':[width,height],
            'collection':self.collection,'nominal_resolution_m':self.nominal_resolution,'brightness_gain':2.5,'bands_rgb':list(self.bands),
            'output_pixel_size_m_at_center':(east-west)/width*math.cos(math.radians((bbox[1]+bbox[3])/2)),
            'cloud_cover_catalog':product.get('cloud_cover_catalog'),
            'bbox_fraction_with_data':float(valid.mean()),'territory_fraction_with_data':float(valid[inside].mean()) if inside.any() else None,
            'url':f'{self.api_prefix}/images/{key}.png','metadata_url':f'{self.api_prefix}/images/{key}.json',
            'generated_at':iso(datetime.now(timezone.utc)),'png_sha256':hashlib.sha256(png).hexdigest(),
            'processing_units':next((v for k,v in headers.items() if k.lower()=='x-processingunits-spent'),None),
            'note':'Composición de ±10 minutos; puede combinar segmentos. Cobertura con datos no mide nubes ni confirma incendios.'}
        result=self.decorate_result(result,alpha,p)
        folder.mkdir(parents=True,exist_ok=True);pngfile.with_suffix('.tmp').write_bytes(png);pngfile.with_suffix('.tmp').replace(pngfile)
        meta.with_suffix('.tmp').write_text(json.dumps(result,ensure_ascii=False));meta.with_suffix('.tmp').replace(meta)
        (folder/'.last_used').touch()
        return {**result,'cached':False}
    def image_file(self,name):
        import re
        if not re.fullmatch(r'[0-9a-f]{64}\.(png|json)',name): raise ValueError('Imagen no encontrada')
        key,ext=name.rsplit('.',1);file=self.root/key/('image.png' if ext=='png' else 'metadata.json')
        if not file.is_file(): raise ValueError('Imagen no encontrada')
        (file.parent/'.last_used').touch()
        metadata=file.parent/'metadata.json'
        if metadata.is_file():
            parent=json.loads(metadata.read_text()).get('regional_image_id')
            if isinstance(parent,str) and re.fullmatch(r'[0-9a-f]{64}',parent) and (self.root/parent).is_dir():
                (self.root/parent/'.last_used').touch()
        return file

class Sentinel2Service(OlciService):
    config_key='sentinel2'
    collection='sentinel-2-l2a'
    api_prefix='/api/sentinel2'
    bands=('B04','B03','B02')
    nominal_resolution=10
    projected_pixel=10.5
    max_side=1600
    def satellite(self,product):
        match=re.match(r'S2([ABC])',product['id'])
        if match: return 'Sentinel-2'+match[1]
        platform=product.get('properties',{}).get('platform','')
        return platform.replace('sentinel-','Sentinel-') if platform else 'Sentinel-2'
