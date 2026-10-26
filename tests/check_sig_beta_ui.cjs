// Verifica el puente local y los enlaces externos sin publicar ni transferir datos.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {spawn}=require('node:child_process'),assert=require('node:assert/strict');
const project=path.resolve(__dirname,'..'),cache=path.join(project,'.conda-env/.npm-cache/_npx');
const modulePath=fs.readdirSync(cache).map(n=>path.join(cache,n,'node_modules/playwright')).find(p=>fs.existsSync(path.join(p,'package.json'))&&JSON.parse(fs.readFileSync(path.join(p,'package.json'))).version==='1.58.2');
const {chromium}=require(modulePath),temp=fs.mkdtempSync(path.join(os.tmpdir(),'cemec-sig-')),ready=path.join(temp,'ready.json');
const fixture=spawn(path.join(project,'.conda-env/bin/python'),[path.join(__dirname,'ui_fixture.py'),'--ready-file',ready],{stdio:['ignore','ignore','inherit']});
const delay=ms=>new Promise(r=>setTimeout(r,ms)),qa=path.join(project,'runtime/sig-beta-qa');fs.mkdirSync(qa,{recursive:true});
(async()=>{let browser;try{
 for(let i=0;i<300&&!fs.existsSync(ready);i++){if(fixture.exitCode!==null)throw Error('No inició QA');await delay(100);}
 const {port}=JSON.parse(fs.readFileSync(ready)),base='http://127.0.0.1:'+port;
 browser=await chromium.launch({channel:'chrome',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base,{waitUntil:'networkidle'});
 await page.getByRole('button',{name:'Datos',exact:true}).click();
 const entry=page.getByRole('link',{name:'Abrir catálogo SIG · beta ↗',exact:true});assert.equal(await entry.getAttribute('href'),'/sig-beta/');
 await page.goto(base+'/sig-beta/',{waitUntil:'networkidle'});
 assert.equal(await page.locator('.layer').count(),3);assert.match(await page.locator('#connection-status').innerText(),/Modo local/);
 assert.equal(await page.locator('#open-gis').getAttribute('href'),'https://web.geolibre.app/');
 const pending=page.waitForEvent('download');await page.getByRole('link',{name:'Descargar Detecciones VIIRS · marzo de 2026 · GeoJSON',exact:true}).click();
 const download=await pending;await download.saveAs(path.join(qa,download.suggestedFilename()));
 const fc=JSON.parse(fs.readFileSync(path.join(qa,download.suggestedFilename())));assert.equal(fc.features.length,986);
 await page.screenshot({path:path.join(qa,'desktop.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(qa,'mobile.png'),fullPage:true});
 await page.route('**/sig-beta/config.json',r=>r.fulfill({json:{public_base_url:'https://datos.example.org/prueba/'}}));
 await page.reload({waitUntil:'networkidle'});
 const url=new URL(await page.locator('#open-gis').getAttribute('href'));assert.equal(url.origin,'https://web.geolibre.app');
 assert.deepEqual(url.searchParams.getAll('data'),['municipios.geojson','areas-protegidas.geojson','viirs-marzo-2026.geojson'].map(n=>'https://datos.example.org/prueba/data/'+n));
 await page.route('**/sig-beta/config.json',r=>r.fulfill({status:503,body:'Unavailable'}));await page.reload({waitUntil:'networkidle'});assert.match(await page.locator('#connection-status').innerText(),/manualmente/);
 await page.route('**/sig-beta/data/manifest.json',r=>r.fulfill({status:503,body:'Unavailable'}));await page.reload({waitUntil:'networkidle'});assert.ok(await page.getByRole('alert').isVisible());
 assert.deepEqual(errors,[]);fs.writeFileSync(path.join(qa,'result.json'),JSON.stringify({ok:true,layers:3,viirs:986,external_data_transferred:false,checks:['entry','local','download','mobile','public-link-mocked','config-failure','manifest-failure']},null,2));
 console.log('SIG beta UI OK: catálogo, descarga, móvil, enlaces y fallos. No se abrió el SIG externo.');
}finally{await browser?.close();fixture.kill('SIGTERM');await delay(500);fs.rmSync(temp,{recursive:true,force:true});}})().catch(e=>{console.error(e);process.exitCode=1;});
