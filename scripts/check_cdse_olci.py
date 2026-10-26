"""Prueba explícita de CDSE: catálogo completo y una composición OLCI. No cambia el visor."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from firms_backend import load_environment

ROOT = Path(__file__).resolve().parent.parent
TOKEN = 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token'
CATALOG = 'https://sh.dataspace.copernicus.eu/catalog/v1/search'
PROCESS = 'https://sh.dataspace.copernicus.eu/process/v1'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start', help='Primer día UTC; requiere --end')
    parser.add_argument('--end', help='Último día UTC, incluido')
    parser.add_argument('--index', type=int, default=0, help='Referencia del catálogo, orden más reciente primero')
    parser.add_argument('--catalog-only', action='store_true', help='Consultar fechas sin procesar otra imagen')
    args = parser.parse_args()
    if bool(args.start) != bool(args.end):
        parser.error('Indica --start y --end juntos')
    load_environment(ROOT)
    credentials = {k:os.environ.get(k, '').strip() for k in ('CDSE_CLIENT_ID','CDSE_CLIENT_SECRET')}
    if not all(credentials.values()):
        raise RuntimeError('Faltan las variables CDSE del servidor')
    opener = urllib.request.build_opener(NoRedirect())
    def request(url, payload, headers):
        try:
            with opener.open(urllib.request.Request(url,data=payload,headers=headers),timeout=120) as response:
                return response.read(),dict(response.headers)
        except urllib.error.HTTPError as error:
            raise RuntimeError(f'CDSE HTTP {error.code} en {url}; revisa acceso, parámetros o cuota') from None
    raw,_ = request(TOKEN,urllib.parse.urlencode({'grant_type':'client_credentials',
        'client_id':credentials['CDSE_CLIENT_ID'],'client_secret':credentials['CDSE_CLIENT_SECRET']}).encode(),
        {'Content-Type':'application/x-www-form-urlencoded'})
    token = json.loads(raw)['access_token']
    print('Autenticación CDSE correcta; token oculto.',flush=True)
    def post(url,payload,accept):
        return request(url,json.dumps(payload).encode(),{'Authorization':'Bearer '+token,
            'Content-Type':'application/json','Accept':accept})
    iso = lambda t:t.isoformat(timespec='seconds').replace('+00:00','Z')
    parse = lambda s:datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc)
    end = datetime.now(timezone.utc) if not args.end else parse(args.end+'T00:00:00Z')+timedelta(days=1,seconds=-1)
    start = end-timedelta(days=7) if not args.start else parse(args.start+'T00:00:00Z')
    if start>=end: raise ValueError('Intervalo inválido')
    import yaml
    bbox = yaml.safe_load((ROOT/'config.yaml').read_text())['firms']['bbox']
    query={'bbox':bbox,'datetime':iso(start)+'/'+iso(end),'collections':['sentinel-3-olci'],'limit':100}
    products={}
    for page in range(100):
        raw,_ = post(CATALOG,query,'application/geo+json')
        result=json.loads(raw)
        products.update({p['id']:p for p in result.get('features',[])})
        nxt=result.get('context',{}).get('next')
        if nxt is None: break
        query['next']=nxt
    else: raise RuntimeError('Catálogo incompleto; reduce el período')
    def time_of(p): return parse(p['properties'].get('datetime') or p['properties']['start_datetime'])
    products=sorted(products.values(),key=time_of,reverse=True)
    if args.catalog_only:
        folder=ROOT/'runtime/cdse-validation'/('catalog-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
        folder.mkdir(parents=True,exist_ok=False)
        summary={'search_interval_utc':[iso(start),iso(end)],'bbox_crs84':bbox,'catalog_complete':True,
            'product_count':len(products),'products':[{'id':p['id'],'time_utc':iso(time_of(p))} for p in products]}
        (folder/'catalog.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
        print(f'Período consultado: {iso(start)} / {iso(end)}; {len(products)} productos. Guardado: {folder.relative_to(ROOT)}',flush=True)
        return
    if not 0<=args.index<len(products): raise RuntimeError(f'Sin referencia seleccionable: {len(products)} productos')
    reference=products[args.index];hour=time_of(reference)
    lower=max(start,hour-timedelta(minutes=10));upper=min(end,hour+timedelta(minutes=10))
    # Web Mercator coincide con el espacio de dibujo del visor.
    def project(lon,lat): return [6378137*math.radians(lon),6378137*math.log(math.tan(math.pi/4+math.radians(lat)/2))]
    west,south=project(bbox[0],bbox[1]);east,north=project(bbox[2],bbox[3])
    width=math.ceil((east-west)/315);height=math.ceil((north-south)/315)
    if max(width,height)>2500: raise ValueError('Salida demasiado grande')
    script='''//VERSION=3
function setup(){return {input:[{bands:["B08","B06","B04","dataMask"]}],output:{bands:4,sampleType:"AUTO"}}}
function evaluatePixel(s){return [2.5*s.B08,2.5*s.B06,2.5*s.B04,s.dataMask]}'''
    payload={'input':{'bounds':{'bbox':[west,south,east,north],'properties':{'crs':'http://www.opengis.net/def/crs/EPSG/0/3857'}},
        'data':[{'type':'sentinel-3-olci','dataFilter':{'timeRange':{'from':iso(lower),'to':iso(upper)},'mosaickingOrder':'mostRecent'},'processing':{'upsampling':'NEAREST'}}]},
        'output':{'width':width,'height':height,'responses':[{'identifier':'default','format':{'type':'image/png'}}]},'evalscript':script}
    print(f'Catálogo: {len(products)} productos. Referencia {iso(hour)}; solicitando RGB {width}×{height}.',flush=True)
    png,headers=post(PROCESS,payload,'image/png')
    if not png.startswith(b'\x89PNG\r\n\x1a\n'): raise RuntimeError('Respuesta no PNG')
    folder=ROOT/'runtime/cdse-validation'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder.mkdir(parents=True,exist_ok=False)
    (folder/'olci-rgb.png').write_bytes(png)
    (folder/'catalog.json').write_text(json.dumps(products,ensure_ascii=False,indent=2))
    metadata={'reference':reference['id'],'reference_time_utc':iso(hour),'search_interval_utc':[iso(start),iso(end)],
        'processing_interval_utc':[iso(lower),iso(upper)],'collection':'sentinel-3-olci','bbox_crs84':bbox,
        'output_crs':'EPSG:3857','output_bbox':[west,south,east,north],'dimensions':[width,height],
        'nominal_sensor_resolution_m':300,'bands_rgb':['B08','B06','B04'],'brightness_gain':2.5,
        'product_count':len(products),'catalog_complete':True,'png_sha256':hashlib.sha256(png).hexdigest(),
        'processing_units':next((v for k,v in headers.items() if k.lower()=='x-processingunits-spent'),None),
        'note':'Ventana de procesamiento; puede combinar segmentos. Transparencia indica ausencia de datos, no nubes.'}
    (folder/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    print('Resultado guardado:',folder.relative_to(ROOT),flush=True)

if __name__=='__main__':
    main()
