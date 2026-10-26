// QA opcional con Playwright 1.58.2, alojado en la caché del entorno del proyecto.
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const {spawn} = require('node:child_process');
const assert = require('node:assert/strict');
const project = path.resolve(__dirname, '..');
const cache = path.join(project, '.conda-env/.npm-cache/_npx');
const candidates = fs.readdirSync(cache).map(dir => path.join(cache, dir, 'node_modules/playwright'));
const modulePath = candidates.find(dir => fs.existsSync(path.join(dir, 'package.json')) && JSON.parse(fs.readFileSync(path.join(dir, 'package.json'))).version === '1.58.2');
if (!modulePath) throw Error('Instala Playwright 1.58.2 según README.md');
const {chromium} = require(modulePath);
const temp = fs.mkdtempSync(path.join(os.tmpdir(),'cemec-browser-'));
const ready = path.join(temp,'ready.json');
const fixture = spawn(path.join(project,'.conda-env/bin/python'),[path.join(__dirname,'ui_fixture.py'),'--ready-file',ready], {stdio:['ignore','ignore','inherit']});
const delay = ms => new Promise(resolve => setTimeout(resolve,ms));
(async () => {
  let browser, page;
  const errors=[];
  try {
    for (let i=0;i<300 && !fs.existsSync(ready);i++) {
      if (fixture.exitCode !== null) throw Error('El servidor de prueba no inició');
      await delay(100);
    }
    const {port} = JSON.parse(fs.readFileSync(ready));
    browser = await chromium.launch({channel:'chrome',headless:true});
    page = await browser.newPage({viewport:{width:1600,height:1000}});
    page.on('pageerror',error=>errors.push(error.message));
    await page.goto(`http://127.0.0.1:${port}`,{waitUntil:'networkidle'});
    await page.locator('.cemec-page-heading h1').waitFor();
    await page.getByText('Administración',{exact:true}).click();
    await page.getByText('Ajustes',{exact:true}).click();
    const sync=page.getByRole('button',{name:'Sincronizar ahora',exact:true});
    await sync.waitFor();
    await page.getByRole('combobox',{name:'Periodo FIRMS',exact:true}).selectOption('30');
    assert.equal(await sync.isEnabled(),true,'La clave configurada habilita el botón');
    await sync.click();
    console.log('UI: sincronización iniciada');
    await page.getByText(/Última sincronización:/).waitFor({timeout:120000});
    const catalog = await (await page.request.get(`http://127.0.0.1:${port}/data/catalog.json`)).json();
    assert.equal(catalog.total_points,66600,'Tres productos VIIRS por seis bloques incorporan dieciocho detecciones');
    const status = await (await page.request.get(`http://127.0.0.1:${port}/api/status`)).json();
    assert.equal(catalog.date_max,status.last_sync.downloads.at(-1).start,'La fecha máxima representa observaciones, no el fin de la ventana consultada');
    assert.equal(status.last_sync.added,18);
    assert.equal(status.last_sync.downloads.length,18);
    assert.equal((Date.parse(status.last_sync.end)-Date.parse(status.last_sync.start))/86400000,29);
    assert.ok(status.last_sync.downloads.every(block=>block.days<=5));
    assert.equal(status.jobs[0].status,'completed');
    const close=page.getByRole('button',{name:/Cerrar/});
    if (await close.count()) await close.first().click();
    await page.getByRole('button',{name:'Explorar',exact:true}).click();
    assert.equal(await page.getByLabel('Fecha inicial',{exact:true}).inputValue(),status.last_sync.start);
    assert.equal(await page.getByLabel('Fecha final',{exact:true}).inputValue(),status.last_sync.end);
    await page.getByRole('tab',{name:'Registros',exact:true}).click();
    await page.locator('.table-view').getByText(/NASA FIRMS/).first().waitFor({timeout:30000});
    // Comprueba descarga de CSV con las detecciones sincronizadas desde la UI.
    await page.getByRole('tab',{name:'Registros',exact:true}).click();
    await delay(1000);
    const downloaded = page.waitForEvent('download');
    await page.getByRole('button',{name:'CSV',exact:true}).click();
    const csv = await downloaded;
    const csvPath = path.join(temp,'detecciones.csv');
    await csv.saveAs(csvPath);
    assert.match(fs.readFileSync(csvPath,'utf8'),/NASA FIRMS/,'El CSV exportado incluye las detecciones nuevas');
    fs.mkdirSync(path.join(project,'runtime'),{recursive:true});
    await page.screenshot({path:path.join(project,'runtime/firms-sync-qa.png')});
    assert.deepEqual(errors,[],'No hay errores JavaScript durante sincronización y análisis');
    console.log('QA UI OK: 30 días, 18 bloques de tres productos, fechas actualizadas y CSV. Solo datos temporales simulados.');
  } catch(error) {
    if (page) {
      fs.mkdirSync(path.join(project,'runtime'),{recursive:true});
      await page.screenshot({path:path.join(project,'runtime/firms-sync-qa-error.png')});
      console.error('Errores del navegador:',errors);
      console.error('Mensajes visibles:',await page.getByRole('alert').allTextContents());
      console.error('Panel:',(await page.locator('body').innerText()).slice(-3000));
    }
    throw error;
  } finally {
    if (browser) await browser.close();
    const stopped = new Promise(resolve=>fixture.once('exit',resolve));
    fixture.kill('SIGTERM');
    if (fixture.exitCode===null) await stopped;
    fs.rmSync(temp,{recursive:true,force:true});
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
