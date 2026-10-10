from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from rime_native import prepare


class NativeFixtureIsolationTests(unittest.TestCase):
    def test_nested_context_databases_preferences_and_backups_are_not_copied(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.tools') as temp:
            source = Path(temp)
            for name in ('lua', 'dicts', 'opencc'):
                (source / name).mkdir()
            (source / 'lua/skin_context.lua').write_text('return {}', encoding='utf-8')
            (source / 'dicts/custom_simple.dict.yaml').write_text('static dictionary', encoding='utf-8')
            (source / 'lua/skin_context.userdb').mkdir()
            private = source / 'lua/skin_context.userdb/private.log'
            private.write_bytes(b'private learning')
            (source / 'dicts/.backups').mkdir()
            (source / 'dicts/.backups/private.dict.yaml').write_text('backup', encoding='utf-8')
            for name in ('user.yaml', 'installation.yaml', 'skin_scheme_memory.yaml'):
                (source / name).write_text('private preference', encoding='utf-8')
            fixture = prepare(source)
            self.assertTrue((fixture / 'lua/skin_context.lua').is_file())
            self.assertTrue((fixture / 'dicts/custom_simple.dict.yaml').is_file())
            self.assertFalse((fixture / 'lua/skin_context.userdb').exists())
            self.assertFalse((fixture / 'dicts/.backups').exists())
            for name in ('user.yaml', 'installation.yaml', 'skin_scheme_memory.yaml'):
                self.assertFalse((fixture / name).exists())
            self.assertEqual(private.read_bytes(), b'private learning')
