'use strict';
const fs=require('node:fs');
const path=require('node:path');
module.exports=function patchReport(script){
  const marker='r.includeTable&&l.length&&(t.addPage()';
  if(!script.includes(marker))throw Error('El generador PDF original no coincide con la adaptación.');
  script=script.replace(marker,'CemecAppendReport(t,a,l,i,d,U);'+marker);
  script=script.replace('t.text(p,14,n),n+=p.length*5+7',
    '(n+p.length*5>273&&(t.addPage(),d("Metodología y trazabilidad"),n=43)),t.text(p,14,n),n+=p.length*5+7');
  script=script.replace('La confianza se normaliza por producto: VIIRS l/n/h; MODIS menor de 30, 30 a 79 y 80 o más.',
    'La confianza utiliza la clasificación de cada producto: VIIRS l/n/h; MODIS conserva su escala porcentual agrupada; SLSTR conserva sus clases originales. No son una escala común de calidad entre sensores.');
  script=script.replace('La misma observación importada de varias fuentes se conserva una sola vez.',
    'Se evitan observaciones repetidas del mismo sensor. Las observaciones de sensores diferentes se conservan separadas y pueden corresponder al mismo evento.');
  script=script.replace('e.fillStyle={h:"#c74436",l:"#d4aa43",n:"#e77443"}[f.confidence]||"#8a9591"',
    'e.fillStyle=a.map_color_by==="sensor"?({VIIRS:"#c96025",MODIS:"#8954b7",SLSTR:"#3557ae",ABI:"#286d78"}[f.instrument]||"#68766f"):({h:"#c74436",l:"#d4aa43",n:"#e77443"}[f.confidence]||"#8a9591")');
  script=script.replace('[["Alta","#c74436"],["Nominal","#e77443"],["Baja","#d4aa43"],["Sin clasificación","#8a9591"]].forEach',
    '(a.map_color_by==="sensor"?[["VIIRS","#c96025"],["MODIS","#8954b7"],["SLSTR","#3557ae"],["ABI","#286d78"],["Otro","#68766f"]]:[["Alta","#c74436"],["Nominal","#e77443"],["Baja","#d4aa43"],["Sin clasificación","#8a9591"]]).forEach');
  script=script.replace('const j=x-1200+C*300','const j=x-(a.map_color_by==="sensor"?1500:1200)+C*300');
  return script+'\n'+fs.readFileSync(path.join(__dirname,'../ui/report-context.js'),'utf8');
};
