// Presentación React legible, inyectada en la compilación original por el servidor.
// Reutiliza sus datos, geometrías, filtros, tablas y exportadores. Sin dependencias nuevas.
function CemecDialog({open, onClose, title, children}) {
  const ref = ot.useRef(null);
  ot.useEffect(() => {
    const dialog = ref.current;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);
  return ot.createElement('dialog', {ref, className:'cemec-dialog', 'aria-label':title,
    onCancel:event=>{event.preventDefault();onClose();}, onClick:event=>{
      if(event.target===event.currentTarget){const box=event.currentTarget.getBoundingClientRect();
        if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)onClose();}
    }}, ot.createElement('header', {className:'cemec-dialog-heading'},
      ot.createElement('div', null, ot.createElement('span',{className:'cemec-eyebrow'},'TU SELECCIÓN'),ot.createElement('h2',null,title)),
      ot.createElement('button',{type:'button',className:'cemec-icon-button','aria-label':'Cerrar '+title,onClick:onClose},'×')),
    ot.createElement('div',{className:'cemec-dialog-body'},children));
}

function CemecView(ctx) {
  const e=ot.createElement;
  const {catalog,filters,unit,unitKind,units,rows,statistics,timeline,backend,busy,loading}=ctx;
  const [page,setPage]=ot.useState('explore');
  const [selectionOpen,setSelectionOpen]=ot.useState(()=>window.innerWidth>760);
  ot.useEffect(()=>{const media=window.matchMedia('(max-width:760px)');const update=()=>setSelectionOpen(!media.matches);media.addEventListener('change',update);return()=>media.removeEventListener('change',update);},[]);
  const [tab,setTab]=ot.useState('map');
  const [advanced,setAdvanced]=ot.useState(false);
  const [report,setReport]=ot.useState(false);
  const [geoPdf,setGeoPdf]=ot.useState(false);
  const [geoMap,setGeoMap]=ot.useState(null);
  const [download,setDownload]=ot.useState(false);
  const [colorBy,setColorBy]=ot.useState('sensor');
  const [left,setLeft]=ot.useState('firms|VIIRS');
  const [right,setRight]=ot.useState('eumetsat|SLSTR');
  const mainRef=ot.useRef(null);
  const adminRef=ot.useRef(null);
  const KIND={region:'Región',municipio:'Municipio',protegida:'Área protegida',manejo:'Zona de manejo'};
  const SOURCE={all:'Todas las fuentes',static:'Histórico y archivos',firms:'NASA FIRMS',eumetsat:'EUMETSAT'};
  const CONF={all:'Todas',h:'Alta',n:'Nominal',l:'Baja',unknown:'Sin clasificar'};
  const COLORS={VIIRS:'#c96025',MODIS:'#8954b7',SLSTR:'#3557ae',ABI:'#286d78'};
  const date=value=>value?new Date(value+'T12:00:00Z').toLocaleDateString('es-GT',{day:'2-digit',month:'short',year:'numeric',timeZone:'UTC'}):'Sin observaciones';
  const instant=value=>value?new Date(value).toLocaleString('es-GT',{timeZone:'America/Guatemala',dateStyle:'medium',timeStyle:'short'})+' · Guatemala':'Sin consulta registrada';
  const sourceOf=row=>row.source?.startsWith('NASA FIRMS')?'firms':row.source?.startsWith('EUMETSAT')?'eumetsat':'static';
  const nav=(name)=>{setPage(name);setAdvanced(false);mainRef.current?.focus();};
  const sensorNames=[...new Set(rows.map(row=>row.instrument))].sort();
  const satelliteNames=catalog.satellites.filter(name=>filters.instrument==='all'||
    (filters.instrument==='VIIRS'&&['S-NPP','NOAA-20','NOAA-21'].includes(name))||
    (filters.instrument==='MODIS'&&['Aqua','Terra'].includes(name))||
    (filters.instrument==='SLSTR'&&/^Sentinel-3[AB]$/.test(name))||
    (filters.instrument==='ABI'&&/^(G18|G19|GOES)/.test(name)));
  const restrictionCount=Number(filters.source!=='all')+Number(filters.instrument!=='all')+
    Number(filters.confidence!=='all')+Number(filters.daynight!=='all')+Number(filters.satellites.length>0);
  const scope=KIND[unit.kind]+' · '+unit.name+' · '+date(filters.start)+' — '+date(filters.end);
  const latestQuery=[backend?.last_sync,backend?.last_eumetsat_sync].filter(Boolean).sort((a,b)=>b.at.localeCompare(a.at))[0];
  const latestFailures=['sync','eumetsat'].map(kind=>(backend?.jobs||[]).find(job=>job.kind===kind)).filter(job=>job?.status==='failed');
  const selectionOutsideQuery=['firms','eumetsat'].filter(provider=>filters.source==='all'||filters.source===provider).filter(provider=>{
    const sync=provider==='firms'?backend?.last_sync:backend?.last_eumetsat_sync;
    return sync&&(filters.start<sync.start.slice(0,10)||filters.end>sync.end.slice(0,10));
  });
  const warning=latestFailures.length?'Alguna fuente no pudo actualizarse. Se conservan las observaciones publicadas; revisa el estado por fuente.':
    selectionOutsideQuery.length?'El periodo seleccionado supera la última ventana consultada de alguna fuente. Revisa su cobertura antes de interpretar los resultados.':null;

  const button=(label,onClick,className='cemec-button secondary',extra={})=>e('button',{type:'button',className,onClick,...extra},label);
  const field=(label,control,extra={})=>e('label',{className:'cemec-field',...extra},e('span',null,label),control);
  const select=(label,value,onChange,options,extra={})=>e('select',{'aria-label':label,value,onChange:event=>onChange(event.target.value),...extra},
    options.map(([value,text])=>e('option',{key:value,value},text)));
  const filterChips=()=>e('div',{className:'cemec-filter-summary','aria-label':'Filtros activos'},
    e('span',{className:'cemec-scope'},KIND[unit.kind]+' · '+unit.name),
    [['source',filters.source!=='all'&&'Fuente: '+SOURCE[filters.source],'all'],
      ['instrument',filters.instrument!=='all'&&'Instrumento: '+filters.instrument,'all'],
      ['confidence',filters.confidence!=='all'&&'Confianza: '+CONF[filters.confidence],'all'],
      ['daynight',filters.daynight!=='all'&&(filters.daynight==='D'?'Solo día':'Solo noche'),'all'],
      ['satellites',filters.satellites.length>0&&'Satélites: '+filters.satellites.join(', '),[]]]
      .filter(([,label])=>label).map(([key,label,reset])=>button(label+' ×',()=>ctx.onFilter(key==='instrument'?{instrument:'all',satellites:[]}:{[key]:reset}),'cemec-chip',{key,'aria-label':'Quitar '+label})),
    restrictionCount===0&&e('span',{className:'cemec-muted'},'Todas las fuentes, instrumentos y clasificaciones'),
    button('Restablecer',ctx.onReset,'cemec-link'));

  const controls=e('details',{className:'cemec-controls',open:selectionOpen,onToggle:event=>setSelectionOpen(event.currentTarget.open),'aria-label':'Selección territorial'},
    e('summary',null,e('strong',null,'Selección territorial'),e('span',null,unit.name+' · '+date(filters.start)+' — '+date(filters.end))),
    e('div',{className:'cemec-control-grid'},
      field('Unidad de análisis',select('Unidad de análisis',unitKind,ctx.onKind,Object.entries(KIND))),
      field('Buscar territorio',e('input',{'aria-label':'Buscar unidad administrativa',type:'search',placeholder:'Nombre del territorio',value:ctx.unitSearch,onChange:event=>ctx.setUnitSearch(event.target.value)})),
      field('Territorio',select('Unidad administrativa',filters.unitId,ctx.onUnit,
        [...(!units.some(item=>item.id===filters.unitId)?[[filters.unitId,unit.name]]:[]),...units.map(item=>[item.id,item.name])])),
      field('Desde · UTC',e('input',{'aria-label':'Fecha inicial',type:'date',value:filters.start,onChange:event=>ctx.onFilter({start:event.target.value})})),
      field('Hasta · UTC',e('input',{'aria-label':'Fecha final',type:'date',value:filters.end,onChange:event=>ctx.onFilter({end:event.target.value})})),
      button('Más filtros'+(restrictionCount?' · '+restrictionCount:''),()=>setAdvanced(true),'cemec-button secondary',{'aria-expanded':advanced,'aria-controls':'cemec-advanced'})),
    e('div',{className:'cemec-periods','aria-label':'Periodos rápidos'},
      ...[[1,'1 día'],[7,'7 días'],[30,'30 días'],['year','Temporada']].map(([days,label])=>button(label,()=>ctx.onPeriod(days),'cemec-period',{key:days})),
      e('span',{className:'cemec-muted'},'Fechas de adquisición en UTC · '+ge(unit.area_ha)+' ha · '+unit.category)),filterChips());

  const advancedDialog=e(CemecDialog,{open:advanced,onClose:()=>setAdvanced(false),title:'Más filtros'},
    e('div',{id:'cemec-advanced',className:'cemec-advanced-grid'},
      field('Fuente de datos',select('Origen',filters.source,value=>ctx.onFilter({source:value}),Object.entries(SOURCE))),
      field('Instrumento',select('Instrumento',filters.instrument,value=>ctx.onFilter({instrument:value,satellites:[]}),
        [['all','Todos los instrumentos'],['VIIRS','VIIRS · 375 m'],['MODIS','MODIS · 1 km'],['SLSTR','SLSTR · Sentinel-3 · 1 km MWIR'],['ABI','ABI · Geoestacionario']])),
      field('Confianza del producto',select('Confianza',filters.confidence,value=>ctx.onFilter({confidence:value}),Object.entries(CONF))),
      field('Observación',select('Día o noche',filters.daynight,value=>ctx.onFilter({daynight:value}),[['all','Día, noche y sin dato'],['D','Día'],['N','Noche']])),
      field('Color del mapa',select('Color del mapa',colorBy,setColorBy,[['sensor','Sensor'],['confidence','Confianza del producto']]))),
    e('fieldset',{className:'cemec-satellites'},e('legend',null,'Satélites'),
      button('Todos los satélites',()=>ctx.onFilter({satellites:[]}),'cemec-link'),
      satelliteNames.map(name=>e('label',{key:name},e('input',{type:'checkbox',checked:filters.satellites.length===0||filters.satellites.includes(name),onChange:()=>{
        const previous=filters.satellites.length?filters.satellites:satelliteNames;
        const next=previous.includes(name)?previous.filter(item=>item!==name):[...previous,name];
        ctx.onFilter({satellites:next.length?next:['__none__']});
      }}),name)),!satelliteNames.length&&e('p',{className:'cemec-muted'},'No hay satélites publicados para este instrumento.')),
    e('p',{className:'cemec-callout'},'La confianza se define según cada producto. SLSTR utiliza sus clases originales; no se aplican los umbrales de MODIS a Sentinel-3.'),
    e('div',{className:'cemec-dialog-actions'},button('Restablecer filtros',()=>{ctx.onFilter({source:'all',instrument:'all',confidence:'all',daynight:'all',satellites:[]});setColorBy('sensor');},'cemec-button secondary'),
      button('Ver resultados',()=>setAdvanced(false),'cemec-button primary')));

  function sourceState(provider) {
    const sync=provider==='firms'?backend?.last_sync:backend?.last_eumetsat_sync;
    const job=(backend?.jobs||[]).find(item=>item.kind===(provider==='firms'?'sync':'eumetsat'));
    return e('div',{className:'cemec-provider-state'},
      e('strong',null,job?.status==='failed'?'Actualización fallida':sync?'Última consulta completada':'Sin consulta registrada'),
      e('span',null,instant(sync?.at)),sync&&e('span',null,'Ventana consultada: '+date(sync.start.slice(0,10))+' — '+date(sync.end.slice(0,10))),
      job?.status==='failed'&&e('span',null,'Se conserva la última versión publicada. Detalle en Administración.'),
      sync?.notice&&e('span',null,sync.notice));
  }

  const sourceCards=()=>e('div',{className:'cemec-source-grid'},
    e('article',{className:'cemec-card'},e('span',{className:'cemec-source-symbol'},'INAB'),e('h3',null,'Histórico institucional'),
      e('p',null,'Observaciones incorporadas al archivo original. Su procedencia se conserva al integrar las nuevas consultas.'),
      e('p',{className:'cemec-muted'},'Sin actualización adicional de INAB conectada. Los archivos importados pueden aportar otros registros.'),
      e('strong',null,'Histórico y archivos')),
    e('article',{className:'cemec-card'},e('span',{className:'cemec-source-symbol'},'NASA FIRMS'),e('h3',null,'VIIRS y MODIS'),
      e('p',null,'Productos de detecciones térmicas de VIIRS en S-NPP, NOAA-20 y NOAA-21, y de MODIS en Terra y Aqua.'),sourceState('firms'),
      e('a',{href:'https://firms.modaps.eosdis.nasa.gov/faq/',target:'_blank',rel:'noreferrer'},'Documentación de NASA FIRMS ↗')),
    e('article',{className:'cemec-card'},e('span',{className:'cemec-source-symbol'},'EUMETSAT'),e('h3',null,'Sentinel-3 · SLSTR'),
      e('p',null,'Producto FRP de Sentinel-3A/B. La integración utiliza la variante MWIR estándar y conserva el tiempo UTC y la calidad original.'),sourceState('eumetsat'),
      e('a',{href:'https://user.eumetsat.int/news-events/news/collection-3-2-of-sentinel-3-near-real-time-fire-radiative-power',target:'_blank',rel:'noreferrer'},'Documentación de EUMETSAT ↗')),
    e('article',{className:'cemec-card'},e('span',{className:'cemec-source-symbol'},'CDSE · SENTINEL HUB'),e('h3',null,'Sentinel-3 y Sentinel-2'),
      e('p',null,'OLCI aporta imágenes de pasadas. Sentinel-2 aporta mosaicos trimestrales oficiales L3 para un fondo más continuo. Complementan las detecciones térmicas sin añadir puntos a sus conteos.'),
      e('p',{className:'cemec-muted'},'Puede tener nubes y cobertura parcial. La fecha de imagen es independiente del período de detecciones.'),
      e('a',{href:'https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S3OLCI.html',target:'_blank',rel:'noreferrer'},'OLCI ↗'),e('span',null,' · '),
      e('a',{href:'https://documentation.dataspace.copernicus.eu/Data/SentinelMissions/Sentinel2.html',target:'_blank',rel:'noreferrer'},'Mosaicos Sentinel-2 ↗')));

  const sourcesPage=e('section',{className:'cemec-page'},e('div',{className:'cemec-section-heading'},
    e('div',null,e('span',{className:'cemec-eyebrow'},'FUENTES Y SENSORES'),e('h2',null,'Entender las diferencias'),e('p',null,'La fuente distribuye los datos; el sensor realiza la observación.')),
    button('Volver a Explorar',()=>nav('explore'))),sourceCards(),
    e('article',{className:'cemec-card'},e('h3',null,'Sensores y resolución nominal'),e('div',{className:'cemec-table-wrap'},e('table',null,
      e('thead',null,e('tr',null,...['Sensor','Resolución nominal','Qué aporta y qué revisar'].map(text=>e('th',{key:text,scope:'col'},text)))),
      e('tbody',null,...[
        ['VIIRS','375 m','Detecciones térmicas; clases de confianza propias del producto.'],
        ['MODIS','1 km','Detecciones térmicas; preservar su clasificación de calidad.'],
        ['SLSTR · MWIR','1 km','Sentinel-3: FRP, incertidumbre y clases originales de confianza.'],
        ['OLCI · RGB','300 m','Imagen óptica de contexto; cobertura con datos no significa superficie despejada ni confirma fuego.'],
        ['MSI · Mosaico L3','10 m en las bandas RGB','Combina fechas del trimestre y reduce nubes. Vista regional compartida y reducida; su escala efectiva aparece en el mapa y los metadatos.'],
        ['ABI','Depende del producto y posición','Observaciones geoestacionarias presentes en el histórico; sin conector nuevo en esta versión.']
      ].map(row=>e('tr',{key:row[0]},...row.map((text,index)=>e(index===0?'th':'td',{key:index,...(index===0?{scope:'row'}:{})},text))))))),
      e('p',{className:'cemec-muted'},'La resolución es nominal. El píxel no representa la superficie quemada; una fuente térmica puede ocupar solo parte de él.')),
    e('div',{className:'cemec-explanation-grid'},...[
      ['Una observación, no un incendio','Un punto indica una anomalía térmica. También puede corresponder a otras fuentes de calor. La confirmación requiere contexto y observaciones de campo.'],
      ['Confianza y calidad','Alta, nominal y baja siguen la definición de cada producto. Las clases y los porcentajes de sensores diferentes no son una escala común.'],
      ['FRP: potencia radiativa','Se expresa en MW. No es superficie quemada ni una medida suficiente de gravedad o riesgo. La media se calcula con valores disponibles.'],
      ['Cobertura y disponibilidad','Nubes, resolución, algoritmos y horario de paso afectan las detecciones. Una descarga fallida o la ausencia de productos no deben interpretarse como cero actividad.']
    ].map(([title,text])=>e('article',{className:'cemec-card',key:title},e('h3',null,title),e('p',null,text)))),
    e('article',{className:'cemec-card'},e('h3',null,'Metodología y trazabilidad'),e('p',null,'Las fechas de adquisición se filtran en UTC. Cada observación conserva fuente, satélite, instrumento y versión del producto. Las unidades territoriales superpuestas pueden compartir observaciones; no se deben sumar como categorías excluyentes.'),
      e('p',null,'Versión de datos: '+catalog.version+' · Límites: '+catalog.boundary_version),
      button('Comparar observaciones',()=>nav('compare'),'cemec-button primary')));

  function bars(series,label,other=null,colors=['#c96025','#3557ae']) {
    const maximum=Math.max(1,...series.map(day=>day.count),...(other||[]).map(day=>day.count));
    return e('div',{className:'cemec-chart-card'},e('h3',null,label),
      e('div',{className:'cemec-chart',role:'img','aria-label':label+' del '+date(filters.start)+' al '+date(filters.end)+'. Consulta los valores en la tabla.'},
        series.map((day,index)=>e('div',{key:day.date,className:'cemec-chart-day',title:day.date+': '+day.count+(other?' / '+other[index].count:'')},
          e('i',{style:{height:(day.count/maximum*100)+'%',background:other?colors[0]:'#50806a'}}),
          other&&e('i',{style:{height:(other[index].count/maximum*100)+'%',background:colors[0]===colors[1]?'repeating-linear-gradient(45deg,'+colors[1]+' 0 3px, transparent 3px 5px)':colors[1]}})))),
      e('div',{className:'cemec-chart-axis'},e('span',null,date(filters.start)),e('span',null,date(filters.end))),
      e('details',{className:'cemec-chart-values'},e('summary',null,'Ver valores por día'),e('div',{className:'cemec-table-wrap'},
        e('table',null,e('thead',null,e('tr',null,e('th',null,'Fecha UTC'),e('th',null,other?'Selección A':'Detecciones'),other&&e('th',null,'Selección B'))),
          e('tbody',null,series.map((day,index)=>e('tr',{key:day.date},e('td',null,day.date),e('td',null,ge(day.count)),other&&e('td',null,ge(other[index].count)))))))));
  }

  const comparisonOptions=[['firms|VIIRS','NASA FIRMS · VIIRS'],['firms|MODIS','NASA FIRMS · MODIS'],['eumetsat|SLSTR','EUMETSAT · SLSTR'],
    ['static|VIIRS','Histórico y archivos · VIIRS'],['static|MODIS','Histórico y archivos · MODIS'],['static|ABI','Histórico y archivos · ABI']];
  const comparisonRows=value=>{const [source,instrument]=value.split('|');return rows.filter(row=>sourceOf(row)===source&&row.instrument===instrument);};
  const leftRows=ot.useMemo(()=>comparisonRows(left),[rows,left]);
  const rightRows=ot.useMemo(()=>comparisonRows(right),[rows,right]);
  const comparisonLabel=value=>comparisonOptions.find(([key])=>key===value)?.[1]||value;
  const comparisonColors=[COLORS[left.split('|')[1]]||'#68766f',COLORS[right.split('|')[1]]||'#68766f'];
  const comparePage=e('section',{className:'cemec-page'},e('div',{className:'cemec-section-heading'},
    e('div',null,e('span',{className:'cemec-eyebrow'},'COMPARAR OBSERVACIONES'),e('h2',null,'Una mirada complementaria'),e('p',null,'Mismo territorio y periodo. Se conservan los filtros activos de Explorar.')),
    button('Volver a Explorar',()=>nav('explore'))),controls,
    e('p',{className:'cemec-callout'},'Más detecciones no significa más incendios. Un mismo evento puede ser observado por varios satélites. Una serie sin puntos no demuestra cobertura completa ni ausencia de fuego.'),
    e('div',{className:'cemec-comparison-grid'},...[[left,setLeft,leftRows,'A'],[right,setRight,rightRows,'B']].map(([value,setValue,subset,label])=>
      e('article',{className:'cemec-card cemec-comparison-map',key:label},field('Selección '+label,select('Sensor de comparación '+label,value,setValue,comparisonOptions)),
        e('p',null,ge(subset.length)+' detecciones que coinciden con los filtros'),ctx.map(subset,unit,colorBy,'comparison'),
        e('div',{className:'cemec-map-legend'},e('strong',null,colorBy==='sensor'?'Color por sensor':'Confianza del producto'),
          colorBy==='sensor'?e('span',null,e('i',{style:{background:COLORS[value.split('|')[1]]||'#68766f'}}),value.split('|')[1]):
            e('span',null,'Alta · nominal · baja · sin clasificar'))))),
    left===right&&e('p',{className:'cemec-callout'},'Elegiste el mismo producto en ambas selecciones. Cambia uno para comparar observaciones diferentes.'),
    e('div',{className:'cemec-comparison-key'},e('span',{style:{color:comparisonColors[0]}},'● A · '+comparisonLabel(left)),
      e('span',{style:{color:comparisonColors[1]}},'● B · '+comparisonLabel(right)+(comparisonColors[0]===comparisonColors[1]?' · barras rayadas':''))),
    bars(zy(leftRows,filters.start,filters.end),'Evolución de las selecciones',zy(rightRows,filters.start,filters.end),comparisonColors),
    e('p',{className:'cemec-muted'},'Las barras cuentan los registros almacenados; sus ceros no certifican observación completa. Consulta las ventanas y el estado de cada fuente.'),
    button('Ver cobertura y fuentes',()=>nav('sources'),'cemec-link'),
    button('Generar reporte de comparación',()=>{setReport('comparison');},'cemec-button primary'));

  const explanation=e('details',{className:'cemec-context'},e('summary',null,'Cómo leer estos datos'),
    e('article',{className:'cemec-card'},e('span',{className:'cemec-eyebrow'},'INTERPRETAR'),e('h3',null,'¿Qué significa un punto?'),
      e('p',null,'Es una observación térmica. No confirma por sí sola un incendio ni representa superficie quemada.'),button('Entender las diferencias →',()=>nav('sources'),'cemec-link')),
    e('article',{className:'cemec-card'},e('h3',null,'Fuentes disponibles'),
      ...[['INAB','Histórico'],['NASA FIRMS','VIIRS / MODIS'],['EUMETSAT','Sentinel-3 / SLSTR'],['CDSE · Sentinel Hub','OLCI y mosaicos trimestrales · opcionales']].map(([source,sensor])=>e('div',{className:'cemec-source-row',key:source},e('strong',null,source),e('span',null,sensor))),
      e('p',{className:'cemec-muted'},'Fuente de datos y sensor son conceptos diferentes.'),button('Estado y metodología →',()=>nav('sources'),'cemec-link')));

  const actionBar=e('div',{className:'cemec-action-bar'},e('div',null,e('strong',null,KIND[unit.kind]+' · '+unit.name),e('small',null,date(filters.start)+' — '+date(filters.end)+' · '+SOURCE[filters.source])),
    e('div',{className:'cemec-actions'},button('Generar reporte',()=>setReport('selection'),'cemec-button primary',{disabled:busy||loading}),
      button('Descargar datos',()=>setDownload(true),'cemec-button secondary',{disabled:busy||loading}),
      button('Ver registros',()=>{nav('explore');setTab('table');},'cemec-link')));

  const reportDialog=e(CemecDialog,{open:!!report,onClose:()=>setReport(false),title:'Reporte de la selección'},
    e('p',null,'El documento utiliza la unidad, fechas y filtros seleccionados.'),
    e('dl',{className:'cemec-report-scope'},...[
      ['Unidad',KIND[unit.kind]],['Territorio',unit.name],['Periodo UTC',date(filters.start)+' — '+date(filters.end)],
      ['Fuentes',SOURCE[filters.source]],['Instrumentos',filters.instrument==='all'?'Todos; presentes: '+(sensorNames.join(', ')||'sin observaciones'):filters.instrument],
      ['Satélites',filters.satellites.length?filters.satellites.join(', '):'Todos'],['Confianza',CONF[filters.confidence]],
      ['Observación',filters.daynight==='all'?'Día, noche y sin dato':filters.daynight==='D'?'Día':'Noche']
    ].map(([label,value])=>e('div',{key:label},e('dt',null,label),e('dd',null,value)))),
    report==='comparison'&&e('p',{className:'cemec-callout'},'El reporte incluye resultados separados por fuente y sensor. Comparación visual actual: '+comparisonLabel(left)+' / '+comparisonLabel(right)+'.'),
    warning&&e('p',{className:'cemec-callout'},warning),
    !rows.length&&e('p',{className:'cemec-callout'},'El reporte indicará que no hay observaciones que coincidan con esta selección. Esto no demuestra ausencia de fuego.'),
    e('h3',null,'Contenido del PDF'),e('ul',{className:'cemec-report-list'},...['Mapa y resumen territorial','Evolución temporal','Resultados por fuente y sensor','Estado de las consultas, metodología y limitaciones'].map(text=>e('li',{key:text},text))),
    e('p',{className:'cemec-muted'},'El mapa del PDF muestra detecciones y límites. Las imágenes OLCI y Sentinel-2 y sus metadatos se descargan por separado desde su panel.'),
    e('label',{className:'cemec-check'},e('input',{type:'checkbox',checked:ctx.config.includeTable,onChange:event=>ctx.setConfig(previous=>({...previous,includeTable:event.target.checked}))}),'Incluir tabla de registros'),
    CemecGeoPdfEnabled&&report!=='comparison'&&e('section',{className:'cemec-geopdf-choice'},e('h3',null,'Mapa para SIG · beta'),
      e('p',null,'Otra salida: un mapa PDF georreferenciado con las capas visibles de Explorar. Incluye las imágenes ya cargadas; no solicita una imagen nueva.'),
      button('Mapa PDF georreferenciado · beta',()=>{setReport(false);nav('explore');setTab('map');setGeoPdf(true);},'cemec-button secondary',{disabled:loading||busy})),
    e('div',{className:'cemec-dialog-actions'},button('Opciones de mapas y lotes',()=>{setReport(false);ctx.onProducts();},'cemec-link'),
      button('Generar PDF',()=>{const override=report==='comparison'?{colorBy,
        rows:[...new Map([...leftRows,...rightRows].map(row=>[row.id,row])).values()],
        comparison:[{key:left,label:comparisonLabel(left)},{key:right,label:comparisonLabel(right)}]
      }:{colorBy};setReport(false);ctx.onExport('report',override);},'cemec-button primary',{disabled:loading||busy})),
    e('p',{className:'cemec-muted'},'Generación al pulsar el botón. Las actualizaciones y los reportes no están programados periódicamente.'));

  const downloadDialog=e(CemecDialog,{open:download,onClose:()=>setDownload(false),title:'Descargar datos'},
    e('p',null,scope),e('p',null,ge(rows.length)+' observaciones con los filtros activos. Incluyen fuente y metadatos originales.'),
    e('div',{className:'cemec-dialog-actions'},button('CSV',()=>{setDownload(false);ctx.onExport('csv');},'cemec-button primary'),
      button('GeoJSON',()=>{setDownload(false);ctx.onExport('geojson');},'cemec-button secondary')));

  const dataPage=e('section',{className:'cemec-page'},e('div',{className:'cemec-section-heading'},
    e('div',null,e('span',{className:'cemec-eyebrow'},'DATOS'),e('h2',null,'Datos y trazabilidad'),e('p',null,ge(catalog.total_points)+' observaciones publicadas · '+catalog.date_min+' — '+catalog.date_max)),
    button('Volver a Explorar',()=>nav('explore'))),
    e('article',{className:'cemec-card'},e('h3',null,'Tu selección actual'),e('p',null,scope),filterChips(),actionBar),
    e('article',{className:'cemec-card'},e('span',{className:'cemec-eyebrow'},'SIG WEB · BETA'),e('h3',null,'Del dato al análisis'),
      e('p',null,'Prueba un ejercicio con municipios, áreas protegidas y detecciones VIIRS de marzo de 2026. Descarga las capas y continúa en GeoLibre, un SIG externo que procesa en tu navegador.'),
      e('p',{className:'cemec-muted'},'Copia fija de prueba. No utiliza los filtros actuales ni inicia sincronizaciones.'),
      e('a',{href:'/sig-beta/',target:'_blank',rel:'noopener noreferrer',className:'cemec-button primary'},'Abrir catálogo SIG · beta ↗')),
    e('article',{className:'cemec-card'},e('h3',null,'Archivo completo y cartografía'),e('p',null,'Estos archivos corresponden al catálogo completo, no a los filtros de tu selección.'),
      e('div',{className:'cemec-file-links'},
        e('a',{href:'/data/catalog.json',download:true},'Catálogo y versión de datos · JSON'),
        e('a',{href:catalog.territories_parquet_url,download:true},'Límites · GeoParquet'),
        e('a',{href:catalog.territories_fgb_url,download:true},'Límites · FlatGeobuf'),
        e('a',{href:catalog.pmtiles_url,download:true},'Cartografía · PMTiles')),

      e('select',{'aria-label':'Partición GeoParquet',id:'cemec-parquet',defaultValue:catalog.partitions.at(-1)?.parquet_url},catalog.partitions.slice().reverse().map(partition=>e('option',{key:partition.date,value:partition.parquet_url},partition.date+' · '+ge(partition.count)+' puntos'))),
      button('Descargar GeoParquet',()=>{const value=document.getElementById('cemec-parquet').value;if(value)location.assign(value);},'cemec-button secondary')),
    e('p',{className:'cemec-muted'},'Datos: '+catalog.version+' · Límites: '+catalog.boundary_version),sourceCards());

  const explore=e('section',{className:'cemec-page cemec-workspace'},
    e('aside',{className:'cemec-selection-rail'},controls,explanation),
    e('div',{className:'cemec-workspace-results'},
    warning&&e('div',{className:'cemec-availability',role:'status'},e('span',null,warning),button('Revisar fuentes',()=>nav('sources'),'cemec-link')),
    e('section',{className:'cemec-metrics','aria-label':'Resumen de la selección'},...[
      ['Detecciones térmicas',statistics.count,'Observaciones, no incendios individuales','detections-count'],
      ['Días con observaciones',statistics.days,'Dentro del periodo seleccionado','observation-days'],
      ['Sensores con observaciones',sensorNames.length,sensorNames.join(' · ')||'Sin registros en esta selección','observation-sensors']
    ].map(([label,value,description,id])=>e('article',{className:'cemec-metric',key:id},e('span',null,label),e('strong',{'data-testid':id},loading?'—':ge(value)),e('small',null,description)))),
    e('div',{className:'cemec-explore-grid'},e('div',{className:'cemec-result-panel'},
      e('div',{className:'cemec-result-tabs',role:'tablist','aria-label':'Vista de resultados'},...[["map","Mapa"],["analysis","Análisis"],["table","Registros"]].map(([name,label])=>
        button(label,()=>setTab(name),'cemec-tab '+(tab===name?'active':''),{key:name,role:'tab','aria-selected':tab===name,
          'data-tab':name,tabIndex:tab===name?0:-1,onKeyDown:event=>{
            const names=['map','analysis','table'];let index=names.indexOf(name);
            if(event.key==='ArrowRight')index=(index+1)%3;else if(event.key==='ArrowLeft')index=(index+2)%3;
            else if(event.key==='Home')index=0;else if(event.key==='End')index=2;else return;
            event.preventDefault();setTab(names[index]);event.currentTarget.parentElement.querySelector('[data-tab="'+names[index]+'"]').focus();
          }}))),
      button('Comparar observaciones',()=>nav('compare'),'cemec-link cemec-compare-launch'),
      loading&&e('div',{className:'cemec-loading',role:'status'},ctx.loadingText),
      !loading&&!rows.length&&tab!=='table'&&e('div',{className:'cemec-empty'},e('strong',null,'Sin detecciones en esta selección'),e('p',null,'Revisa las fechas, territorio y filtros. La ausencia de registros no demuestra ausencia de fuego.'),button('Restablecer selección',ctx.onReset,'cemec-link')),
      tab==='map'&&e(ot.Fragment,null,ctx.map(rows,unit,colorBy,null,setGeoMap),e('div',{className:'cemec-map-legend','aria-label':'Leyenda del mapa'},
        e('strong',null,colorBy==='sensor'?'Color por sensor':'Confianza del producto'),
        ...(colorBy==='sensor'?Object.entries(COLORS):[['Alta','#c74436'],['Nominal','#e77443'],['Baja','#e6b855'],['Sin clasificar','#8a9591']]).map(([label,color])=>e('span',{key:label},e('i',{style:{background:color}}),label)),
        e('span',null,ge(rows.length)+' detecciones en la selección')),bars(timeline,'Observaciones por día')),
      tab==='analysis'&&e(ot.Fragment,null,e('p',{className:'cemec-callout'},'Los indicadores de confianza mantienen las clases de cada producto; no constituyen una clasificación común de riesgo.'),ctx.analysis),
      tab==='table'&&ctx.table))));

  return e('div',{className:'cemec-app'},e('a',{className:'cemec-skip',href:'#cemec-main'},'Ir al contenido'),
    e('header',{className:'cemec-topbar'},e('div',{className:'cemec-identity'},button('CEMEC',()=>nav('explore'),'cemec-brand',{'aria-label':'CEMEC · Inicio'}),e('span',{className:'cemec-product-name'},'Observatorio de calor')),
      e('nav',{'aria-label':'Navegación principal'},...[['explore','Explorar'],['data','Datos'],['sources','Fuentes y sensores']].map(([name,label])=>
        button(label,()=>nav(name),'cemec-nav '+(page===name?'active':''),{key:name,'aria-current':page===name?'page':undefined}))),
      e('details',{className:'cemec-admin-menu',ref:adminRef},e('summary',null,'Administración'),e('div',null,
        button('Ajustes',()=>{adminRef.current.open=false;ctx.onAdmin();},'cemec-menu-item'),
        button('Importar datos',()=>{adminRef.current.open=false;ctx.onImport();},'cemec-menu-item'),
        button('Mapas y lotes',()=>{adminRef.current.open=false;ctx.onProducts();},'cemec-menu-item')))),
    e('main',{id:'cemec-main',ref:mainRef,tabIndex:-1,className:'cemec-main'},
      e('div',{className:'cemec-page-heading'},e('div',null,e('span',{className:'cemec-location'},'Monitoreo territorial / Guatemala'),e('h1',null,page==='explore'?unit.name:'Observatorio de calor'),e('p',null,'Observaciones satelitales para comprender el territorio.')),
        page==='explore'?actionBar:e('div',{className:'cemec-freshness'},e('span',null,'Última consulta exitosa: '+instant(latestQuery?.at)),e('span',null,'Última observación incorporada: '+date(catalog.date_max)+' · UTC'))),
      page==='explore'?explore:page==='sources'?sourcesPage:page==='compare'?comparePage:dataPage,
      page==='explore'&&e('div',{className:'cemec-update-line'},e('span',null,'Última consulta exitosa: '+instant(latestQuery?.at)),e('span',null,'Última observación incorporada: '+date(catalog.date_max)+' · UTC'))),
    e('footer',{className:'cemec-footer'},e('span',null,'CEMEC · Observaciones térmicas para comprender el territorio'),button('Fuentes y metodología',()=>nav('sources'),'cemec-link')),
    advancedDialog,reportDialog,downloadDialog,
    e(CemecGeoPdfDialog,{open:geoPdf,onClose:()=>setGeoPdf(false),mapContext:geoMap,context:{catalog,filters,unit,rows,colorBy,loading,busy}}),
    ctx.hiddenImport,ctx.drawer,ctx.notices);
}
