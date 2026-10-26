// Datos CDSE simulados; verifica alternancia, fechas, metadatos y móvil sin cuota real.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const root=path.resolve(__dirname,'..'),cache=path.join(root,'.conda-env/.npm-cache/_npx');
const lib=fs.readdirSync(cache).map(n=>path.join(cache,n,'node_modules/playwright')).find(p=>fs.existsSync(path.join(p,'package.json'))&&JSON.parse(fs.readFileSync(path.join(p,'package.json'))).version==='1.58.2');
const {chromium}=require(lib),temp=fs.mkdtempSync(path.join(os.tmpdir(),'cemec-sentinel2-')),ready=path.join(temp,'ready.json');
const fixture=spawn(path.join(root,'.conda-env/bin/python'),[path.join(__dirname,'ui_fixture.py'),'--ready-file',ready,'--sentinel2'],{stdio:['ignore','ignore','inherit']});
const delay=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 let browser,page;const errors=[];const qa=path.join(root,'runtime/sentinel2-qa');fs.mkdirSync(qa,{recursive:true});
 try{
  for(let i=0;i<300&&!fs.existsSync(ready);i++){if(fixture.exitCode!==null)throw Error('No inició el servidor de prueba');await delay(100)}
  const {port}=JSON.parse(fs.readFileSync(ready)),base='http://127.0.0.1:'+port;
  browser=await chromium.launch({headless:true,channel:'chrome'});page=await browser.newPage({viewport:{width:1500,height:1100}});
  page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&m.text().startsWith('Error:'))errors.push(m.text())});
  await page.goto(base,{waitUntil:'networkidle'});
  const count=await page.getByTestId('detections-count').innerText();
  const s2=page.getByRole('button',{name:'Imagen Mosaico Sentinel-2',exact:true}),s3=page.getByRole('button',{name:'Imagen Sentinel-3 OLCI',exact:true});
  await s2.waitFor();await s3.waitFor();
  const dialog=page.getByRole('dialog',{name:'Imagen Mosaico Sentinel-2',exact:true});
  await s2.click();await dialog.getByRole('button',{name:'Cargar último mosaico',exact:true}).click();
  await dialog.waitFor({state:'hidden',timeout:60000});await page.getByRole('button',{name:'Ocultar imagen Mosaico',exact:true}).waitFor();
  await delay(1600);assert.equal(await page.getByTestId('detections-count').innerText(),count);
  await s2.click();const link=await dialog.getByRole('link',{name:'Metadatos · JSON',exact:true}).getAttribute('href');
  const metadata=await (await page.request.get(base+link)).json();
  assert.equal(metadata.nominal_resolution_m,10);assert.equal(metadata.collection,'byoc-5460de54-082e-473a-b6ea-d5cbe3c17cca');assert.deepEqual(metadata.bands_rgb,['B04','B03','B02']);
  assert.equal(metadata.kind,'quarterly_mosaic');assert.equal(metadata.cloud_cover_catalog,null);assert.ok(Math.max(...metadata.dimensions)<=128);
  await dialog.getByRole('slider',{name:'Opacidad de imagen Mosaico',exact:true}).fill('60');await page.keyboard.press('Escape');
  await s3.click();const old=page.getByRole('dialog',{name:'Imagen Sentinel-3 OLCI',exact:true});await old.getByRole('button',{name:'Buscar última imagen',exact:true}).click();
  await old.waitFor({state:'hidden',timeout:60000});await page.getByRole('button',{name:'Ocultar imagen OLCI',exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Ocultar imagen Mosaico',exact:true}).count(),0,'Al activar S3 se oculta S2');
  await s2.click();await dialog.getByRole('checkbox',{name:'Mostrar imagen en el mapa',exact:true}).check();await page.keyboard.press('Escape');
  assert.equal(await page.getByRole('button',{name:'Ocultar imagen OLCI',exact:true}).count(),0,'Al reactivar S2 se oculta S3');
  await page.getByRole('button',{name:'Ocultar imagen Mosaico',exact:true}).waitFor();
  await page.screenshot({path:path.join(qa,'desktop.png'),fullPage:true});
  await s2.click();await dialog.getByRole('button',{name:'Elegir trimestre',exact:true}).click();
  const quarter=metadata.quarter,year=metadata.year;
  await dialog.getByLabel('Año del mosaico').selectOption(String(year));
  await dialog.getByLabel('Trimestre del mosaico').selectOption(String(quarter));
  await dialog.getByRole('button',{name:'Cargar trimestre',exact:true}).click();await dialog.waitFor({state:'hidden'});
  await page.getByRole('button',{name:'Ocultar imagen Mosaico',exact:true}).waitFor();
  await s2.click();await page.route('**/api/sentinel2/search',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'CDSE temporalmente no disponible'})}));
  await dialog.getByRole('button',{name:'Cargar trimestre',exact:true}).click();await dialog.getByRole('alert').filter({hasText:'CDSE temporalmente no disponible'}).waitFor();
  await page.keyboard.press('Escape');await page.getByRole('button',{name:'Ocultar imagen Mosaico',exact:true}).waitFor();
  await page.unroute('**/api/sentinel2/search');
  await page.getByRole('combobox',{name:'Unidad de análisis',exact:true}).selectOption('municipio');await delay(500);
  assert.equal(await page.getByRole('button',{name:/Ocultar imagen (Mosaico|OLCI)/}).count(),0);
  await page.setViewportSize({width:390,height:844});
  const box2=await s2.boundingBox(),box3=await s3.boundingBox();assert.ok(box2.x>=box3.x+box3.width,'Botones separados en móvil');
  for(const button of [s2,s3])assert.ok(await button.evaluate(b=>b.scrollWidth<=b.clientWidth),'El texto cabe dentro de cada botón');
  await s2.click();await dialog.getByRole('button',{name:'Elegir trimestre',exact:true}).click();
  await page.screenshot({path:path.join(qa,'mobile-dialog.png'),fullPage:true});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.keyboard.press('Escape');
  assert.deepEqual(errors,[]);console.log('Mosaicos UI OK: último publicado, trimestre, metadatos, opacidad, alternancia, fallo API, cambio territorial y móvil.');
 }catch(error){if(page)await page.screenshot({path:path.join(qa,'error.png'),fullPage:true});console.error(errors);throw error}
 finally{if(browser)await browser.close();const stopped=new Promise(r=>fixture.once('exit',r));fixture.kill('SIGTERM');if(fixture.exitCode===null)await stopped;fs.rmSync(temp,{recursive:true,force:true})}
})().catch(e=>{console.error(e);process.exitCode=1});
