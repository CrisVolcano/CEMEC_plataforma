// Adaptaciones al bundle original: se aplican al servir, sin modificar el ZIP.
'use strict';
const redesign = require('./redesign.cjs');
module.exports = function patchFrontend(script) {
  const replace = (before, after) => {
    if (!script.includes(before)) throw Error('El visor original no coincide con la adaptación CEMEC.');
    script = script.replace(before, after);
  };
  replace('if(V&&_t.includes(Ft||""))', 'if(V?.import_formats?.includes(Ft||""))');
  replace('async function an(){o(await k2()),ct(await K2())}',
    'async function an(){const k=await k2();o(k);h(Ft=>({...Ft,end:k.date_max}));ct(await K2())}');
  replace('h.current=null}},[i.version]),ot.useEffect',
    'h.current=null}},[i.boundary_version,i.pmtiles_url,i.context_url]),ot.useEffect');
  replace('l.source==="firms"?s.source.startsWith("NASA FIRMS"):!s.source.startsWith("NASA FIRMS")',
    'l.source==="firms"?s.source.startsWith("NASA FIRMS"):l.source==="eumetsat"?s.source.startsWith("EUMETSAT"):!s.source.startsWith("NASA FIRMS")&&!s.source.startsWith("EUMETSAT")');
  replace('f.jsx("option",{value:"ABI",children:"ABI · geoestacionarios"})',
    'f.jsx("option",{value:"ABI",children:"ABI · geoestacionarios"}),f.jsx("option",{value:"SLSTR",children:"SLSTR · Sentinel-3 · 1 km"})');
  replace('c.instrument==="ABI"&&/^(G18|G19|GOES)/.test(x)',
    'c.instrument==="ABI"&&/^(G18|G19|GOES)/.test(x)||c.instrument==="SLSTR"&&/^Sentinel-3[AB]$/.test(x)');
  replace('c.instrument==="MODIS"?["Aqua","Terra"]:s.satellites',
    'c.instrument==="MODIS"?["Aqua","Terra"]:c.instrument==="SLSTR"?s.satellites.filter(Pt=>/^Sentinel-3[AB]$/.test(Pt)):s.satellites');
  replace('f.jsx("option",{value:"firms",children:"NASA FIRMS"})',
    'f.jsx("option",{value:"firms",children:"NASA FIRMS"}),f.jsx("option",{value:"eumetsat",children:"EUMETSAT · Sentinel-3"})');
  replace('[["all","Todas"],["h","Alta"],["n","Nominal"],["l","Baja"]]',
    '[["all","Todas"],["h","Alta"],["n","Nominal"],["l","Baja"],["unknown","Sin clasificar"]]');
  replace('"product_version","units"];return"\\uFEFF"',
    '"product_version","units","observation_utc","confidence_class","confidence_scheme","product_id","entry","raw_fields"];return"\\uFEFF"');
  replace('[Ct,gt]=ot.useState(3),', '[Ct,gt]=ot.useState(3),[eumDays,setEumDays]=ot.useState(3),');
  replace('f.jsx("select",{value:Ct,onChange:x=>gt(Number(x.target.value)),children:[1,2,3,4,5].map',
    'f.jsx("select",{"aria-label":"Periodo FIRMS",value:Ct,onChange:x=>gt(Number(x.target.value)),children:[1,2,3,4,5,10,15,30].filter(days=>days<=(V?.firms?.max_days_per_sync||30)).map');
  replace('f.jsx("label",{children:"Productos satelitales"})',
    'f.jsx("p",{className:"field-hint",children:"Hasta 30 días, incluido hoy en UTC. Las ventanas mayores a 5 días se descargan por bloques y requieren más consultas por producto; dependen de la disponibilidad de NASA."}),f.jsx("label",{children:"Productos satelitales"})');
  replace('it(Ft.status==="running"?"Validando y publicando nuevos datos…":"Esperando ejecución…")',
    'it(Ft.stage||(Ft.status==="running"?"Validando y publicando nuevos datos…":"Esperando ejecución…"))');
  replace('await an(),fe(`Sincronización completada:',
    'await an(),h(previous=>({...previous,start:_t.result.start,end:_t.result.end})),fe(`Sincronización completada:');
  replace('async function nn(){', `async function syncEumetsat(){jt(!0);it("Consultando EUMETSAT…");N("");try{
    const response=await fetch("/api/eumetsat/sync",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({days:eumDays})});
    const job=await response.json();if(!response.ok)throw new Error(job.detail||"No se pudo iniciar Sentinel-3");De(job);
    const done=await J2(job.id,progress=>{De(progress);it(progress.stage||"Procesando Sentinel-3…")});await an();
    h(previous=>({...previous,instrument:"SLSTR",source:"eumetsat",satellites:[],confidence:"all",daynight:"all",start:done.result.start.slice(0,10),end:done.result.end.slice(0,10)}));
    fe(done.result.products_found===0?"Sin productos disponibles para este periodo; no demuestra ausencia de fuego.":
      "Sentinel-3: "+done.result.products_processed+" productos procesados; "+done.result.in_area+" detecciones en el área; "+done.result.added+" nuevas.");
    }catch(error){N(error.message);await an()}finally{jt(!1)}}async function nn(){`);
  const history = 'f.jsxs("div",{className:"form-section",children:[f.jsx("h3",{children:"Historial de tareas"})';
  const panel = `f.jsxs("div",{className:"form-section",children:[
    f.jsx("h3",{children:"EUMETSAT · Sentinel-3"}),
    f.jsx("p",{className:"field-hint",children:V?.eumetsat_configured?"Credenciales configuradas en el servidor. Descarga de todos los productos MWIR estándar del área.":"Configura las credenciales EUMETSAT en el servidor."}),
    f.jsxs("label",{children:["Periodo de descarga",f.jsx("select",{"aria-label":"Periodo Sentinel-3",value:eumDays,onChange:event=>setEumDays(Number(event.target.value)),children:[1,3,5,10,30].filter(days=>days<=(V?.eumetsat?.max_days_per_sync||31)).map(days=>f.jsx("option",{value:days,children:days===1?"Último día":"Últimos "+days+" días"},days))})]}),
    f.jsx("button",{className:"primary full",disabled:bt||!V?.eumetsat_configured||V?.busy,onClick:()=>void syncEumetsat(),children:"Sincronizar Sentinel-3"}),
    bt&&pt?.kind==="eumetsat"&&f.jsx("p",{className:"field-hint",role:"status",children:pt.stage||K}),
    V?.last_eumetsat_sync&&f.jsx("p",{className:"field-hint",children:"Última sincronización Sentinel-3: "+new Date(V.last_eumetsat_sync.at).toLocaleString("es-GT")+" · "+V.last_eumetsat_sync.products_processed+" productos · "+V.last_eumetsat_sync.in_area+" detecciones en el área"}),
    f.jsx("p",{className:"field-hint",children:"SLSTR utiliza sus propias clases de confianza. Los filtros siguen la clasificación original, sin aplicar umbrales de VIIRS. Cada punto es una observación, no un incendio individual."}),
    f.jsx("a",{className:"external-text",href:"https://user.eumetsat.int",target:"_blank",rel:"noreferrer",children:"Cuenta y licencias EUMETSAT"})]}),`;
  replace(history, panel + history);
  // Tareas extensas siguen activas en el backend al cerrar el panel/navegador.
  replace('s<300;s++', 's<2400;s++');
  return process.env.CEMEC_LEGACY_UI === '1' ? script : redesign(script);
};
