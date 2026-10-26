// Beta GeoPDF: MapLibre existente + exportador local 6.0.0. No llama a APIs de procesamiento.
let CemecGeoPdfLibraryPromise;
function CemecLoadGeoPdf(engine) {
  if(CemecGeoPdfLibraryPromise)return CemecGeoPdfLibraryPromise;
  window.maplibregl=engine;
  if(!document.getElementById('cemec-geopdf-hidden-style')){
    const style=document.createElement('style');style.id='cemec-geopdf-hidden-style';
    style.textContent='.hidden-map{overflow:hidden;height:0;width:0;position:fixed;pointer-events:none}';document.head.appendChild(style);
  }
  CemecGeoPdfLibraryPromise=new Promise((resolve,reject)=>{
    const script=document.createElement('script');
    script.src='/cemec-vendor/maplibre-gl-export-6.0.0/maplibre-gl-export.umd.js';
    script.onload=()=>window.MaplibreExportControl?.MapGenerator?resolve(window.MaplibreExportControl):reject(Error('No se pudo cargar el exportador local.'));
    script.onerror=()=>{script.remove();reject(Error('No se pudo cargar el exportador local. Reintenta la exportación.'));};
    document.head.appendChild(script);
  }).catch(error=>{CemecGeoPdfLibraryPromise=null;throw error;});
  return CemecGeoPdfLibraryPromise;
}
function CemecSaveGeoFile(blob,name) {
  const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=name;
  document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);
}
function CemecDecorateGeoMap(canvas,metadata,renderMap) {
  const c=canvas.getContext('2d'),scale=canvas.width/1800;
  c.save();c.scale(scale,scale);
  const w=canvas.width/scale,h=canvas.height/scale;
  const wrap=(value,max,font)=>{
    c.font=font;const lines=[];let line='';
    for(const word of String(value).split(/\s+/)){if(c.measureText(line+' '+word).width>max&&line){lines.push(line);line=word}else line+=(line?' ':'')+word;}
    if(line)lines.push(line);return lines;
  };
  const sourceNames={all:'Todas',static:'Histórico y archivos',firms:'NASA FIRMS',eumetsat:'EUMETSAT'};
  const confidenceNames={all:'Todas',h:'Alta',n:'Nominal',l:'Baja',unknown:'Sin clasificar'};
  const f=metadata.filters;
  const titles=wrap(metadata.unit.name,w-130,'bold 30px Arial');
  const scope=`${f.start} — ${f.end} UTC · Fuente: ${sourceNames[f.source]||f.source} · Sensor: ${f.instrument==='all'?'Todos':f.instrument}`;
  const filters=`Confianza: ${confidenceNames[f.confidence]} · Observación: ${f.daynight==='all'?'Día, noche y sin dato':f.daynight==='D'?'Día':'Noche'} · Satélites: ${f.satellites.length?f.satellites.join(', '):'Todos'}`;
  const lines=[...titles,...wrap(scope,w-130,'21px Arial'),...wrap(filters,w-130,'21px Arial')];
  const headerHeight=56+lines.length*30;
  c.fillStyle='rgba(255,255,255,.96)';c.fillRect(0,0,w,headerHeight);
  c.fillStyle='#244c3d';c.font='bold 19px Arial';c.fillText('CEMEC · MAPA GEORREFERENCIADO · BETA',24,30);
  let y=65;
  lines.forEach((line,i)=>{c.font=i<titles.length?'bold 30px Arial':'21px Arial';c.fillStyle='#233c34';c.fillText(line,24,y);y+=30;});
  c.font='bold 22px Arial';c.fillText('N',w-45,38);c.beginPath();c.moveTo(w-36,49);c.lineTo(w-47,80);c.lineTo(w-36,73);c.lineTo(w-25,80);c.closePath();c.fill();
  const legend=metadata.color_by==='sensor'?
    [['VIIRS','#c96025'],['MODIS','#8954b7'],['SLSTR','#3557ae'],['ABI','#286d78'],['Otro','#68766f']]:
    [['Alta','#c74436'],['Nominal','#e77443'],['Baja','#e6b855'],['Sin clasificar','#8a9591']];
  const present=new Set(metadata.legend_values),entries=legend.filter(([name])=>present.has(name));
  c.save();c.translate(0,-60);
  const bottomHeight=84+Math.max(1,entries.length)*28;
  c.fillStyle='rgba(255,255,255,.96)';c.fillRect(12,h-bottomHeight-68,450,bottomHeight);
  c.fillStyle='#233c34';c.font='bold 20px Arial';c.fillText('Observaciones térmicas · '+(metadata.color_by==='sensor'?'sensor':'confianza'),24,h-bottomHeight-40);
  let ly=h-bottomHeight-12;c.font='20px Arial';
  if(!entries.length){c.fillText('Sin observaciones en la selección',24,ly);ly+=28;}
  for(const [label,color] of entries){c.fillStyle=color;c.beginPath();c.arc(32,ly-6,6,0,Math.PI*2);c.fill();c.fillStyle='#233c34';c.fillText(label,50,ly);ly+=28;}
  c.font='18px Arial';c.fillText(metadata.selection_count+' registros en la selección',24,ly+5);
  c.fillText(metadata.in_frame_count+' dentro del marco del mapa',24,ly+30);
  c.restore();
  // Escala local calculada con las coordenadas del marco; evita recortar el texto de controles HTML.
  const factor=canvas.width/renderMap.getCanvas().clientWidth,sx=w-255,sy=h-150;
  const a=renderMap.unproject([sx*scale/factor,sy*scale/factor]),
    b=renderMap.unproject([(sx+200)*scale/factor,sy*scale/factor]);
  const rad=Math.PI/180,dh=(b.lat-a.lat)*rad,dl=(b.lng-a.lng)*rad;
  const distance=2*6371008.8*Math.asin(Math.sqrt(Math.sin(dh/2)**2+Math.cos(a.lat*rad)*Math.cos(b.lat*rad)*Math.sin(dl/2)**2));
  const magnitude=10**Math.floor(Math.log10(distance)),nice=[5,2,1].map(v=>v*magnitude).find(v=>v<=distance),bar=200*nice/distance;
  c.fillStyle='rgba(255,255,255,.96)';c.fillRect(w-275,h-215,260,100);
  c.fillStyle='#233c34';c.font='20px Arial';c.textAlign='center';c.fillText(nice>=1000?(nice/1000).toLocaleString('es-GT')+' km':nice.toLocaleString('es-GT')+' m',sx+bar/2,sy-20);c.textAlign='left';
  c.strokeStyle='#233c34';c.lineWidth=2;c.beginPath();c.moveTo(sx,sy-9);c.lineTo(sx,sy);c.lineTo(sx+bar,sy);c.lineTo(sx+bar,sy-9);c.stroke();
  metadata.scale_bar={distance_m:nice,latitude:a.lat,method:'great-circle distance at scale bar latitude'};
  const usedSources=new Set(metadata.visible_layers.map(id=>renderMap.getLayer(id)?.source).filter(Boolean));
  metadata.attributions=[...new Set(Object.entries(renderMap.getStyle().sources).filter(([id])=>usedSources.has(id)).map(([,source])=>source.attribution).filter(Boolean)
    .map(value=>value.replace(/<[^>]*>/g,'').replace(/&copy;/g,'©').replace(/&amp;/g,'&')))];
  if(metadata.imagery_sources.some(source=>source.layer!=='cemec-esri-basemap'))metadata.attributions.push('Copernicus Sentinel data · CDSE');
  const credits=wrap(metadata.attributions.join(' · '),w-48,'17px Arial'),footerHeight=55+credits.length*22;
  c.fillStyle='#fff';c.fillRect(0,h-footerHeight,w,footerHeight);c.fillStyle='#344d42';c.font='17px Arial';
  credits.forEach((line,i)=>c.fillText(line,24,h-footerHeight+20+i*22));
  c.fillText('WGS 84 / Pseudo-Mercator · EPSG:3857 · '+metadata.dpi+' DPI · '+(metadata.paper==='LETTER'?'Carta':metadata.paper)+' · '+(metadata.orientation==='portrait'?'Vertical':'Horizontal'),24,h-32);
  c.fillText('Un punto no equivale a un incendio individual ni a superficie quemada. Imágenes de contexto: fechas propias.',24,h-10);
  c.restore();
}
async function CemecGenerateGeoPdf({map,engine,context,paper,orientation,dpi,extent}) {
  if(window.__cemecGeoPdfBusy)throw Error('Ya se está exportando un mapa. Espera a que termine.');
  if(context.loading||context.busy||map.isMoving())throw Error('Espera a que termine la carga o el movimiento del mapa.');
  if(Math.abs(map.getPitch())>.001||Math.abs(map.getBearing())>.001||map.getTerrain()||map.getProjection?.()?.type==='globe')
    throw Error('La beta requiere un mapa plano orientado al norte, sin inclinación ni relieve.');
  window.__cemecGeoPdfBusy=true;
  const pixelRatioDescriptor=Object.getOwnPropertyDescriptor(window,'devicePixelRatio');
  let rendered=null;
  try{
    const lib=await CemecLoadGeoPdf(engine);
    if(!['A4','LETTER'].includes(paper)||!['landscape','portrait'].includes(orientation)||![150,200].includes(dpi))throw Error('Formato de exportación no admitido.');
    const bounds=extent==='unit'?context.unit.bbox:map.getBounds().toArray().flat();
    if(!bounds?.every(Number.isFinite)||bounds[0]>=bounds[2]||bounds[1]>=bounds[3])throw Error('La extensión del mapa no es válida.');
    const metadata={schema_version:1,beta:true,created_at_utc:new Date().toISOString(),
      unit:{id:context.unit.id,name:context.unit.name,kind:context.unit.kind},filters:structuredClone(context.filters),
      catalog_version:context.catalog.version,selection_count:context.rows.length,color_by:context.colorBy,
      legend_values:[...new Set(context.rows.map(row=>context.colorBy==='sensor'?
        (['VIIRS','MODIS','SLSTR','ABI'].includes(row.instrument)?row.instrument:'Otro'):
        ({h:'Alta',n:'Nominal',l:'Baja'}[row.confidence]||'Sin clasificar')))],
      crs:'EPSG:3857',paper,orientation,dpi,extent_mode:extent,requested_bbox_crs84:bounds,
      imagery_sources:[],exporter:'@watergis/maplibre-gl-export@6.0.0',
      limitations:['Salida raster georreferenciada; no conserva capas vectoriales editables.',
        'El marco se ajusta a la proporción del papel. El conteo de selección puede superar los puntos dentro del marco.',
        'Las imágenes cargadas conservan su fecha y resolución; exportar no añade detalle físico.',
        'Los rótulos HTML de municipios no forman parte del mapa exportado.']};
    const visibleLayers=map.getStyle().layers.filter(l=>l.layout?.visibility!=='none');
    metadata.visible_layers=visibleLayers.map(l=>l.id);
    for(const layer of visibleLayers){
      if(layer.type==='raster'){
        const spec=map.getSource(layer.source)?.serialize?.()||{};
        metadata.imagery_sources.push({layer:layer.id,source:layer.source,url:spec.url,coordinates:spec.coordinates,opacity:layer.paint?.['raster-opacity']??1});
      }
    }
    const failures=[];
    // Adaptación acotada al exportador fijado: decorar su canvas antes de escribir el PDF.
    class CemecGenerator extends lib.MapGenerator {
      getRenderedMap(container,style){
        rendered=super.getRenderedMap(container,style);rendered.on('remove',()=>{rendered=null;});
        rendered.on('error',()=>failures.push(true));return rendered;
      }
      renderMapPost(copy){super.renderMapPost(copy);copy.fitBounds([[bounds[0],bounds[1]],[bounds[2],bounds[3]]],{padding:{top:125,bottom:175,left:28,right:28},duration:0});return copy;}
      // El complemento convertiría rótulos HTML en puntos; se omiten para no crear falsas detecciones.
      renderMarkers(copy){return copy;}
      getFormat(copy){
        const format=super.getFormat(copy),original=format.getCanvas.bind(format);let decorated=false;
        format.getCanvas=async()=>{
          if(failures.length||!copy.areTilesLoaded())throw Error('No se completó la carga de las capas. Revisa la conexión o exporta con el fondo CEMEC.');
          const canvas=await original();
          if(!decorated){
            const size=copy.getCanvas(),corners=[[0,0],[size.clientWidth,0],[size.clientWidth,size.clientHeight],[0,size.clientHeight]].map(point=>copy.unproject(point).toArray());
            metadata.corners_crs84={top_left:corners[0],top_right:corners[1],bottom_right:corners[2],bottom_left:corners[3]};
            metadata.pixel_size=[canvas.width,canvas.height];
            const b=copy.getBounds();metadata.in_frame_count=context.rows.filter(row=>b.contains([row.lon,row.lat])).length;
            CemecDecorateGeoMap(canvas,metadata,copy);decorated=true;
          }
          return canvas;
        };
        return format;
      }
    }
    const size=paper==='A4'?[297,210]:[279.4,215.9];if(orientation==='portrait')size.reverse();
    const generator=new CemecGenerator(map,{size,dpi,format:lib.Format.PDF,unit:lib.Unit.mm,geoPdf:true,
      svgVectorOptions:{enabled:false},northIconOptions:{visibility:'none'},
      attributionOptions:{visibility:'none'},scalebarOptions:{visibility:'none'}});
    const blob=await generator.toBlob();
    if(!metadata.corners_crs84||blob.size<1000)throw Error('No se pudo completar el PDF georreferenciado.');
    const stem='CEMEC_mapa_'+context.unit.id.replace(/[^a-zA-Z0-9_-]/g,'_')+'_'+context.filters.start+'_'+context.filters.end;
    return {blob,metadata,stem};
  }finally{
    try{if(rendered)rendered.remove();}
    finally{
      if(pixelRatioDescriptor)Object.defineProperty(window,'devicePixelRatio',pixelRatioDescriptor);
      else delete window.devicePixelRatio;
      window.__cemecGeoPdfBusy=false;
    }
  }
}
function CemecGeoPdfDialog({open,onClose,mapContext,context}) {
  const e=ot.createElement,[paper,setPaper]=ot.useState('A4'),[orientation,setOrientation]=ot.useState('landscape'),
    [dpi,setDpi]=ot.useState(150),[extent,setExtent]=ot.useState('unit'),[running,setRunning]=ot.useState(false),
    [error,setError]=ot.useState(''),[result,setResult]=ot.useState(null);
  const latest=ot.useRef(context);latest.current=context;
  ot.useEffect(()=>{if(open){setError('');setResult(null)}},[open]);
  const close=()=>{if(!running)onClose();};
  const field=(label,value,set,options)=>e('label',{className:'cemec-field'},e('span',null,label),
    e('select',{'aria-label':label,value,disabled:running,onChange:event=>set(event.target.value)},...options.map(([value,label])=>e('option',{key:value,value},label))));
  async function run(){
    if(!mapContext)return;setRunning(true);setError('');setResult(null);
    try{
      const snapshot=latest.current;
      await CemecLoadGeoPdf(mapContext.engine);
      if(snapshot!==latest.current)throw Error('La selección cambió durante la preparación. Revisa los filtros y vuelve a exportar.');
      const output=await CemecGenerateGeoPdf({...mapContext,context:snapshot,paper,orientation,dpi:Number(dpi),extent});
      CemecSaveGeoFile(output.blob,output.stem+'.pdf');setResult(output);
    }catch(err){setError(err.message||'No se pudo exportar el mapa.');}finally{setRunning(false);}
  }
  return e(CemecDialog,{open,onClose:close,title:'Mapa PDF georreferenciado · beta'},
    e('p',null,'Mapa de '+context.unit.name+' · '+context.filters.start+' — '+context.filters.end+' UTC. Conserva los filtros y las capas visibles del mapa de Explorar.'),
    e('p',{className:'cemec-callout'},'Salida raster georreferenciada en EPSG:3857, con título, leyenda, norte, escala y atribución. El marco se ajusta al papel. No conserva capas vectoriales editables.'),
    !mapContext&&e('p',{role:'status'},'Preparando el mapa de Explorar…'),
    e('div',{className:'cemec-advanced-grid'},field('Papel',paper,setPaper,[['A4','A4'],['LETTER','Carta']]),
      field('Orientación',orientation,setOrientation,[['landscape','Horizontal'],['portrait','Vertical']]),
      field('Resolución de salida',dpi,setDpi,[[150,'150 DPI · recomendado'],[200,'200 DPI · mayor consumo']]),
      field('Extensión del mapa',extent,setExtent,[['unit','Territorio completo'],['view','Vista actual del mapa']])),
    e('p',{className:'cemec-muted'},'Incluye las imágenes ya visibles y sus opacidades. Puede cargar teselas para imprimir, pero no sincroniza detecciones ni solicita nuevas imágenes a FIRMS, EUMETSAT o CDSE. Los rótulos HTML de municipios se omiten en esta beta.'),
    running&&e('p',{role:'status'},'Preparando mapa y georreferenciación… Mantén esta ventana abierta.'),
    error&&e('p',{role:'alert',className:'cemec-olci-warning'},error),
    result&&e('p',{role:'status'},'PDF generado. Descarga también sus metadatos para conservar filtros, versión del catálogo y coordenadas.'),
    e('div',{className:'cemec-dialog-actions'},
      result&&e('button',{type:'button',className:'cemec-button secondary',onClick:()=>CemecSaveGeoFile(new Blob([JSON.stringify(result.metadata,null,2)],{type:'application/json'}),result.stem+'.json')},'Descargar metadatos del mapa'),
      e('button',{type:'button',className:'cemec-button primary',disabled:running||!mapContext||context.loading||context.busy,onClick:run},running?'Generando…':'Exportar PDF georreferenciado')));
}
