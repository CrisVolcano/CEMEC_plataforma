"""Instalación desde archivos verificados sin requerir el ZIP privado original."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/replicate.py'


class ReplicateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        catalog = {'version':'v-demo','boundary_version':'b-demo','total_points':0,'date_min':None,'date_max':None,'units':[]}
        for name, content in [('site/assets/app.js', '/* fixture */'), ('site/data/catalog.json', json.dumps(catalog)), ('site/products/catalog.json','{"products":[]}')]:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        files = [{'path':str(p.relative_to(self.root/'site')), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (self.root/'site').rglob('*') if p.is_file()]
        (self.root/'manifest.json').write_text(json.dumps({'files':files}))
        config = {'artifacts':{'archive':'origen/app.zip','archive_sha256':'0'*64,'manual':'origen/manual.docx','manual_sha256':'0'*64,'original_manifest':'manifest.json'}, 'server':{'root':'site'}, 'dataset':{**{k:catalog[k] for k in ['version','boundary_version','total_points','date_min','date_max']},'territory_count':0}}
        (self.root/'config.yaml').write_text(yaml.safe_dump(config))

    def run_copy(self, *args):
        return subprocess.run([sys.executable,str(SCRIPT),'--config',str(self.root/'config.yaml'),*args],capture_output=True,text=True)

    def test_complete_checkout_without_archives(self):
        for args in [(), ('--verify-only',)]:
            result=self.run_copy(*args)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_missing_files_require_original_or_complete_checkout(self):
        (self.root/'site/assets/app.js').unlink()
        result=self.run_copy()
        self.assertNotEqual(result.returncode,0)
        self.assertIn('checkout completo',result.stderr)

    def test_existing_original_with_bad_hash_is_rejected(self):
        (self.root/'origen').mkdir()
        (self.root/'origen/app.zip').write_bytes(b'bad archive')
        self.assertNotEqual(self.run_copy('--verify-only').returncode,0)

    def test_modified_compilation_is_never_overwritten(self):
        target=self.root/'site/assets/app.js'
        target.write_text('modified\n')
        self.assertNotEqual(self.run_copy().returncode,0)
        self.assertEqual(target.read_text(),'modified\n')


if __name__ == '__main__':
    unittest.main()
