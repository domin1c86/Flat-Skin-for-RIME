from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from manage_personal_dict import edit


class PersonalDictionaryTests(unittest.TestCase):
    def setUp(self):
        cache = Path(__file__).resolve().parents[1] / '.tools'
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'dicts/custom_simple.dict.yaml'
        self.path.parent.mkdir()
        self.original = b'\xef\xbb\xbf' + ('# existing\r\n---\r\nname: custom_simple\r\n...\r\n\r\n原词\tyuan ci\t99\r\n').encode()
        self.path.write_bytes(self.original)

    def test_add_update_remove_preserve_header_old_words_and_backup(self):
        _, backup, _ = edit(self.root, 'add', '库莉姆', 'ku li mu')
        self.assertEqual(backup.read_bytes(), self.original)
        self.assertTrue(self.path.read_bytes().startswith(self.original))
        edit(self.root, 'update', '库莉姆', 'ku li mu', 123)
        self.assertIn('库莉姆\tku li mu\t123\r\n', self.path.read_bytes().decode('utf-8-sig'))
        edit(self.root, 'remove', '库莉姆', 'ku li mu')
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_invalid_duplicate_and_missing_do_not_change_dictionary(self):
        for operation, word, code, weight in [('add', '原词', 'yuan ci', 99),
                ('update', '缺词', 'que ci', 100), ('remove', '缺词', 'que ci', 100),
                ('add', '恶\t词', 'e ci', 100), ('add', '词', 'ku  li', 100),
                ('add', '词', 'Ku', 100), ('add', '词', 'ci', -1)]:
            with self.subTest(operation=operation, code=code):
                with self.assertRaises(ValueError):
                    edit(self.root, operation, word, code, weight)
                self.assertEqual(self.path.read_bytes(), self.original)
        self.assertFalse((self.path.parent / '.backups').exists())

    def test_dry_run_and_noop_do_not_create_backup(self):
        edit(self.root, 'add', '库莉姆', 'ku li mu', dry_run=True)
        self.assertEqual(self.path.read_bytes(), self.original)
        self.assertFalse(edit(self.root, 'update', '原词', 'yuan ci', 99)[2])
        self.assertFalse((self.path.parent / '.backups').exists())

    def test_duplicate_file_and_wrong_dictionary_rejected(self):
        self.path.write_bytes(self.original + '原词\tyuan ci\t100\r\n'.encode())
        with self.assertRaisesRegex(ValueError, '重复'):
            edit(self.root, 'add', '库莉姆', 'ku li mu')
        self.path.write_bytes(self.original.replace(b'custom_simple', b'other'))
        with self.assertRaisesRegex(ValueError, 'custom_simple'):
            edit(self.root, 'add', '库莉姆', 'ku li mu')
