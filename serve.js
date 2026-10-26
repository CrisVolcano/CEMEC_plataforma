// Servidor local para la compilación original. Solo módulos nativos de Node.js.
'use strict';
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const patchFrontend = require('./scripts/frontend_patch.cjs');
const patchReport = require('./scripts/report_patch.cjs');
const modernUi = process.env.CEMEC_LEGACY_UI !== '1';

const args = process.argv.slice(2);
const option = (name, fallback) => {
  const idx = args.indexOf(name);
  if (idx < 0) return fallback;
  if (!args[idx + 1]) throw new Error(`Falta valor para ${name}`);
  return args[idx + 1];
};
const root = fs.realpathSync(option('--root', path.join(__dirname, 'cemec-sitio-estatico')));
const host = option('--host', process.env.HOST || '127.0.0.1');
const backendPort = Number(process.env.CEMEC_BACKEND_PORT || 0);
function proxy(req, res) {
  const origin = req.headers.origin;
  if (req.method === 'POST' && origin && origin !== `http://${req.headers.host}`) {
    return json(res, 403, {detail: 'La operación debe iniciarse desde la plataforma CEMEC.'});
  }
  const headers = {...req.headers, 'x-cemec-token': process.env.CEMEC_INTERNAL_TOKEN};
  delete headers['transfer-encoding'];
  const upstream = http.request({host: '127.0.0.1', port: backendPort, path: req.url, method: req.method, headers}, response => {
    res.writeHead(response.statusCode, response.headers);
    response.pipe(res);
  });
  upstream.on('error', () => {
    if (!res.headersSent) json(res, 503, {detail: 'El servicio de datos CEMEC no está disponible.'});
    else res.destroy();
  });
  upstream.setTimeout(90000, () => upstream.destroy());
  req.pipe(upstream);
}
const port = Number(option('--port', process.env.PORT || '8000'));
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('Puerto inválido');
const mime = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8',
  '.geojson': 'application/geo+json', '.png': 'image/png', '.svg': 'image/svg+xml',
  '.pdf': 'application/pdf', '.csv': 'text/csv; charset=utf-8',
  '.pmtiles': 'application/octet-stream', '.parquet': 'application/octet-stream',
  '.fgb': 'application/octet-stream', '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
};
function json(res, status, value) {
  res.writeHead(status, {'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store'});
  res.end(JSON.stringify(value));
}
// Soporte de un rango (incluidos rangos abiertos y sufijos). Rangos múltiples
// se ignoran y producen 200; PMTiles usa solicitudes de un solo rango.
function parseRange(header, size) {
  if (!header || !header.startsWith('bytes=') || header.includes(',')) return null;
  const match = /^bytes=(\d*)-(\d*)$/.exec(header);
  if (!match || (!match[1] && !match[2])) return null;
  let start, end;
  if (!match[1]) {
    const suffix = Number(match[2]);
    if (!Number.isSafeInteger(suffix) || suffix <= 0 || size === 0) return false;
    start = Math.max(0, size - suffix); end = size - 1;
  } else {
    start = Number(match[1]); end = match[2] ? Number(match[2]) : size - 1;
    if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start >= size || end < start) return false;
    end = Math.min(end, size - 1);
  }
  return {start, end};
}
const server = http.createServer(async (req, res) => {
  try {
    let pathname;
    try { pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname); }
    catch { return json(res, 400, {detail: 'Ruta inválida'}); }
    if (pathname.includes('\0')) return json(res, 400, {detail: 'Ruta inválida'});
    if (pathname === '/sig-beta' || pathname.startsWith('/sig-beta/')) {
      if (!['GET', 'HEAD', 'OPTIONS'].includes(req.method)) {
        res.setHeader('Allow', 'GET, HEAD, OPTIONS');
        return json(res, 405, {detail: 'Catálogo de solo lectura'});
      }
      if (pathname === '/sig-beta') {
        res.writeHead(308, {Location: '/sig-beta/'}); return res.end();
      }
      const relative = pathname.slice('/sig-beta/'.length) || 'index.html';
      const allowed = new Set(['index.html', 'portal.css', 'portal.js', 'config.json',
        'data/manifest.json', 'data/municipios.geojson', 'data/areas-protegidas.geojson', 'data/viirs-marzo-2026.geojson']);
      if (!allowed.has(relative)) return json(res, 404, {detail: 'Recurso no encontrado'});
      const isData = relative.startsWith('data/');
      const headers = {'Cache-Control': 'no-cache', 'X-Content-Type-Options': 'nosniff'};
      if (isData) Object.assign(headers, {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS'});
      if (req.method === 'OPTIONS') { res.writeHead(204, headers); return res.end(); }
      let data;
      if (relative === 'config.json') {
        // Publicar una URL no publica archivos ni inicia túneles. Solo configura
        // referencias a las copias que el administrador haya alojado y revisado.
        let base = process.env.CEMEC_SIG_PUBLIC_BASE_URL || '';
        if (base) {
          try {
            const u = new URL(base);
            if (u.protocol !== 'https:' || u.username || u.password || u.search || u.hash ||
                u.hostname === 'localhost' || u.hostname.endsWith('.localhost') || u.hostname.endsWith('.local') ||
                /^[\d.]+$/.test(u.hostname) || u.hostname.includes(':')) throw Error();
            base = u.href.replace(/\/?$/, '/');
          } catch { return json(res, 500, {detail: 'CEMEC_SIG_PUBLIC_BASE_URL debe ser una URL HTTPS pública sin credenciales ni parámetros'}); }
        }
        data = Buffer.from(JSON.stringify({public_base_url: base}));
      } else {
        data = await fs.promises.readFile(path.join(__dirname, 'ui/sig-beta', relative));
      }
      res.writeHead(200, {...headers, 'Content-Type': mime[path.extname(relative)] || 'application/octet-stream', 'Content-Length': data.length});
      return res.end(req.method === 'HEAD' ? undefined : data);
    }
    if (backendPort && (pathname.startsWith('/api/') || pathname.startsWith('/live-data/') || pathname === '/data/catalog.json')) {
      return proxy(req, res);
    }
    if (pathname.startsWith('/api/')) {
      // 404 conserva el modo estático previsto por el frontend: status -> null.
      return json(res, 404, {detail: 'El ZIP estático no incluye el backend de sincronización/importación.'});
    }
    if (pathname === '/cemec-ui.css' && ['GET','HEAD'].includes(req.method)) {
      const css = await fs.promises.readFile(path.join(__dirname, 'ui/cemec-ui.css'));
      res.writeHead(200, {'Content-Type':'text/css; charset=utf-8','Cache-Control':'no-cache','Content-Length':css.length});
      return res.end(req.method === 'HEAD' ? undefined : css);
    }
    if (pathname.startsWith('/cemec-vendor/') && ['GET','HEAD'].includes(req.method)) {
      const relative=pathname.slice('/cemec-vendor/'.length);
      const allowed=new Set(['maplibre-gl-export-6.0.0/maplibre-gl-export.umd.js','maplibre-gl-export-6.0.0/maplibre-gl-export.css','barlow/Barlow-Regular.ttf','barlow/Barlow-SemiBold.ttf']);
      if(!allowed.has(relative))return json(res,404,{detail:'Recurso no encontrado'});
      const data=await fs.promises.readFile(path.join(__dirname,'ui/vendor',relative));
      res.writeHead(200,{'Content-Type':mime[path.extname(relative)],'Content-Length':data.length,'Cache-Control':'no-cache','X-Content-Type-Options':'nosniff'});
      return res.end(req.method==='HEAD'?undefined:data);
    }
    if (!['GET', 'HEAD'].includes(req.method)) {
      res.setHeader('Allow', 'GET, HEAD'); return json(res, 405, {detail: 'Método no permitido'});
    }
    const target = path.resolve(root, '.' + (pathname === '/' ? '/index.html' : pathname));
    if (!target.startsWith(root + path.sep)) return json(res, 403, {detail: 'Ruta fuera del sitio'});
    let real, stat;
    try { real = await fs.promises.realpath(target); stat = await fs.promises.stat(real); }
    catch (err) {
      if (['ENOENT', 'ENOTDIR'].includes(err.code)) return json(res, 404, {detail: 'Archivo no encontrado'});
      throw err;
    }
    if (!real.startsWith(root + path.sep)) return json(res, 403, {detail: 'Ruta fuera del sitio'});
    if (!stat.isFile()) return json(res, 404, {detail: 'Archivo no encontrado'});
    let patched = null;
    if (modernUi && path.extname(real) === '.html' && pathname === '/') {
      const html = await fs.promises.readFile(real, 'utf8');
      patched = Buffer.from(html.replace('</head>','<link rel="stylesheet" href="/cemec-ui.css"></head>'));
      stat.size = patched.length;
    }
    if ((backendPort || modernUi) && path.extname(real) === '.js') {
      const script = await fs.promises.readFile(real, 'utf8');
      // El visor original delega todas las importaciones cuando detecta un backend.
      // Anuncia solo los formatos implementados; ZIP conserva su importador local.
      if (script.includes('if(V&&_t.includes(Ft||""))')) {
        patched = Buffer.from(patchFrontend(script));
        stat.size = patched.length;
      } else if (modernUi && script.includes('r.includeTable&&l.length&&(t.addPage()')) {
        patched = Buffer.from(patchReport(script));
        stat.size = patched.length;
      }
    }
    const headers = {
      'Content-Type': mime[path.extname(real)] || 'application/octet-stream',
      'Accept-Ranges': 'bytes', 'Last-Modified': stat.mtime.toUTCString(),
      'X-Content-Type-Options': 'nosniff',
      'Cache-Control': pathname.startsWith('/data/v-') ? 'public, max-age=31536000, immutable' : 'no-cache',
    };
    const ifRangeMatches = !req.headers['if-range'] || req.headers['if-range'] === headers['Last-Modified'];
    const range = req.method === 'GET' && ifRangeMatches ? parseRange(req.headers.range, stat.size) : null;
    if (range === false) {
      res.writeHead(416, {...headers, 'Content-Range': `bytes */${stat.size}`, 'Content-Length': 0}); return res.end();
    }
    if (range) headers['Content-Range'] = `bytes ${range.start}-${range.end}/${stat.size}`;
    headers['Content-Length'] = range ? range.end - range.start + 1 : stat.size;
    res.writeHead(range ? 206 : 200, headers);
    if (req.method === 'HEAD' || stat.size === 0) return res.end();
    if (patched) return res.end(range ? patched.subarray(range.start, range.end + 1) : patched);
    const stream = fs.createReadStream(real, range || {});
    stream.on('error', () => res.destroy());
    res.on('close', () => stream.destroy());
    stream.pipe(res);
  } catch (err) {
    console.error(err.message);
    if (!res.headersSent) json(res, 500, {detail: 'Error al servir el archivo'});
    else res.destroy();
  }
});
server.on('error', err => {
  console.error(err.code === 'EADDRINUSE' ? `El puerto ${port} está ocupado. Usa PORT=8080 ./Start-CEMEC.sh` : err.message);
  process.exitCode = 1;
});
server.listen(port, host, () => {
  console.log(`CEMEC disponible en http://${host === '0.0.0.0' ? 'localhost' : host}:${port}`);
  console.log('Detener: Ctrl+C');
});
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => {
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(0), 2000).unref();
});
