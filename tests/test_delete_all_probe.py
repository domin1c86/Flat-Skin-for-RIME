import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_delete_all_probe import build_probe
from build_skin import SKIN, SkinError, validate_action, validate_document
from rime_skin_actions import CANCEL, RESET, semantic_action

BINARY = shutil.which('jsonnet') or ROOT / '.tools' / ('jsonnet.exe' if sys.platform == 'win32' else 'jsonnet')


def fingerprints():
    return {path.relative_to(SKIN).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in SKIN.rglob('*') if path.is_file()}


class DeleteAllProbeValidationTests(unittest.TestCase):
    def test_invalid_padding_is_rejected_without_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'output'
            for padding in (-1, 25, True, 2.5):
                with self.subTest(padding=padding), self.assertRaises(SkinError):
                    build_probe(output, Path('unused'), padding)
                self.assertFalse(output.exists())

    def test_only_named_clear_shortcuts_are_added(self):
        for shortcut in ('#重输', '#deleteText'):
            validate_action({'shortcut': shortcut}, 'probe')
        with self.assertRaisesRegex(SkinError, 'unknown shortcut'):
            validate_action({'shortcut': '#deleteAllInvented'}, 'probe')


@unittest.skipUnless(Path(BINARY).is_file(), 'native Jsonnet CLI unavailable')
class DeleteAllProbePackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / '.tools')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.before = fingerprints()
        cls.output, cls.count = build_probe(Path(cls.temporary.name), BINARY, padding=12)
        with zipfile.ZipFile(cls.output) as archive:
            cls.crc_error = archive.testzip()
            cls.files = {name.split('/', 1)[1]: archive.read(name) for name in archive.namelist()}
            cls.roots = {name.split('/', 1)[0] for name in archive.namelist()}

    def test_package_is_separate_and_keeps_recompilable_source(self):
        self.assertIsNone(self.crc_error)
        self.assertEqual(self.count, 28)
        config = json.loads(self.files['config.yaml'])
        self.assertEqual(config['name'], '扁平灰白·留白12pt·删除全部验证')
        self.assertEqual(self.roots, {config['name']})
        self.assertEqual(json.loads(self.files['jsonnet/Constants/MainKeyboard.json']), {'sidePadding': 12})
        self.assertEqual(self.files['jsonnet/main.standard.jsonnet'], (SKIN / 'jsonnet/main.jsonnet').read_bytes())
        self.assertEqual(self.files['jsonnet/main.jsonnet'], (ROOT / 'experiments/delete-all/main.jsonnet').read_bytes())
        self.assertEqual(fingerprints(), self.before)

    def test_primary_keys_keep_tap_and_require_hold_selection(self):
        for theme in ('light', 'dark'):
            for layout in ('pinyin', 'alphabetic'):
                for orientation in ('Portrait', 'Landscape'):
                    path = theme + '/' + layout + orientation + '.yaml'
                    with self.subTest(path=path):
                        document = json.loads(self.files[path])
                        validate_document(document)
                        original = json.loads((SKIN / path).read_text(encoding='utf-8'))
                        expected = {field: value for field, value in original['backspaceButton'].items()
                                    if field != 'repeatAction'}
                        expected['hintSymbolsGridStyle'] = 'deleteAllProbeGrid'
                        self.assertEqual(document['backspaceButton'], expected)
                        self.assertEqual(document['backspaceButton']['action'], 'backspace')
                        self.assertNotIn('swipeUpAction', document['backspaceButton'])
                        grid = document['deleteAllProbeGrid']
                        self.assertEqual(grid['symbolRows'], [['deleteAllProbeOption'], ['deleteAllProbeCancel']])
                        self.assertEqual(grid['selected'], {'row': 1, 'col': 0})
                        self.assertEqual(grid['anchor'], grid['selected'])
                        self.assertEqual(grid['moveStep']['vertical'], 40)
                        self.assertEqual(grid['moveThreshold'], 16)
                        self.assertTrue(grid['checkIfOverflowsParentHeight'])
                        cancel = document['deleteAllProbeCancel']
                        self.assertEqual(cancel['action'], 'none')
                        self.assertFalse(any(field.endswith('Action') for field in cancel))
                        self.assertEqual(document[cancel['foregroundStyle']]['text'], '取消')
                        option = document['deleteAllProbeOption']
                        self.assertEqual(document[option['foregroundStyle']]['text'], '删除全部')
                        self.assertEqual(semantic_action(option['action']), {
                            'combine': [{'shortcut': '#重输'}, {'shortcut': '#deleteText'}]})
                        self.assertEqual(option['action']['combine'][0], CANCEL)
                        self.assertEqual(option['action']['combine'][-1], RESET)
                        original['backspaceButton'] = expected
                        original['keyboardStyle']['insets'] = {'left': 12, 'right': 12}
                        for name, node in original.items():
                            self.assertEqual(document[name], node, name)
                        self.assertEqual(set(document) - set(original), {
                            'deleteAllProbeGrid', 'deleteAllProbeOption', 'deleteAllProbeCancel',
                            'deleteAllProbeLabel', 'deleteAllProbeCancelLabel'})

    def test_all_other_layouts_and_resources_are_unchanged(self):
        for path, contents in self.files.items():
            if path.startswith(('light/', 'dark/')) and not any(
                path.endswith('/' + layout + orientation + '.yaml')
                for layout in ('pinyin', 'alphabetic') for orientation in ('Portrait', 'Landscape')
            ):
                with self.subTest(path=path):
                    if path.endswith('.yaml'):
                        self.assertEqual(json.loads(contents), json.loads((SKIN / path).read_bytes()))
                    else:
                        self.assertEqual(contents, (SKIN / path).read_bytes())


if __name__ == '__main__':
    unittest.main()
