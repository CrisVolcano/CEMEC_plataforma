// Fondo externo bajo demanda; no descarga ni guarda imágenes en el backend.
function CemecBasemapLayer({map,ready,value,onChange,onError}) {
  ot.useEffect(()=>{
    if(!ready||!map)return;
    const id='cemec-esri-basemap';
    if(value!=='esri'){
      if(map.getLayer(id))map.removeLayer(id);
      if(map.getSource(id))map.removeSource(id);
      return;
    }
    const failed=event=>{
      if(event.sourceId!==id)return;
      onError('No se pudo cargar Esri. Se muestra el mapa CEMEC; puedes volver a intentarlo.');
      onChange('cemec');
    };
    map.on('error',failed);
    const {tiles,tileSize,maxzoom,attribution}=CemecBasemapConfig.esri;
    if(!map.getSource(id))map.addSource(id,{type:'raster',tiles,tileSize,maxzoom,attribution});
    const before=map.getStyle().layers.find(layer=>['cemec-olci-rgb','cemec-sentinel2-rgb','protected-fill'].includes(layer.id))?.id;
    if(!map.getLayer(id))map.addLayer({id,type:'raster',source:id,paint:{'raster-opacity':1,'raster-fade-duration':0}},before);
    return()=>map.off('error',failed);
  },[map,ready,value,onChange,onError]);
  return null;
}
function CemecBasemapSelector({value,onChange,error,onError}) {
  const e=ot.createElement,group=ot.useId();
  return e('fieldset',{className:'cemec-basemap-selector'},
    e('legend',null,'Mapa de fondo'),
    ...[['cemec','Mapa CEMEC'],['esri',CemecBasemapConfig.esri.label]].map(([id,label])=>
      e('label',{key:id},e('input',{type:'radio',name:group,checked:value===id,
        onChange:()=>{onError('');onChange(id);}}),label)),
    value==='esri'&&e('small',null,'Referencia visual: la fecha varía según la zona y puede diferir de las detecciones. Requiere Internet.'),
    error&&e('small',{role:'alert',className:'cemec-olci-warning'},error));
}
