// Fondo opcional: teselas simuladas, sin llamadas externas a Esri/CDSE.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const root=path.resolve(__dirname,'..'),cache=path.join(root,'.conda-env/.npm-cache/_npx');
const lib=fs.readdirSync(cache).map(n=>path.join(cache,n,'node_modules/playwright')).find(p=>fs.existsSync(path.join(p,'package.json'))&&JSON.parse(fs.readFileSync(path.join(p,'package.json'))).version==='1.58.2');
const {chromium}=require(lib),temp=fs.mkdtempSync(path.join(os.tmpdir(),'cemec-esri-')),ready=path.join(temp,'ready.json');
const fixture=spawn(path.join(root,'.conda-env/bin/python'),[path.join(__dirname,'ui_fixture.py'),'--ready-file',ready,'--sentinel2'],{stdio:['ignore','ignore','inherit']});
const delay=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 let browser,page;const errors=[],requests=[];const qa=path.join(root,'runtime/esri-qa');fs.mkdirSync(qa,{recursive:true});
 try{
  for(let i=0;i<300&&!fs.existsSync(ready);i++){if(fixture.exitCode!==null)throw Error('No inició la prueba');await delay(100)}
  const {port}=JSON.parse(fs.readFileSync(ready));browser=await chromium.launch({headless:true,channel:'chrome'});page=await browser.newPage({viewport:{width:1500,height:1100}});
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.url().includes('services.arcgisonline.com/'))requests.push(r.url())});
  const tile=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGMwjzL/DwADXAHIjMM8DQAAAABJRU5ErkJggg==','base64');
  const pattern='https://services.arcgisonline.com/**';
  await page.route(pattern,r=>r.fulfill({status:200,contentType:'image/png',headers:{'Cache-Control':'no-store'},body:tile}));
  await page.goto('http://127.0.0.1:'+port,{waitUntil:'networkidle'});assert.equal(requests.length,0,'Esri no se precarga');
  const count=await page.getByTestId('detections-count').innerText();
  await page.getByRole('button',{name:'Capas del mapa',exact:true}).click();
  const original=page.getByRole('radio',{name:'Mapa CEMEC',exact:true}),esri=page.getByRole('radio',{name:'Esri · Imagen satelital',exact:true});
  assert.equal(await original.isChecked(),true);await esri.check();await delay(1500);
  assert.ok(requests.length>0,'El fondo se solicita al seleccionarlo');assert.equal(await esri.isChecked(),true);
  assert.ok((await page.locator('.maplibregl-ctrl-attrib').allTextContents()).join('').includes('Esri, Vantor'));
  assert.equal(await page.getByTestId('detections-count').innerText(),count);
  await page.screenshot({path:path.join(qa,'desktop.png'),fullPage:true});
  await page.getByRole('button',{name:'Capas del mapa',exact:true}).click();await page.getByRole('button',{name:'Capas del mapa',exact:true}).click();assert.equal(await esri.isChecked(),true);
  await original.check();await delay(500);const stopped=requests.length;
  await page.getByRole('button',{name:'Acercar',exact:true}).first().click();await delay(800);assert.equal(requests.length,stopped,'Desactivar Esri detiene sus peticiones');
  await esri.check();await delay(500);
  await page.getByRole('button',{name:'Capas del mapa',exact:true}).click();
  await page.getByRole('button',{name:'Imagen Mosaico Sentinel-2',exact:true}).click();const dialog=page.getByRole('dialog',{name:'Imagen Mosaico Sentinel-2',exact:true});
  await dialog.getByRole('button',{name:'Cargar último mosaico',exact:true}).click();await dialog.waitFor({state:'hidden',timeout:60000});await page.getByRole('button',{name:'Ocultar imagen Mosaico',exact:true}).waitFor();
  await page.getByRole('button',{name:'Capas del mapa',exact:true}).click();assert.equal(await esri.isChecked(),true);await original.check();await esri.check();await delay(700);
  await page.screenshot({path:path.join(qa,'with-sentinel2.png'),fullPage:true});
  await page.getByRole('button',{name:'Ocultar imagen Mosaico',exact:true}).click();
  await page.setViewportSize({width:390,height:844});await delay(400);await page.screenshot({path:path.join(qa,'mobile.png'),fullPage:true});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert.ok(await page.locator('.layer-popover').evaluate(panel=>{const p=panel.getBoundingClientRect(),m=panel.closest('.map-shell').getBoundingClientRect();return p.top>=m.top&&p.bottom<=m.bottom;}),'El panel cabe dentro del mapa móvil');
  await original.check();await page.unroute(pattern);await page.route(pattern,r=>r.fulfill({status:503,body:'Unavailable'}));await esri.check();
  await page.getByRole('alert').filter({hasText:'No se pudo cargar Esri'}).waitFor();assert.equal(await original.isChecked(),true,'Fallo conserva el mapa local');
  await page.screenshot({path:path.join(qa,'fallback.png'),fullPage:true});assert.deepEqual(errors,[]);
  console.log('Esri UI OK: carga optativa, atribución, capas térmicas intactas, desactivación, Sentinel-2, móvil y retorno local ante fallo.');
 }catch(e){if(page)await page.screenshot({path:path.join(qa,'error.png'),fullPage:true});console.error(errors);throw e}
 finally{if(browser)await browser.close();const done=new Promise(r=>fixture.once('exit',r));fixture.kill('SIGTERM');if(fixture.exitCode===null)await done;fs.rmSync(temp,{recursive:true,force:true})}
})().catch(e=>{console.error(e);process.exitCode=1});
