// Detalle bajo demanda con CDSE simulado y almacenamiento temporal.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const root=path.resolve(__dirname,'..'),cache=path.join(root,'.conda-env/.npm-cache/_npx');
const lib=fs.readdirSync(cache).map(n=>path.join(cache,n,'node_modules/playwright')).find(p=>fs.existsSync(path.join(p,'package.json'))&&JSON.parse(fs.readFileSync(path.join(p,'package.json'))).version==='1.58.2');
const {chromium}=require(lib),temp=fs.mkdtempSync(path.join(os.tmpdir(),'cemec-detail-')),ready=path.join(temp,'ready.json');
const fixture=spawn(path.join(root,'.conda-env/bin/python'),[path.join(__dirname,'ui_fixture.py'),'--ready-file',ready,'--sentinel2'],{stdio:['ignore','ignore','inherit']});
const delay=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 let browser,page;const errors=[],posts=[],details=[];const qa=path.join(root,'runtime/detail-qa');fs.mkdirSync(qa,{recursive:true});
 try{
  for(let i=0;i<300&&!fs.existsSync(ready);i++){if(fixture.exitCode!==null)throw Error('No inició la prueba');await delay(100)}
  const {port}=JSON.parse(fs.readFileSync(ready));browser=await chromium.launch({headless:true,channel:'chrome'});
  page=await browser.newPage({viewport:{width:1500,height:1100}});
  page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&m.text().startsWith('Error:'))errors.push(m.text())});
  page.on('request',r=>{if(r.method()==='POST'&&r.url().includes('/api/sentinel2/'))posts.push(r.url())});
  page.on('response',async r=>{if(r.url().includes('/api/sentinel2/jobs/')&&r.status()===200){try{const d=await r.json();if(d.status==='completed'&&d.result?.kind==='quarterly_mosaic_detail')details.push(d.result)}catch{}}});
  await page.goto('http://127.0.0.1:'+port,{waitUntil:'networkidle'});
  const count=await page.getByTestId('detections-count').innerText();
  await page.getByRole('button',{name:'Imagen Mosaico Sentinel-2',exact:true}).click();
  const dialog=page.getByRole('dialog',{name:'Imagen Mosaico Sentinel-2',exact:true});
  await dialog.getByRole('button',{name:'Cargar último mosaico',exact:true}).click();await dialog.waitFor({state:'hidden',timeout:60000});
  const detail=page.getByRole('button',{name:'Cargar detalle de esta zona',exact:true});await detail.waitFor();
  assert.equal(await detail.isEnabled(),false,'El recorte regional requiere acercarse');
  const before=posts.length;
  for(let n=0;n<9&&!(await detail.isEnabled());n++){await page.getByRole('button',{name:'Acercar',exact:true}).first().click();await delay(500)}
  assert.equal(posts.length,before,'El zoom no hace solicitudes');assert.equal(await detail.isEnabled(),true);
  await detail.click();await page.getByText('Detalle solicitado',{exact:false}).waitFor({timeout:60000});await delay(1200);
  assert.ok(details.length);const first=details.at(-1);assert.equal(first.coverage_scope,'visible_crop');assert.ok(first.area_km2<=400);
  assert.equal(await page.getByTestId('detections-count').innerText(),count);
  await page.screenshot({path:path.join(qa,'desktop.png'),fullPage:true});
  const after=posts.length;await page.getByRole('button',{name:'Vista general',exact:true}).click();await delay(300);assert.equal(posts.length,after);
  await detail.click();await page.getByText('Detalle solicitado',{exact:false}).waitFor();await delay(500);
  assert.equal(details.at(-1).cached,true);assert.equal(details.at(-1).url,first.url,'El mismo recorte se reutiliza');
  await page.getByRole('button',{name:'Acercar',exact:true}).first().click();await delay(500);
  // Un zoom puede quedar cubierto por el detalle existente a su resolución
  // nativa. Desplazar la vista solicita otra zona, sin forzar nuevas descargas.
  if(!(await detail.isEnabled())){
    const box=await page.locator('.map-canvas').first().boundingBox();
    await page.mouse.move(box.x+box.width*.8,box.y+box.height*.55);await page.mouse.down();
    await page.mouse.move(box.x+box.width*.2,box.y+box.height*.55,{steps:20});await page.mouse.up();await delay(900);
  }
  assert.ok(await detail.isEnabled(),'Una zona fuera del detalle guardado permite otra solicitud');
  await page.route('**/api/sentinel2/detail',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Detalle temporalmente no disponible'})}));
  await detail.click();await page.getByRole('alert').filter({hasText:'Detalle temporalmente no disponible'}).waitFor();
  await page.getByRole('button',{name:'Vista general',exact:true}).waitFor();await page.unroute('**/api/sentinel2/detail');
  await page.setViewportSize({width:390,height:844});await delay(500);
  await page.screenshot({path:path.join(qa,'mobile.png'),fullPage:true});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.locator('.cemec-controls>summary').click();
  await page.getByRole('combobox',{name:'Unidad de análisis',exact:true}).selectOption('municipio');await delay(500);
  assert.equal(await detail.count(),0,'Cambiar unidad retira el detalle anterior');assert.deepEqual(errors,[]);
  console.log('Detalle UI OK: zoom sin POST, carga manual, límites, caché, retorno general, error conservando imagen, móvil y cambio de territorio.');
 }catch(e){if(page)await page.screenshot({path:path.join(qa,'error.png'),fullPage:true});console.error(errors);throw e}
 finally{if(browser)await browser.close();const done=new Promise(r=>fixture.once('exit',r));fixture.kill('SIGTERM');if(fixture.exitCode===null)await done;fs.rmSync(temp,{recursive:true,force:true})}
})().catch(e=>{console.error(e);process.exitCode=1});
