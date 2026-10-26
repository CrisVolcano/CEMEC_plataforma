// QA con respuestas simuladas y almacenamiento temporal; no publica en el visor real.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {spawn}=require('node:child_process');
const assert=require('node:assert/strict');
const project=path.resolve(__dirname,'..');
const cache=path.join(project,'.conda-env/.npm-cache/_npx');
const modulePath=fs.readdirSync(cache).map(dir=>path.join(cache,dir,'node_modules/playwright')).find(dir=>fs.existsSync(path.join(dir,'package.json'))&&JSON.parse(fs.readFileSync(path.join(dir,'package.json'))).version==='1.58.2');
const {chromium}=require(modulePath);
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'cemec-eumetsat-ui-'));
const ready=path.join(temp,'ready.json');
const empty=process.argv.includes('--empty');
const fixture=spawn(path.join(project,'.conda-env/bin/python'),[path.join(__dirname,'ui_fixture.py'),'--ready-file',ready,'--eumetsat',...(empty?['--eumetsat-empty']:[])],{stdio:['ignore','ignore','inherit']});
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
(async()=>{
 let browser,page; const errors=[];
 try {
  for(let i=0;i<300&&!fs.existsSync(ready);i++){
   if(fixture.exitCode!==null)throw Error('El servidor QA no inició');
   await delay(100);
  }
  const {port}=JSON.parse(fs.readFileSync(ready));
  browser=await chromium.launch({channel:'chrome',headless:true});
  page=await browser.newPage({viewport:{width:1600,height:1000}});
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto(`http://127.0.0.1:${port}`,{waitUntil:'networkidle'});
  await page.locator('.cemec-page-heading h1').waitFor();
  await page.getByText('Administración',{exact:true}).click();
    await page.getByText('Ajustes',{exact:true}).click();
  const sync=page.getByRole('button',{name:'Sincronizar Sentinel-3',exact:true});
  assert.equal(await sync.isEnabled(),true);
  await sync.click();
  await page.getByText(/Última sincronización Sentinel-3:/).waitFor({timeout:120000});
  const status=await (await page.request.get(`http://127.0.0.1:${port}/api/status`)).json();
  assert.equal(status.last_eumetsat_sync.products_processed,17);
  assert.equal(status.last_eumetsat_sync.added,empty?0:17);
  const catalog=await (await page.request.get(`http://127.0.0.1:${port}/data/catalog.json`)).json();
  assert.equal(catalog.total_points,empty?66582:66599);
  if(empty){
   await page.getByRole('button',{name:'Cerrar panel',exact:true}).click();
   const dates=await page.locator('input[type="date"]').evaluateAll(inputs=>inputs.map(input=>input.value));
   assert.equal(dates[1],status.last_eumetsat_sync.end.slice(0,10));
   assert.ok(dates[0]<=dates[1],'El rango de consulta sigue siendo válido cuando el catálogo no añade observaciones');
   assert.deepEqual(errors,[]);
   console.log('QA Sentinel-3 sin detecciones: descarga completa, histórico conservado y fechas válidas aunque el último dato publicado sea anterior.');
   return;
  }
  assert.ok(catalog.satellites.includes('Sentinel-3A'));
  assert.ok(catalog.satellites.includes('Sentinel-3B'));
  await page.screenshot({path:path.join(project,'runtime/eumetsat-sync-qa.png')});
  await page.getByRole('button',{name:'Cerrar panel',exact:true}).click();
  await page.getByRole('button',{name:'Explorar',exact:true}).click();
  await page.getByTestId('detections-count').filter({hasText:/^17$/}).waitFor({timeout:30000});
  await delay(1500); // Esperar al dibujo del mapa tras actualizar su GeoJSON.
  await page.screenshot({path:path.join(project,'runtime/eumetsat-map-qa.png')});
  await page.getByRole('button',{name:/Más filtros/}).click();
  assert.equal(await page.getByRole('combobox',{name:'Instrumento'}).inputValue(),'SLSTR');
  await page.getByRole('button',{name:'Ver resultados',exact:true}).click();
  await page.getByRole('tab',{name:'Registros',exact:true}).click();
  const downloaded=page.waitForEvent('download');
  await page.getByRole('button',{name:'CSV',exact:true}).click();
  const csvFile=path.join(temp,'detecciones.csv');
  await (await downloaded).saveAs(csvFile);
  const text=fs.readFileSync(csvFile,'utf8');
  assert.match(text,/EUMETSAT/);assert.match(text,/observation_utc/);assert.match(text,/confidence_scheme/);
  // La fuente histórico/archivos excluye Sentinel-3.
  await page.getByRole('button',{name:/Más filtros/}).click();
  const source=page.getByRole('combobox',{name:'Origen',exact:true});
  await source.selectOption('static');
  await page.getByRole('button',{name:'Ver resultados',exact:true}).click();
  await page.getByText('Sin detecciones en esta selección',{exact:true}).waitFor();
  await page.getByRole('button',{name:/Más filtros/}).click();
  await source.selectOption('eumetsat');
  await page.getByRole('button',{name:'Ver resultados',exact:true}).click();
  await page.getByText(/17 observaciones · coordenadas/).waitFor();
  await page.screenshot({path:path.join(project,'runtime/eumetsat-registros-qa.png')});
  assert.deepEqual(errors,[]);
  console.log('QA Sentinel-3 OK: 17 productos, INAB conservado, filtros por SLSTR/origen y CSV con hora UTC/calidad original. Datos de prueba aislados.');
 }catch(error){
  if(page){await page.screenshot({path:path.join(project,'runtime/eumetsat-qa-error.png')});console.error('Errores JS:',errors);console.error((await page.locator('body').innerText()).slice(-2000));}
  throw error;
 }finally{
  if(browser)await browser.close();
  const stopped=new Promise(resolve=>fixture.once('exit',resolve));fixture.kill('SIGTERM');if(fixture.exitCode===null)await stopped;
  fs.rmSync(temp,{recursive:true,force:true});
 }
})().catch(error=>{console.error(error.message);process.exitCode=1;});
