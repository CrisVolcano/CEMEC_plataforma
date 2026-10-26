// Exportación beta aislada: APIs simuladas, datos operativos intactos, GeoPDF verificado con GDAL.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const {spawn,execFileSync}=require('node:child_process');
const root=path.resolve(__dirname,'..'),cache=path.join(root,'.conda-env/.npm-cache/_npx');
const lib=fs.readdirSync(cache).map(n=>path.join(cache,n,'node_modules/playwright')).find(p=>fs.existsSync(path.join(p,'package.json'))&&JSON.parse(fs.readFileSync(path.join(p,'package.json'))).version==='1.58.2');
const {chromium}=require(lib),temp=fs.mkdtempSync(path.join(os.tmpdir(),'cemec-geopdf-')),ready=path.join(temp,'ready.json');
const fixture=spawn(path.join(root,'.conda-env/bin/python'),[path.join(__dirname,'ui_fixture.py'),'--ready-file',ready,'--sentinel2'],{stdio:['ignore','ignore','inherit']});
const delay=ms=>new Promise(r=>setTimeout(r,ms));const qa=path.join(root,'runtime/geopdf-qa');fs.mkdirSync(qa,{recursive:true});
(async()=>{
 let browser,page;const errors=[],consoleErrors=[];
 try{
  for(let i=0;i<300&&!fs.existsSync(ready);i++){if(fixture.exitCode!==null)throw Error('No inició la prueba');await delay(100)}
  const {port}=JSON.parse(fs.readFileSync(ready));browser=await chromium.launch({headless:true,channel:'chrome'});page=await browser.newPage({viewport:{width:1500,height:1100},acceptDownloads:true});
  page.on('pageerror',e=>errors.push(e.message));page.on('console',msg=>{if(msg.type()==='error')consoleErrors.push(msg.text())});
  await page.goto('http://127.0.0.1:'+port,{waitUntil:'networkidle'});
  assert.equal(await page.locator('script[src*="maplibre-gl-export"]').count(),0,'El exportador no se precarga');
  await page.getByRole('button',{name:'Temporada',exact:true}).click();
  await page.getByRole('combobox',{name:'Unidad de análisis',exact:true}).selectOption('municipio');
  await page.getByRole('combobox',{name:'Unidad administrativa',exact:true}).selectOption('mun-san-andres');
  await page.getByRole('button',{name:/Más filtros/}).click();await page.getByRole('combobox',{name:'Instrumento',exact:true}).selectOption('VIIRS');
  await page.getByRole('button',{name:'Ver resultados',exact:true}).click();await page.getByTestId('detections-count').filter({hasText:/[1-9]/}).waitFor({timeout:60000});await delay(1000);
  const count=Number((await page.getByTestId('detections-count').innerText()).replace(/[^0-9]/g,''));assert.ok(count>0);
  async function open(){await page.getByRole('button',{name:'Generar reporte',exact:true}).click();await page.getByRole('button',{name:'Mapa PDF georreferenciado · beta',exact:true}).click();const d=page.getByRole('dialog',{name:'Mapa PDF georreferenciado · beta',exact:true});await d.waitFor();return d;}
  async function download(d,stem){
   await page.screenshot({path:path.join(qa,stem+'-dialog.png'),fullPage:true});
   const ratioGetter=await page.evaluate(()=>Object.getOwnPropertyDescriptor(window,'devicePixelRatio')?.get?.toString());
   const pending=page.waitForEvent('download',{timeout:90000});await d.getByRole('button',{name:'Exportar PDF georreferenciado',exact:true}).click();
   const pdf=await Promise.race([pending,d.getByRole('alert').waitFor({timeout:90000}).then(async()=>{throw Error(await d.getByRole('alert').innerText())})]);await pdf.saveAs(path.join(qa,stem+'.pdf'));
   const metaPending=page.waitForEvent('download');await d.getByRole('button',{name:'Descargar metadatos del mapa',exact:true}).click();const metaFile=await metaPending;await metaFile.saveAs(path.join(qa,stem+'.json'));
   const meta=JSON.parse(fs.readFileSync(path.join(qa,stem+'.json')));assert.equal(meta.selection_count,count);assert.equal(meta.filters.instrument,'VIIRS');assert.equal(meta.unit.id,'mun-san-andres');
   const info=JSON.parse(execFileSync('gdalinfo',['-json',path.join(qa,stem+'.pdf')],{encoding:'utf8'}));
   assert.ok(info.coordinateSystem.wkt.includes('3857'));assert.equal(info.geoTransform.length,6);assert.ok(info.geoTransform[1]>0&&info.geoTransform[5]<0);
   const points=info.wgs84Extent.coordinates[0];for(const point of Object.values(meta.corners_crs84))assert.ok(points.some(v=>Math.abs(v[0]-point[0])<.00001&&Math.abs(v[1]-point[1])<.00001),'Esquinas PDF y metadatos coinciden');
   fs.writeFileSync(path.join(qa,stem+'-gdal.json'),JSON.stringify(info,null,2));
   assert.equal(await page.getByTestId('detections-count').innerText().then(v=>Number(v.replace(/[^0-9]/g,''))),count,'La exportación no cambia selección');
   assert.equal(await page.locator('.hidden-map').count(),0,'El mapa temporal se libera');
   assert.equal(await page.evaluate(()=>Object.getOwnPropertyDescriptor(window,'devicePixelRatio')?.get?.toString()),ratioGetter,'Se restaura el descriptor nativo de densidad de píxeles');
   assert.ok(meta.scale_bar.distance_m>0&&Number.isFinite(meta.scale_bar.latitude));
   return meta;
  }
  const d=await open();const first=await download(d,'a4-horizontal');assert.equal(first.paper,'A4');assert.equal(first.dpi,150);
  await d.getByRole('button',{name:'Cerrar Mapa PDF georreferenciado · beta',exact:true}).click();
  await page.getByRole('button',{name:'Imagen Mosaico Sentinel-2',exact:true}).click();const imageDialog=page.getByRole('dialog',{name:'Imagen Mosaico Sentinel-2',exact:true});await imageDialog.getByRole('button',{name:'Cargar último mosaico',exact:true}).click();await imageDialog.waitFor({state:'hidden',timeout:60000});
  const secondDialog=await open();await secondDialog.getByRole('combobox',{name:'Papel',exact:true}).selectOption('LETTER');await secondDialog.getByRole('combobox',{name:'Orientación',exact:true}).selectOption('portrait');await secondDialog.getByRole('combobox',{name:'Extensión del mapa',exact:true}).selectOption('view');
  await secondDialog.getByRole('combobox',{name:'Resolución de salida',exact:true}).selectOption('200');
  const second=await download(secondDialog,'carta-vertical-imagen');assert.ok(second.imagery_sources.some(v=>v.layer==='cemec-sentinel2-rgb'));assert.equal(second.dpi,200);assert.equal(second.orientation,'portrait');assert.equal(second.extent_mode,'view');
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(qa,'mobile.png'),fullPage:true});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await secondDialog.getByRole('button',{name:'Cerrar Mapa PDF georreferenciado · beta',exact:true}).click();
  await page.getByRole('button',{name:'Generar reporte',exact:true}).click();assert.ok(await page.getByRole('button',{name:'Generar PDF',exact:true}).isVisible(),'El reporte original sigue disponible');
  const probe=await browser.newPage({viewport:{width:1400,height:1000},acceptDownloads:true});
  await probe.bringToFront();
  probe.on('pageerror',e=>errors.push(e.message));
  await probe.route('**/cemec-vendor/maplibre-gl-export-6.0.0/**',route=>route.fulfill({status:503,body:'QA unavailable'}));
  await probe.goto('http://127.0.0.1:'+port,{waitUntil:'networkidle'});
  await probe.evaluate(()=>document.fonts.ready);
  await probe.getByRole('button',{name:'Generar reporte',exact:true}).click();
  await probe.getByRole('button',{name:'Mapa PDF georreferenciado · beta',exact:true}).click();
  const probeDialog=probe.getByRole('dialog',{name:'Mapa PDF georreferenciado · beta',exact:true});
  await probeDialog.getByRole('button',{name:'Exportar PDF georreferenciado',exact:true}).click();
  await probeDialog.getByRole('alert').filter({hasText:'No se pudo cargar el exportador local'}).waitFor();
  assert.equal(await probeDialog.getByRole('button',{name:'Descargar metadatos del mapa',exact:true}).count(),0);
  await probe.unroute('**/cemec-vendor/maplibre-gl-export-6.0.0/**');
  const retry=probe.waitForEvent('download',{timeout:90000});
  await probeDialog.getByRole('button',{name:'Exportar PDF georreferenciado',exact:true}).click();
  // Mantener la segunda pestaña activa y capturar el estado de recuperación
  // también solicita un frame al compositor de Chromium en modo headless.
  await probe.screenshot({path:path.join(qa,'retry-state.png'),fullPage:true});
  await (await retry).saveAs(path.join(qa,'seleccion-vacia-reintento.pdf'));
  const emptyInfo=JSON.parse(execFileSync('gdalinfo',['-json',path.join(qa,'seleccion-vacia-reintento.pdf')],{encoding:'utf8'}));assert.ok(emptyInfo.geoTransform);
  await probe.close();
  assert.deepEqual(errors,[]);console.log('GeoPDF UI OK: filtros, A4/Carta, 150/200 DPI, dos orientaciones, imagen activa, metadatos, coordenadas GDAL, limpieza, móvil, selección vacía, fallo/reintento y reporte conservado.');
 }catch(e){console.error('Errores de navegador:',errors,consoleErrors);if(page)await page.screenshot({path:path.join(qa,'error.png'),fullPage:true});throw e;}
 finally{if(browser)await browser.close();const done=new Promise(r=>fixture.once('exit',r));fixture.kill('SIGTERM');if(fixture.exitCode===null)await done;fs.rmSync(temp,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1});
