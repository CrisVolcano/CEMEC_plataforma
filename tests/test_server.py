"""Pruebas HTTP reales: PMTiles, catálogos, aislamiento y modo estático."""
import http.client
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest

PROJECT = Path(__file__).resolve().parents[1]
SITE = PROJECT / 'cemec-sitio-estatico'

class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            cls.port = sock.getsockname()[1]
        cls.process = subprocess.Popen([
            str(Path(sys.executable).parent / 'node'), str(PROJECT / 'serve.js'),
            '--port', str(cls.port), '--root', str(SITE),
        ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        cls.addClassCleanup(cls.stop_server)
        for _ in range(100):
            if cls.process.poll() is not None:
                raise RuntimeError(cls.process.stderr.read().decode())
            try:
                cls.request('GET', '/')
                break
            except OSError:
                time.sleep(0.05)
        else:
            raise RuntimeError('El servidor no inició')
        cls.tiles = json.loads((SITE / 'data/catalog.json').read_text())['pmtiles_url']
        cls.content = (SITE / cls.tiles.lstrip('/')).read_bytes()

    @classmethod
    def stop_server(cls):
        cls.process.terminate()
        try:
            cls.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.process.kill()
            cls.process.wait()
        cls.process.stderr.close()

    @classmethod
    def request(cls, method, path, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', cls.port, timeout=10)
        try:
            conn.request(method, path, headers=headers or {})
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            conn.close()

    def test_original_page_and_catalog(self):
        status, headers, body = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn(b'/cemec-ui.css', body)
        self.assertIn(b'/assets/index-LLDJc-3y.js', body)
        status, headers, body = self.request('GET', '/data/catalog.json')
        self.assertEqual(status, 200)
        self.assertEqual(headers['Cache-Control'], 'no-cache')
        self.assertEqual(json.loads(body)['total_points'], 66582)

    def test_redesigned_assets_and_private_files(self):
        status, headers, body = self.request('GET', '/cemec-ui.css')
        self.assertEqual(status, 200)
        self.assertIn(b'.cemec-control-grid', body)
        status, headers, body = self.request('GET', '/assets/index-LLDJc-3y.js')
        self.assertEqual(status, 200)
        self.assertIn(b'function CemecView', body)
        for url in ['/.env', '/ui/cemec-view.js', '/respaldos/ultimo-respaldo.json']:
            self.assertEqual(self.request('GET', url)[0], 404)

    def test_pmtiles_header_range(self):
        status, headers, body = self.request('GET', self.tiles, {'Range': 'bytes=0-126'})
        self.assertEqual(status, 206)
        self.assertEqual(body, self.content[:127])
        self.assertTrue(body.startswith(b'PMTiles'))
        self.assertEqual(headers['Content-Range'], f'bytes 0-126/{len(self.content)}')
        self.assertEqual(headers['Content-Length'], '127')
        self.assertEqual(headers['Accept-Ranges'], 'bytes')

    def test_geopdf_vendor_allowlist(self):
        url = '/cemec-vendor/maplibre-gl-export-6.0.0/maplibre-gl-export.umd.js'
        status, headers, body = self.request('GET', url)
        self.assertEqual(status, 200)
        self.assertTrue(headers['Content-Type'].startswith('text/javascript'))
        self.assertIn(b'createGeoPdfViewport', body)
        status, headers, body = self.request('HEAD', url)
        self.assertEqual(status, 200)
        self.assertEqual(body, b'')
        for url in ['/cemec-vendor/../../../.env', '/cemec-vendor/.env',
                    '/cemec-vendor/maplibre-gl-export-6.0.0/provenance.json']:
            self.assertEqual(self.request('GET', url)[0], 404)

    def test_suffix_and_open_range(self):
        for spec in ('bytes=-20', f'bytes={len(self.content)-20}-'):
            with self.subTest(spec=spec):
                status, headers, body = self.request('GET', self.tiles, {'Range': spec})
                self.assertEqual(status, 206)
                self.assertEqual(body, self.content[-20:])

    def test_unsatisfiable_range(self):
        status, headers, body = self.request('GET', self.tiles, {'Range': f'bytes={len(self.content)}-'})
        self.assertEqual(status, 416)
        self.assertEqual(headers['Content-Range'], f'bytes */{len(self.content)}')
        self.assertEqual(body, b'')

    def test_head_and_multiple_ranges(self):
        status, headers, body = self.request('HEAD', self.tiles)
        self.assertEqual(status, 200)
        self.assertEqual(int(headers['Content-Length']), len(self.content))
        self.assertEqual(body, b'')
        status, headers, body = self.request('GET', self.tiles, {'Range': 'bytes=0-5,10-15'})
        self.assertEqual(status, 200)
        self.assertEqual(body, self.content)

    def test_backend_unavailable_and_missing_asset(self):
        for method, url in [('GET', '/api/status'), ('POST', '/api/sync'), ('GET', '/assets/missing.js')]:
            with self.subTest(url=url):
                status, headers, body = self.request(method, url)
                self.assertEqual(status, 404)
                self.assertIn('application/json', headers['Content-Type'])
                self.assertIn('detail', json.loads(body))

    def test_cannot_read_project_or_parent_files(self):
        for url in ['/config.yaml', '/..%2fconfig.yaml', '/%00', '/data/']:
            with self.subTest(url=url):
                status, headers, body = self.request('GET', url)
                self.assertIn(status, (400, 403, 404))
                self.assertNotIn(b'archive_sha256', body)

    def test_prepared_report_download(self):
        catalog = json.loads((SITE / 'products/catalog.json').read_text())
        url = catalog['products'][0]['report_url']
        status, headers, body = self.request('GET', url)
        self.assertEqual(status, 200)
        self.assertEqual(headers['Content-Type'], 'application/pdf')
        self.assertEqual(body, (SITE / url.lstrip('/')).read_bytes())

    def test_sig_beta_read_only_and_provenance(self):
        import hashlib
        status, headers, body = self.request('GET', '/sig-beta/')
        self.assertEqual(status, 200)
        self.assertIn('Del dato al análisis'.encode(), body)
        status, headers, body = self.request('GET', '/sig-beta/data/manifest.json')
        self.assertEqual(status, 200)
        self.assertEqual(headers['Access-Control-Allow-Origin'], '*')
        manifest = json.loads(body)
        counts = {}
        for layer in manifest['layers']:
            url = '/sig-beta/data/' + layer['file']
            status, headers, content = self.request('GET', url)
            self.assertEqual(status, 200)
            self.assertEqual(hashlib.sha256(content).hexdigest(), layer['sha256'])
            features = json.loads(content)['features']
            self.assertEqual(len(features), layer['count'])
            counts[layer['id']] = len(features)
            self.assertEqual(self.request('HEAD', url)[2], b'')
            self.assertEqual(self.request('OPTIONS', url)[0], 204)
            self.assertEqual(self.request('POST', url)[0], 405)
        self.assertEqual(counts, {'municipios': 14, 'areas-protegidas': 68, 'viirs-marzo-2026': 986})
        original = json.loads((SITE / 'data/v-79544d8e805b0b1d/web/2026-03.json').read_text())
        ids = {r['id'] for r in original if r['instrument'] == 'VIIRS' and 'region-peten' in r['units']}
        points = json.loads(self.request('GET', '/sig-beta/data/viirs-marzo-2026.geojson')[2])['features']
        self.assertEqual({r['id'] for r in points}, ids)
        for r in points:
            self.assertEqual(r['geometry']['type'], 'Point')
            self.assertTrue(r['properties']['date'].startswith('2026-03-'))

    def test_sig_beta_private_paths(self):
        for url in ['/sig-beta/.env', '/sig-beta/data/active.json', '/sig-beta/data/%2e%2e%2f.env',
                    '/sig-beta/data/', '/sig-beta/../../.env']:
            self.assertIn(self.request('GET', url)[0], (403, 404))

    def test_local_interface_fonts(self):
        for name in ['Barlow-Regular.ttf', 'Barlow-SemiBold.ttf']:
            status, headers, body = self.request('GET', '/cemec-vendor/barlow/' + name)
            self.assertEqual(status, 200)
            self.assertEqual(headers['Content-Type'], 'font/ttf')
            self.assertEqual(body, (PROJECT / 'ui/vendor/barlow' / name).read_bytes())
        self.assertEqual(self.request('GET', '/cemec-vendor/barlow/../../.env')[0], 404)

if __name__ == '__main__':
    unittest.main(verbosity=2)
