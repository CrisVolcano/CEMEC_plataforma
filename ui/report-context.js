// Páginas adicionales del PDF: el catálogo es una instantánea del momento de generación.
function CemecAppendReport(pdf,catalog,rows,filters,heading,autoTable) {
  const count=value=>new Intl.NumberFormat('es-GT').format(value);
  const provider=row=>row.source?.startsWith('NASA FIRMS')?'NASA FIRMS':row.source?.startsWith('EUMETSAT')?'EUMETSAT':'Histórico / archivos';
  const groups=new Map();
  for(const row of rows){
    const key=JSON.stringify([row.source,row.instrument,row.product_version||'Sin versión']);
    if(!groups.has(key))groups.set(key,{source:row.source,instrument:row.instrument,version:row.product_version||'Sin versión',count:0,days:new Set(),frp:0,frpCount:0});
    const group=groups.get(key);group.count++;group.days.add(row.date);
    if(Number.isFinite(row.frp)){group.frp+=row.frp;group.frpCount++;}
  }
  pdf.addPage();heading('Fuentes y sensores de la selección');
  pdf.setFontSize(10);
  const introduction='Los conteos corresponden a observaciones, no a incendios individuales. Se separan por fuente, instrumento y versión del producto. La confianza sigue las definiciones originales de cada producto.';
  pdf.text(pdf.splitTextToSize(introduction,180),14,43);
  autoTable(pdf,{startY:68,head:[['Fuente','Sensor','Versión','Detecciones','Días','FRP media MW']],
    body:groups.size?[...groups.values()].map(group=>[group.source,group.instrument,group.version,count(group.count),count(group.days.size),group.frpCount?(group.frp/group.frpCount).toFixed(2):'Sin dato']):[['Sin observaciones','','','0','0','Sin dato']],
    styles:{fontSize:8,cellPadding:3},headStyles:{fillColor:[35,76,58]},margin:{top:40,bottom:18,left:14,right:14}});
  if(catalog.comparison?.length){
    pdf.addPage();heading('Comparación seleccionada');
    pdf.setFontSize(10);pdf.text(pdf.splitTextToSize('Mismo territorio, periodo y filtros. Las selecciones siguientes restringen los registros del reporte; no se incluyen otras combinaciones de fuente y sensor.',180),14,43);
    autoTable(pdf,{startY:66,head:[['Selección','Detecciones','Días con observaciones']],body:catalog.comparison.map(group=>{
      const [source,instrument]=group.key.split('|');
      const selected=rows.filter(row=>(provider(row)==='NASA FIRMS'?'firms':provider(row)==='EUMETSAT'?'eumetsat':'static')===source&&row.instrument===instrument);
      return[group.label,count(selected.length),count(new Set(selected.map(row=>row.date)).size)];
    }),styles:{fontSize:9},headStyles:{fillColor:[35,76,58]},margin:{top:40,bottom:18,left:14,right:14}});
    pdf.setFontSize(10);pdf.text(pdf.splitTextToSize('Más detecciones no significa más incendios. Un mismo evento puede ser observado por distintos satélites. Cero registros no certifica cobertura completa ni ausencia de fuego.',180),14,110);
  }
  pdf.addPage();heading('Consultas y disponibilidad');
  let y=43;
  const paragraph=text=>{
    pdf.setFontSize(10);
    const lines=pdf.splitTextToSize(text,180);
    if(y+lines.length*5>273){pdf.addPage();heading('Consultas y disponibilidad');y=43;}
    pdf.setFontSize(10);pdf.text(lines,14,y);y+=lines.length*5+8;
  };
  paragraph('Periodo de observación en UTC: '+filters.start+' a '+filters.end+'. Última observación incorporada al catálogo: '+catalog.date_max+'. Generado en UTC: '+new Date().toISOString()+'.');
  const state=catalog.provider_status;
  for(const [name,kind,sync] of [['NASA FIRMS','sync',state?.last_sync],['EUMETSAT','eumetsat',state?.last_eumetsat_sync]]){
    if(filters.source!=='all'&&filters.source!==(kind==='sync'?'firms':'eumetsat'))continue;
    const latest=(state?.jobs||[]).find(job=>job.kind===kind);
    paragraph(name+': '+(sync?'última consulta exitosa '+sync.at+'. Ventana consultada '+sync.start+' a '+sync.end+'.':'sin consulta exitosa registrada en este servidor.'));
    if(sync&&(filters.start<sync.start.slice(0,10)||filters.end>sync.end.slice(0,10)))paragraph('Advertencia: el periodo del reporte supera la última ventana consultada de '+name+'. El histórico acumulado puede contener observaciones adicionales, pero esta consulta no garantiza la cobertura de todo el rango solicitado.');
    if(latest?.status==='failed')paragraph('Advertencia: la última actualización de '+name+' falló. Se conservaron los datos previamente publicados; los registros actuales no representan una actualización exitosa de esa tarea.');
    if(sync?.complete===false)paragraph('Advertencia: la consulta registrada está incompleta.');
  }
  paragraph('INAB: histórico entregado con la plataforma; no hay una nueva sincronización conectada. Las fechas de consulta de otras fuentes no actualizan este archivo histórico.');
  if(!rows.length)paragraph('No hay detecciones que coincidan con la selección. Esto no demuestra ausencia de incendios. Debe distinguirse de una descarga fallida o de productos no disponibles.');
  paragraph('VIIRS: resolución nominal de 375 m; MODIS: 1 km; SLSTR MWIR: 1 km. El tamaño del píxel no mide superficie quemada. Horario de paso, nubes, algoritmo, cobertura y resolución afectan las observaciones.');
  paragraph('SLSTR: se preservan las clases declaradas por el producto MWIR estándar (Collection 3.2: 0 baja, 1 nominal y 2 alta), sin aplicar umbrales porcentuales de MODIS. Estas categorías no forman una escala común entre sensores.');
  paragraph('FRP se expresa en MW de potencia radiativa observada. No equivale a energía acumulada, área quemada ni una clasificación suficiente de riesgo.');
  paragraph('Referencias: https://firms.modaps.eosdis.nasa.gov/faq/ y https://data.eumetsat.int/product/EO:EUM:DAT:0417 . Dataset '+catalog.version+'; límites '+catalog.boundary_version+'.');
}
