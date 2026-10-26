'use strict';
(async () => {
  const status = document.getElementById('connection-status');
  try {
    const response = await fetch('/sig-beta/data/manifest.json');
    if (!response.ok) throw Error('No se pudieron cargar las fichas. Reintenta al recargar la página.');
    const manifest = await response.json();
    document.getElementById('summary').textContent = `${manifest.edition} · Coordenadas: ${manifest.coordinates}.`;
    for (const layer of manifest.layers) {
      const card = document.createElement('article'); card.className = 'layer';
      for (const [tag, value, className] of [['h3', layer.title, ''], ['p', `${layer.count.toLocaleString('es')} geometrías · ${(layer.bytes / 1024).toFixed(0)} KB`, 'count'], ['p', layer.source, 'source'], ['p', layer.limitations, '']]) {
        const item = document.createElement(tag); item.textContent = value; item.className = className; card.append(item);
      }
      const link = document.createElement('a'); link.className = 'button';
      link.textContent = 'Descargar GeoJSON'; link.href = '/sig-beta/data/' + layer.file;
      link.download = layer.file; link.setAttribute('aria-label', 'Descargar ' + layer.title + ' · GeoJSON'); card.append(link);
      document.getElementById('layers').append(card);
    }
    let config;
    try { const r = await fetch('/sig-beta/config.json'); if (!r.ok) throw Error(); config = await r.json(); }
    catch { status.textContent = 'No se pudo consultar la conexión automática. Puedes descargar las capas y agregarlas manualmente en GeoLibre.'; return; }
    if (config.public_base_url) {
      const base = new URL(config.public_base_url);
      if (base.protocol !== 'https:' || base.username || base.password || base.search || base.hash) throw Error('La dirección pública configurada no es válida. Usa las descargas directas.');
      const target = new URL('https://web.geolibre.app/');
      for (const layer of manifest.layers) target.searchParams.append('data', new URL('data/' + layer.file, base.href.replace(/\/?$/, '/')).href);
      document.getElementById('open-gis').href = target.href;
      document.getElementById('open-gis').textContent = 'Abrir las tres capas en GeoLibre ↗';
      status.textContent = 'Apertura conectada preparada. Los archivos deben estar disponibles en la dirección pública configurada, con acceso CORS. Si falla, descarga y agrega las capas manualmente.';
    } else {
      status.textContent = 'Modo local: descarga las capas y agrégalas en GeoLibre. La apertura automática necesita archivos publicados en HTTPS; localhost no se envía al sitio externo.';
    }
  } catch (err) {
    const error = document.getElementById('error'); error.hidden = false; error.textContent = err.message;
    status.textContent = 'El acceso a GeoLibre sigue disponible. Revisa los archivos del ejercicio antes de continuar.';
  }
})();
