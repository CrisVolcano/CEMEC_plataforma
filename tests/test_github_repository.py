"""Auditoría de publicación sin datos ni credenciales reales."""
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import github_repository as repository


class RepositoryTests(unittest.TestCase):
    def test_known_secret_nested_archive_and_redaction(self):
        secret = b'private-example-value-for-test'
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as archive:
            archive.writestr('word/document.xml', b'<p>'+secret+b'</p>')
        with self.assertRaises(ValueError) as error:
            repository.inspect_blob(data.getvalue(), 'manual.docx', {secret})
        self.assertNotIn(secret.decode(), str(error.exception))

    def test_excluded_operational_files_and_empty_template(self):
        for name in ['.env', '.env.production', 'entregas/prueba.zip', '.respaldos/v1/code.tar.gz', 'runtime/firms/active.json', 'origen/app.zip']:
            self.assertTrue(repository.blocked(name), name)
        self.assertFalse(repository.blocked('.env.example'))
        repository.inspect_blob(b'FIRMS_MAP_KEY=\nCDSE_CLIENT_SECRET=\n', '.env.example', set())

    def test_staged_secret_is_found_even_if_working_file_is_clean(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            path = root / 'sample.txt'
            secret = 'github_pat_' + 'Z' * 50
            path.write_text(secret)
            subprocess.run(['git', '-C', str(root), 'add', 'sample.txt'], check=True)
            path.write_text('clean working file\n')
            with patch.object(repository, 'ROOT', root):
                with self.assertRaises(ValueError) as error:
                    repository.audit(staged=True)
                self.assertNotIn(secret, str(error.exception))


if __name__ == '__main__':
    unittest.main()
