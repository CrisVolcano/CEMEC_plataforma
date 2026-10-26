// Capa independiente: no modifica filtros ni registros de detecciones térmicas.
function CemecOlciLayer(props) {
  const e=ot.createElement,[active,setActive]=ot.useState(null);
  const requestRef=ot.useRef(0);
  const {map,ready,unit}=props;
  ot.useEffect(()=>{setActive(null)},[unit.id]);
  ot.useEffect(()=>{
    if(!ready||!map)return;
    for(const [layer,property,normal,soft] of [
      ['road-lines','line-opacity',1,.25],['municipal-lines','line-opacity',1,.5],
      ['protected-fill','fill-opacity',.22,.08],['selected-fill','fill-opacity',.08,0],
      ['water-fill','fill-opacity',.9,.15],['river-lines','line-opacity',1,.4]]){
      if(map.getLayer(layer))map.setPaintProperty(layer,property,active?soft:normal);
    }
    map.getContainer().parentElement?.classList.toggle('cemec-has-olci',!!active);
  },[map,ready,active]);
  return e('div',{className:'cemec-imagery-launchers'},
    ...['olci','sentinel2'].map(sensor=>e(CemecSatelliteLayer,{...props,sensor,active,setActive,requestRef,key:sensor})));
}
function CemecSatelliteLayer({map,ready,unit,period,sensor,active,setActive,requestRef}) {
  const e=ot.createElement;
  const isS2=sensor==='sentinel2',name=isS2?'Mosaico Sentinel-2':'Sentinel-3 OLCI';
  const tag=isS2?'Mosaico':'OLCI',resolution=isS2?10:300;
  const apiBase='/api/'+sensor,layer='cemec-'+sensor+'-rgb',source='cemec-'+sensor+'-image';
  const enabled=active===sensor;
  const setEnabled=value=>setActive(current=>value?sensor:current===sensor?null:current);
  const [open,setOpen]=ot.useState(false),[mode,setMode]=ot.useState('latest');
  const [start,setStart]=ot.useState(period?.start||''),[end,setEnd]=ot.useState(period?.end||'');
  const [search,setSearch]=ot.useState(null),[selected,setSelected]=ot.useState('');
  const today=new Date(),currentQuarter=Math.floor(today.getUTCMonth()/3)+1;
  const [year,setYear]=ot.useState(today.getUTCFullYear()-(currentQuarter===1?1:0));
  const [quarter,setQuarter]=ot.useState(currentQuarter===1?4:currentQuarter-1);
  const quarterLabel=p=>p.year+' · T'+p.quarter+' · '+['enero–marzo','abril–junio','julio–septiembre','octubre–diciembre'][p.quarter-1];
  const [image,setImage]=ot.useState(null),[opacity,setOpacity]=ot.useState(.9);
  const [detail,setDetail]=ot.useState(null),[view,setView]=ot.useState(null);
  const [detailLimits,setDetailLimits]=ot.useState({enabled:false,max_area_km2:isS2?400:40000,max_width_km:isS2?30:300,max_image_side:1024,grid_m:isS2?200:1000});
  const [busy,setBusy]=ot.useState(false),[stage,setStage]=ot.useState(''),[error,setError]=ot.useState('');
  const [configured,setConfigured]=ot.useState(null);
  const generation=ot.useRef(0),controller=ot.useRef(null);
  const clock=s=>new Date(s).toLocaleString('es-GT',{timeZone:'America/Guatemala',dateStyle:'medium',timeStyle:'short'});
  ot.useEffect(()=>{
    let canceled=false;fetch(apiBase+'/status').then(r=>r.ok?r.json():{configured:false}).then(s=>{if(!canceled){setConfigured(s.configured);if(s.detail_limits)setDetailLimits(s.detail_limits);}}).catch(()=>{if(!canceled)setConfigured(false)});
    return()=>{canceled=true};
  },[]);
  ot.useEffect(()=>{
    generation.current++;controller.current?.abort();setBusy(false);setOpen(false);setImage(null);setDetail(null);setView(null);setEnabled(false);setSearch(null);setSelected('');setError('');
    return()=>{generation.current++;controller.current?.abort()};
  },[unit.id]);
  ot.useEffect(()=>{
    if(!ready||!map)return;
    if(!image){if(map.getLayer(layer))map.removeLayer(layer);if(map.getSource(source))map.removeSource(source);return;}
    const [west,south,east,north]=image.bbox_crs84;
    const spec={url:image.url,coordinates:[[west,north],[east,north],[east,south],[west,south]]};
    if(map.getSource(source))map.getSource(source).updateImage(spec);
    else map.addSource(source,{type:'image',...spec});
    if(!map.getLayer(layer))map.addLayer({id:layer,type:'raster',source,paint:{'raster-opacity':opacity,'raster-fade-duration':0}},'protected-fill');
    map.setPaintProperty(layer,'raster-opacity',opacity);
    map.setLayoutProperty(layer,'visibility',enabled?'visible':'none');
  },[ready,map,image]);
  ot.useEffect(()=>{
    if(!ready||!map)return;
    const detailLayer=layer+'-detail',detailSource=source+'-detail';
    if(!detail){if(map.getLayer(detailLayer))map.removeLayer(detailLayer);if(map.getSource(detailSource))map.removeSource(detailSource);return;}
    const [w,s,e,n]=detail.bbox_crs84,spec={url:detail.url,coordinates:[[w,n],[e,n],[e,s],[w,s]]};
    if(map.getSource(detailSource))map.getSource(detailSource).updateImage(spec);else map.addSource(detailSource,{type:'image',...spec});
    if(!map.getLayer(detailLayer))map.addLayer({id:detailLayer,type:'raster',source:detailSource,paint:{'raster-opacity':opacity,'raster-fade-duration':0}},'protected-fill');
  },[ready,map,detail]);
  ot.useEffect(()=>{
    if(!ready||!map)return;
    if(map.getLayer(layer)){
      map.setPaintProperty(layer,'raster-opacity',opacity);
      map.setLayoutProperty(layer,'visibility',enabled?'visible':'none');
    }
    if(map.getLayer(layer+'-detail')){
      map.setPaintProperty(layer+'-detail','raster-opacity',opacity);
      map.setLayoutProperty(layer+'-detail','visibility',enabled?'visible':'none');
    }
  },[ready,map,image,detail,enabled,opacity]);
  ot.useEffect(()=>{
    if(!isS2||!ready||!map||!image)return;
    const update=()=>{
      const bounds=map.getBounds(),b=[bounds.getWest(),bounds.getSouth(),bounds.getEast(),bounds.getNorth()],r=image.bbox_crs84;
      const clip=[Math.max(b[0],r[0]),Math.max(b[1],r[1]),Math.min(b[2],r[2]),Math.min(b[3],r[3])];
      if(clip[0]>=clip[2]||clip[1]>=clip[3]){setView({valid:false,label:'Vuelve a la zona de la imagen'});return;}
      const project=(lon,lat)=>[6378137*lon*Math.PI/180,6378137*Math.log(Math.tan(Math.PI/4+lat*Math.PI/360))];
      const inverse=(x,y)=>[x/6378137*180/Math.PI,(2*Math.atan(Math.exp(y/6378137))-Math.PI/2)*180/Math.PI];
      const [fw,fs]=project(r[0],r[1]),[fe,fn]=project(r[2],r[3]),[w,s]=project(clip[0],clip[1]),[e,n]=project(clip[2],clip[3]),grid=detailLimits.grid_m;
      const west=Math.max(fw,Math.floor(w/grid)*grid),south=Math.max(fs,Math.floor(s/grid)*grid),east=Math.min(fe,Math.ceil(e/grid)*grid),north=Math.min(fn,Math.ceil(n/grid)*grid);
      const [lon1,lat1]=inverse(west,south),[lon2,lat2]=inverse(east,north),scale=Math.cos((lat1+lat2)/2*Math.PI/180);
      const width=(east-west)*scale,height=(north-south)*scale,area=width*height/1e6;
      const valid=area<=detailLimits.max_area_km2&&Math.max(width,height)<=detailLimits.max_width_km*1000&&Math.min(width,height)>=50;
      setView({valid,bbox:[lon1,lat1,lon2,lat2],raw_bbox:b,area,resolution:Math.max(resolution,width/detailLimits.max_image_side,height/detailLimits.max_image_side),label:valid?'Cargar detalle de esta zona':'Acércate para cargar detalle'});
    };
    update();map.on('moveend',update);map.on('resize',update);return()=>{map.off('moveend',update);map.off('resize',update);};
  },[ready,map,image,detailLimits]);
  async function api(url,body,signal){
    const r=await fetch(url,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:undefined,body:body?JSON.stringify(body):undefined,signal});
    const result=await r.json();if(!r.ok)throw Error(result.detail||'No se pudo consultar la imagen');return result;
  }
  async function job(action,body,signal){
    let result=await api(apiBase+'/'+action,body,signal);
    while(['pending','running'].includes(result.status)){
      await new Promise(resolve=>setTimeout(resolve,800));
      result=await api(apiBase+'/jobs/'+result.id,null,signal);
    }
    if(result.status!=='completed')throw Error(result.error||'Consulta incompleta');return result.result;
  }
  async function run(renderOnly=false){
    controller.current?.abort();const control=new AbortController();controller.current=control;
    const id=++generation.current,ticket=++requestRef.current;
    const current=()=>id===generation.current&&ticket===requestRef.current;
    setBusy(true);setError('');
    try{
      let results=search,productId=selected;
      if(!renderOnly){
        setStage(isS2?'Consultando mosaicos trimestrales publicados…':'Buscando pasadas sobre '+unit.name+'…');
        results=await job('search',{unit_id:unit.id,mode,start,end,year:Number(year),quarter:Number(quarter)},control.signal);
        if(!current())return;setSearch(results);productId=results.products[0]?.id||'';setSelected(productId);
        if(!productId){setStage(isS2?'No hay un mosaico publicado para este trimestre. Elige otro o consulta el último disponible.':'No hay imágenes para esta zona y período. Prueba otras fechas.');return;}
        if(mode==='period'&&!isS2){setStage(results.products.length+' referencias disponibles. Elige una pasada.');return;}
      }
      if(!productId)throw Error('Selecciona una pasada');
      setStage(isS2?'Cargando el mosaico regional compartido…':'Preparando color verdadero; puede tardar un momento…');
      const result=await job('render',{unit_id:unit.id,search_id:results.search_id,product_id:productId},control.signal);
      if(!current())return;
      if(isS2){setYear(result.year);setQuarter(result.quarter);}
      setDetail(null);
      setImage(result);setEnabled(true);setStage('');setOpen(false);
    }catch(err){if(current()&&err.name!=='AbortError')setError(err.message);}
    finally{if(id===generation.current)setBusy(false);}
  }
  async function loadDetail(){
    if(!view?.valid||!image)return;
    controller.current?.abort();const control=new AbortController();controller.current=control;
    const id=++generation.current,ticket=++requestRef.current;
    setBusy(true);setError('');setStage('Cargando detalle de esta zona…');
    try{
      const result=await job('detail',{unit_id:unit.id,image_id:image.id,bbox:view.raw_bbox},control.signal);
      if(id!==generation.current||ticket!==requestRef.current)return;
      setDetail(result);setStage('');
    }catch(err){if(id===generation.current&&err.name!=='AbortError'){setError(err.message);setStage('');}}
    finally{if(id===generation.current)setBusy(false);}
  }
  const mismatch=image&&period&&(isS2&&image.mosaic_period_utc?image.mosaic_period_utc[0].slice(0,10)<period.start||image.mosaic_period_utc[1].slice(0,10)>period.end:image.reference_time_utc.slice(0,10)<period.start||image.reference_time_utc.slice(0,10)>period.end);
  const displayed=detail||image;
  const coverage=detail?detail.bbox_fraction_with_data:image?.territory_fraction_with_data;
  const sameDetail=detail&&view?.valid&&detail.bbox_crs84[0]<=view.bbox[0]+1e-7&&detail.bbox_crs84[1]<=view.bbox[1]+1e-7&&
    detail.bbox_crs84[2]>=view.bbox[2]-1e-7&&detail.bbox_crs84[3]>=view.bbox[3]-1e-7&&detail.output_pixel_size_m_at_center<=view.resolution*1.1;
  return e(ot.Fragment,null,
    e('button',{type:'button',className:'cemec-olci-launch'+(isS2?' sentinel2':'')+(enabled?' active':''),onClick:()=>setOpen(true),'aria-label':'Imagen '+name,'aria-expanded':open},
      e('span',{'aria-hidden':true},'▧ '),enabled?(isS2?'S2':'S3')+' · '+Math.round(opacity*100)+' %':(isS2?'Sentinel-2 · Mosaico':'Sentinel-3 · OLCI')),
    busy&&!open&&e('div',{className:'cemec-olci-caption',role:'status'},stage),
    isS2&&image&&enabled&&detailLimits.enabled&&e('div',{className:'cemec-detail-controls','aria-label':isS2?'Detalle del mosaico':'Detalle OLCI'},
      e('button',{type:'button',className:'cemec-button secondary',disabled:busy||!view?.valid||sameDetail,onClick:loadDetail,'aria-label':'Cargar detalle de esta zona',title:'Solicita solo este recorte al pulsar; las vistas guardadas se reutilizan.'},busy?'Cargando…':sameDetail?'Detalle cargado':view?.label||'Acércate para cargar detalle'),
      detail&&e('button',{type:'button',className:'cemec-link',onClick:()=>setDetail(null),disabled:busy},'Vista general'),
      !busy&&view?.valid&&!sameDetail&&e('small',null,'≈ '+Math.round(view.resolution)+' m/px · '+view.area.toFixed(0)+' km² · bajo demanda'),
      error&&!open&&e('small',{role:'alert',className:'cemec-olci-warning'},error)),
    image&&enabled&&!busy&&e('div',{className:'cemec-olci-caption',role:'status'},
      e('div',null,e('strong',null,tag+' · '+image.satellite),e('span',null,isS2?quarterLabel(image):clock(image.reference_time_utc)+' · Guatemala'),
        e('small',null,(detail?'Detalle solicitado':resolution+' m')+(displayed.output_pixel_size_m_at_center?' · Vista ≈ '+Math.round(displayed.output_pixel_size_m_at_center)+' m/px':'')+' · '+(coverage==null?'Cobertura no calculada':(coverage*100).toFixed(1)+(detail?' % del recorte con datos':' % del territorio con datos'))+(isS2?' · Puede conservar huecos':' · Puede contener nubes')),
        isS2&&image.cloud_cover_catalog!=null&&e('small',null,'Nubes en tesela de referencia: '+Number(image.cloud_cover_catalog).toFixed(1)+' %'),
        e('small',null,'Copernicus Sentinel data · CDSE')),
      coverage===0&&e('small',{className:'cemec-olci-warning'},'Esta composición no tiene datos visibles en el territorio. Prueba otra pasada.'),
      mismatch&&e('small',{className:'cemec-olci-warning'},isS2?'El mosaico combina fechas de todo el trimestre; su período difiere del filtro de detecciones.':'La fecha de imagen está fuera del período de detecciones.'),
      e('button',{type:'button',className:'cemec-link',onClick:()=>setEnabled(false),'aria-label':'Ocultar imagen '+tag},'Ocultar')),
    e(CemecDialog,{open,onClose:()=>setOpen(false),title:'Imagen '+name},
      e('p',{className:'cemec-olci-intro'},isS2?'Mosaico trimestral oficial sobre ':'Color verdadero sobre ',e('strong',null,unit.name),isS2?'. Un fondo regional compartido entre territorios y usuarios.':'. Una mirada al territorio que complementa las detecciones térmicas.'),
      e('div',{className:'cemec-olci-modes','aria-label':'Modo de imagen'},
        ...(isS2?[['latest','Último publicado'],['period','Elegir trimestre']]:[['latest','Última disponible'],['period','Elegir período']]).map(([value,label])=>e('button',{key:value,type:'button','aria-pressed':mode===value,disabled:busy,className:'cemec-button '+(mode===value?'primary':'secondary'),onClick:()=>{setMode(value);setSearch(null);setSelected('');setError('');setStage('');}},label))),
      mode==='latest'?e('p',{className:'cemec-muted'},isS2?'Utiliza el trimestre más reciente realmente publicado. Puede existir un retraso entre el fin del trimestre y su disponibilidad.':'Busca la pasada más reciente que intersecta el territorio: primero 7 días y, si no hay resultados, hasta 30. Puede cubrir solo una parte o tener nubes.'):
        isS2?e('div',{className:'cemec-olci-dates'},
          e('label',{className:'cemec-field'},e('span',null,'Año'),e('select',{'aria-label':'Año del mosaico',value:year,disabled:busy,onChange:event=>{setYear(Number(event.target.value));setSearch(null);setStage('');}},Array.from({length:today.getUTCFullYear()-2014},(_,i)=>today.getUTCFullYear()-i).map(y=>e('option',{value:y,key:y},y)))),
          e('label',{className:'cemec-field'},e('span',null,'Trimestre'),e('select',{'aria-label':'Trimestre del mosaico',value:quarter,disabled:busy,onChange:event=>{setQuarter(Number(event.target.value));setSearch(null);setStage('');}},[1,2,3,4].map(q=>e('option',{value:q,key:q,disabled:year===today.getUTCFullYear()&&q>=currentQuarter},'T'+q+' · '+['ene–mar','abr–jun','jul–sep','oct–dic'][q-1]))))):
        e('div',{className:'cemec-olci-dates'},...[[start,setStart,'Desde · UTC'],[end,setEnd,'Hasta · UTC']].map(([value,setter,label])=>e('label',{className:'cemec-field',key:label},e('span',null,label),e('input',{type:'date','aria-label':'Imagen '+label,value,disabled:busy,onChange:event=>{setter(event.target.value);setSearch(null);setSelected('');setStage('');}})))),
      configured===false&&e('p',{className:'cemec-olci-warning',role:'status'},'El acceso CDSE no está configurado o el servicio no está disponible. Las detecciones siguen funcionando.'),
      e('button',{type:'button',className:'cemec-button primary',disabled:busy||configured!==true||mode==='period'&&(isS2?year===today.getUTCFullYear()&&quarter>=currentQuarter:!start||!end||start>end),onClick:()=>run(false)},busy?'Consultando…':isS2?(mode==='latest'?'Cargar último mosaico':'Cargar trimestre'):mode==='latest'?'Buscar última imagen':'Buscar imágenes'),
      stage&&e('p',{role:'status','aria-live':'polite'},stage),error&&e('p',{className:'cemec-olci-warning',role:'alert'},error),
      !isS2&&mode==='period'&&search?.products.length>0&&e('div',{className:'cemec-olci-results'},
        e('label',{className:'cemec-field'},e('span',null,'Pasada disponible'),e('select',{'aria-label':'Pasada '+tag+' disponible',value:selected,disabled:busy,onChange:event=>setSelected(event.target.value)},search.products.map(p=>e('option',{value:p.id,key:p.id},clock(p.time_utc)+' · '+p.satellite+(isS2&&p.cloud_cover_catalog!=null?' · Nubes '+Number(p.cloud_cover_catalog).toFixed(0)+' % (tesela)':''))))),
        e('small',{className:'cemec-muted'},search.products.length+' referencias. Una pasada puede tener varios segmentos; la hora es una referencia del catálogo.'),
        e('button',{type:'button',className:'cemec-button primary',disabled:busy||!selected,onClick:()=>run(true)},'Mostrar esta imagen')),
      image&&e('section',{className:'cemec-olci-current'},
        e('label',{className:'cemec-olci-toggle'},e('input',{type:'checkbox',checked:enabled,onChange:event=>setEnabled(event.target.checked)}),'Mostrar imagen en el mapa'),
        e('label',{className:'cemec-field'},e('span',null,'Opacidad · '+Math.round(opacity*100)+' %'),e('input',{type:'range',min:0,max:100,value:Math.round(opacity*100),'aria-label':'Opacidad de imagen '+tag,onChange:event=>setOpacity(Number(event.target.value)/100)})),
        e('p',null,isS2?quarterLabel(image):image.satellite+' · '+clock(image.reference_time_utc)+' · Guatemala'),
        isS2&&image.cloud_cover_catalog!=null&&e('p',{className:'cemec-muted'},'Nubosidad de la tesela de referencia: '+Number(image.cloud_cover_catalog).toFixed(1)+' %; no es una medición de nubes sobre el territorio.'),
        e('p',{className:'cemec-muted'},isS2?'Combina observaciones de todo el trimestre; no representa una fecha única. Se reutiliza el mismo mosaico regional al cambiar de territorio.':'Ventana procesada: '+image.processing_interval_utc.map(clock).join(' — ')+'. Puede combinar segmentos.'),
        e('div',{className:'cemec-file-links'},e('a',{href:displayed.url,download:(detail?(isS2?'Sentinel2-Detalle':'Sentinel3-OLCI-Detalle'):isS2?'Sentinel2-Mosaico':'Sentinel3-OLCI')+'.png'},'Descargar imagen'),e('a',{href:displayed.metadata_url,download:(detail?(isS2?'Sentinel2-Detalle':'Sentinel3-OLCI-Detalle'):isS2?'Sentinel2-Mosaico':'Sentinel3-OLCI')+'.json'},'Metadatos · JSON')),
        e('button',{type:'button',className:'cemec-button secondary',onClick:()=>setOpen(false)},'Volver al mapa')),
      e('p',{className:'cemec-olci-note'},(isS2?'Mosaico trimestral oficial L3: combina fechas y reduce nubes. Acércate y pulsa «Cargar detalle de esta zona» en el mapa para solicitar un recorte más nítido. El zoom por sí solo no hace descargas. No es una escena del día.':'OLCI observa luz reflejada; SLSTR aporta las detecciones térmicas. Su resolución nominal es de 300 m; ampliar el mapa no añade detalle físico ni inicia descargas.')+' Cobertura con datos no equivale a superficie despejada. Solo una imagen de fondo permanece activa. Cada composición nueva usa cuota CDSE; las guardadas se reutilizan.')));
}
