// UI con CDSE simulado y caché temporal; no consulta servicios externos.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const {spawn}=require('node:child_process');
const root=path.resolve(__dirname,'..'),cache=path.join(root,'.conda-env/.npm-cache/_npx');
const library=fs.readdirSync(cache).map(n=>path.join(cache,n,'node_modules/playwright')).find(p=>fs.existsSync(path.join(p,'package.json'))&&JSON.parse(fs.readFileSync(path.join(p,'package.json'))).version==='1.58.2');
const {chromium}=require(library),temp=fs.mkdtempSync(path.join(os.tmpdir(),'cemec-olci-qa-')),ready=path.join(temp,'ready.json');
const fixture=spawn(path.join(root,'.conda-env/bin/python'),[path.join(__dirname,'ui_fixture.py'),'--ready-file',ready,'--olci'],{stdio:['ignore','ignore','inherit']});
const wait=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 let browser,page;const errors=[],images=[];
 const qa=path.join(root,'runtime/olci-qa');fs.mkdirSync(qa,{recursive:true});
 try{
  for(let n=0;n<300&&!fs.existsSync(ready);n++){if(fixture.exitCode!==null)throw Error('No inició el servidor QA');await wait(100)}
  const {port}=JSON.parse(fs.readFileSync(ready));browser=await chromium.launch({headless:true,channel:'chrome'});
  page=await browser.newPage({viewport:{width:1500,height:1100}});page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error')console.error('Browser:',m.text())});
  page.on('response',r=>{if(/\/api\/olci\/images\/.*\.png$/.test(r.url()))images.push(r.status())});
  await page.goto('http://127.0.0.1:'+port,{waitUntil:'networkidle'});
  const count=await page.getByTestId('detections-count').innerText();
  await page.getByRole('button',{name:'Imagen Sentinel-3 OLCI',exact:true}).click();
  const dialog=page.getByRole('dialog',{name:'Imagen Sentinel-3 OLCI'});
  await dialog.getByRole('button',{name:'Buscar última imagen',exact:true}).click();
  await page.getByRole('button',{name:'Ocultar imagen OLCI'}).waitFor({timeout:60000});
  await wait(1600);assert.ok(images.includes(200),'El mapa cargó el raster desde la API');
  assert.equal(await page.getByTestId('detections-count').innerText(),count,'La imagen no modifica el conteo térmico');
  await page.screenshot({path:path.join(qa,'desktop.png'),fullPage:true});
  await page.getByRole('button',{name:'Imagen Sentinel-3 OLCI',exact:true}).click();
  await dialog.getByRole('slider',{name:'Opacidad de imagen OLCI'}).fill('35');
  await dialog.getByRole('button',{name:'Volver al mapa',exact:true}).click();
  await page.getByRole('button',{name:'Imagen Sentinel-3 OLCI',exact:true}).filter({hasText:'35 %'}).waitFor();
  await page.getByRole('button',{name:'Imagen Sentinel-3 OLCI',exact:true}).click();
  await dialog.getByRole('button',{name:'Elegir período',exact:true}).click();
  await dialog.getByLabel('Imagen Desde · UTC').fill('2024-01-01');await dialog.getByLabel('Imagen Hasta · UTC').fill('2024-01-02');
  await dialog.getByRole('button',{name:'Buscar imágenes',exact:true}).click();
  await dialog.getByText('No hay imágenes para esta zona y período. Prueba otras fechas.',{exact:true}).waitFor();
  const today=new Date().toISOString().slice(0,10),from=new Date(Date.now()-3*86400000).toISOString().slice(0,10);
  await dialog.getByLabel('Imagen Desde · UTC').fill(from);await dialog.getByLabel('Imagen Hasta · UTC').fill(today);
  await dialog.getByRole('button',{name:'Buscar imágenes',exact:true}).click();
  await dialog.getByRole('combobox',{name:'Pasada OLCI disponible'}).waitFor();
  await dialog.getByRole('button',{name:'Mostrar esta imagen',exact:true}).click();
  await dialog.waitFor({state:'hidden'});
  await page.getByRole('button',{name:'Ocultar imagen OLCI'}).waitFor();
  await page.getByRole('combobox',{name:'Unidad de análisis',exact:true}).selectOption('municipio');
  await wait(500);assert.equal(await page.getByRole('button',{name:'Ocultar imagen OLCI'}).count(),0,'Cambiar territorio retira la imagen anterior');
  await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Imagen Sentinel-3 OLCI',exact:true}).click();
  await page.screenshot({path:path.join(qa,'mobile-dialog.png'),fullPage:true});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.keyboard.press('Escape');assert.equal(await dialog.isVisible(),false);
  assert.deepEqual(errors,[]);console.log('OLCI UI OK: última, período, vacío, caché, raster, opacidad, cambio de unidad, móvil y Escape. Sin alterar detecciones.');
 }catch(error){if(page)await page.screenshot({path:path.join(qa,'error.png'),fullPage:true});console.error(errors);throw error}
 finally{
  if(browser)await browser.close();const stopped=new Promise(r=>fixture.once('exit',r));fixture.kill('SIGTERM');if(fixture.exitCode===null)await stopped;fs.rmSync(temp,{recursive:true,force:true});
 }
})().catch(e=>{console.error(e);process.exitCode=1});
