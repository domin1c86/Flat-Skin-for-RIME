from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_rime_bundle import build


class RimeBundleTests(unittest.TestCase):
    def test_companion_archive_has_no_personal_words_databases_or_backup_tree(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.tools') as temp:
            path = build(Path(temp) / 'bundle.zip')
            with zipfile.ZipFile(path) as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(len(archive.namelist()), 11)
                self.assertTrue(all('userdb' not in name and 'dicts/' not in name
                                    and '.backups' not in name for name in archive.namelist()))
                self.assertIn('lua/skin_context.lua', archive.namelist())
                self.assertEqual(archive.read('lua/skin_context.lua'),
                                 (ROOT / 'scripts/rime/skin_context.lua').read_bytes())
