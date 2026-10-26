// Adaptador de presentación: conserva el motor original, sus hooks y exportadores.
'use strict';
const fs = require('node:fs');
const path = require('node:path');

function callAt(script, marker) {
  const offset = script.indexOf(marker);
  if (offset < 0) throw Error('Falta un componente del visor original: ' + marker);
  const start = script.indexOf('f.jsxs(', offset);
  let depth = 0, quote = null, escaped = false;
  for (let i = start + 6; i < script.length; i++) {
    const ch = script[i];
    if (quote) {
      if (escaped) escaped = false;
      else if (ch === '\\') escaped = true;
      else if (ch === quote) quote = null;
    } else if ('"\'`'.includes(ch)) quote = ch;
    else if (ch === '(') depth++;
    else if (ch === ')' && --depth === 0) return script.slice(start, i + 1);
  }
  throw Error('No se pudo recuperar el componente original.');
}

module.exports = function redesign(script) {
  const analysis = callAt(script, 'j==="analysis"&&f.jsxs');
  const table = callAt(script, 'j==="table"&&f.jsxs');
  const drawer = callAt(script, 'z&&f.jsxs(f.Fragment');
  const busy = callAt(script, 'bt&&f.jsxs("div",{className:"busy-banner"');
  const error = callAt(script, 'w&&f.jsxs("div",{className:"toast error-toast"');
  const notice = callAt(script, 'B&&f.jsxs("div",{className:"toast"');
  const start = script.indexOf('const ar=Math.floor((Date.now()-Date.parse(s.date_max');
  const end = script.indexOf('}cy.createRoot', start);
  if (start < 0 || end < 0) throw Error('La presentación original no coincide con el adaptador.');
  const presentation = `return f.jsx(CemecView,{
    catalog:s,filters:c,unit:xe,units:Fs,unitKind:p,unitSearch:Z,setUnitSearch:et,
    onUnit:On,onKind:$s,onFilter:ie,onPeriod:en,
    onReset:()=>{const end=new Date().toISOString().slice(0,10);h({...jm,start:Om(end,-6),end});S("region");et("")},
    rows:Se,statistics:Ie,timeline:Ya,loading:q,loadingText:F,backend:V,busy:bt,
    map:(points,unit,colorBy,syncKey,onMapReady)=>f.jsx(qy,{catalog:s,points,unit,onSelect:On,colorBy,syncKey,imagePeriod:c,onMapReady}),
    analysis:${analysis},table:${table},drawer:z&&${drawer},
    hiddenImport:f.jsx("input",{ref:Te,type:"file",className:"hidden",accept:".csv,.geojson,.json,.zip,.gpkg,.parquet,.fgb",onChange:event=>{const file=event.target.files?.[0];if(file)tr(file)}}),
    notices:f.jsxs(f.Fragment,{children:[bt&&${busy},w&&${error},B&&${notice}]}),
    onAdmin:()=>L("settings"),onImport:()=>{L("data");Te.current?.click()},
    onProducts:()=>{L("export");Mt(!1)},onExport:(kind,override)=>Xa(kind,override),config:lt,setConfig:at
  })`;
  script = script.slice(0, start) + presentation + script.slice(end);
  const replace = (before, after) => {
    if (!script.includes(before)) throw Error('No coincide una adaptación de presentación.');
    script = script.replace(before, after);
  };
  replace('instrument:"VIIRS",daynight:"all",source:"all"};function CM()',
    'instrument:"all",daynight:"all",source:"all"};function CM()');
  replace('h(Ft=>({...Ft,start:k.date_max.slice(0,4)+"-01-01",end:k.date_max}))',
    'h(Ft=>{const end=new Date().toISOString().slice(0,10);return {...Ft,start:Om(end,-6),end}})');
  replace('const k=s.date_max;ie({start:x==="year"?',
    'const k=new Date().toISOString().slice(0,10);ie({start:x==="year"?');
  replace('version:s.version+(g.length?`+local-${b}`:"")}:null,[s,g,b]',
    'version:s.version+(g.length?`+local-${b}`:""),provider_status:V}:null,[s,g,b,V]');
  replace('async function Xa(x){', 'async function Xa(x,override){');
  replace('await _t(de,xe,Se,c,lt)', 'await _t({...de,comparison:override?.comparison,map_color_by:override?.colorBy},xe,override?.rows||Se,c,lt)');
  // El mismo componente cartográfico permite elegir color sin modificar sus datos.
  replace('function qy({catalog:i,points:l,unit:s,onSelect:o})',
    'function qy({catalog:i,points:l,unit:s,onSelect:o,colorBy="confidence",syncKey=null,imagePeriod=null,onMapReady=null})');
  replace('className:"map-shell",children:[f.jsx("div",{ref:c',
    'className:"map-shell",children:[!syncKey&&f.jsx(CemecOlciLayer,{map:h.current,ready:m,unit:s,period:imagePeriod}),f.jsx("div",{ref:c');
  replace('properties:{id:q.id,confidence:q.confidence,record:JSON.stringify(q)}',
    'properties:{id:q.id,confidence:q.confidence,instrument:q.instrument,record:JSON.stringify(q)}');
  replace('},[l,m]),ot.useEffect',
    '},[l,m]),ot.useEffect(()=>{if(m&&h.current?.getLayer("heat-points")){h.current.setPaintProperty("heat-points","circle-color",colorBy==="sensor"?["match",["get","instrument"],"VIIRS","#c96025","MODIS","#8954b7","SLSTR","#3557ae","ABI","#286d78","#68766f"]:["match",["get","confidence"],"h","#c74436","l","#e6b855","n","#e77443","#8a9591"])}},[colorBy,m]),ot.useEffect');
  replace('},[colorBy,m]),ot.useEffect', `},[colorBy,m]),ot.useEffect(()=>{
    if(!syncKey||!m||!h.current)return;const map=h.current,id=crypto.randomUUID(),channel="cemec-map-"+syncKey;let muted=false;
    const publish=()=>{if(!muted)window.dispatchEvent(new CustomEvent(channel,{detail:{id,center:map.getCenter().toArray(),zoom:map.getZoom()}}))};
    const receive=event=>{const value=event.detail;if(value?.id!==id&&Array.isArray(value?.center)&&Number.isFinite(value?.zoom)){muted=true;map.jumpTo({center:value.center,zoom:value.zoom});muted=false}};
    map.on("moveend",publish);window.addEventListener(channel,receive);
    return()=>{map.off("moveend",publish);window.removeEventListener(channel,receive)};
  },[syncKey,m]),ot.useEffect`);
  // Selector integrado en el panel existente; el raster solo se crea al elegirlo.
  replace('const c=ot.useRef(null),h=ot.useRef(null),[m,d]=ot.useState(!1)',
    'const [basemap,setBasemap]=ot.useState(CemecBasemapConfig.default),[basemapError,setBasemapError]=ot.useState(""),c=ot.useRef(null),h=ot.useRef(null),[m,d]=ot.useState(!1)');
  replace('className:"map-shell",children:[!syncKey&&f.jsx(CemecOlciLayer',
    'className:"map-shell",children:[f.jsx(CemecBasemapLayer,{map:h.current,ready:m,value:basemap,onChange:setBasemap,onError:setBasemapError}),!syncKey&&f.jsx(CemecOlciLayer');
  replace('f.jsx("strong",{children:"Capas del mapa"}),f.jsxs("label"',
    'f.jsx("strong",{children:"Capas del mapa"}),f.jsx(CemecBasemapSelector,{value:basemap,onChange:setBasemap,error:basemapError,onError:setBasemapError}),f.jsxs("label"');
  replace('Cartografía CEMEC · sin servicios GIS', 'Límites CEMEC · fondo externo opcional');
  replace('Z.current=o,ot.useEffect',
    'Z.current=o,ot.useEffect(()=>{if(!onMapReady||syncKey||!m||!h.current)return;onMapReady({map:h.current,engine:Vh});return()=>onMapReady(null)},[m,onMapReady,syncKey]),ot.useEffect');
  const view = fs.readFileSync(path.join(__dirname, '../ui/cemec-view.js'), 'utf8');
  const olci = fs.readFileSync(path.join(__dirname, '../ui/olci-layer.js'), 'utf8');
  const basemap=fs.readFileSync(path.join(__dirname,'../ui/basemap-layer.js'),'utf8');
  const basemapConfig=JSON.parse(fs.readFileSync(path.join(__dirname,'../ui/basemaps.json'),'utf8'));
  const geopdf=fs.readFileSync(path.join(__dirname,'../ui/geopdf.js'),'utf8');
  return script.replace('const jm=', 'const CemecGeoPdfEnabled='+(process.env.CEMEC_GEO_PDF_BETA!=='0')+';const CemecBasemapConfig='+JSON.stringify(basemapConfig)+';\n'+basemap+'\n'+geopdf+'\n'+view + '\n' + olci + '\nconst jm=');
};
