from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_skin import SKIN, SkinError, keyboard_content_size, layout_rectangles, package_skin, validate_skin


class SkinVariantTests(unittest.TestCase):
    def test_symmetric_padding_compacts_every_key_without_changing_height(self):
        for theme in ('light', 'dark'):
            for layout in ('pinyin', 'alphabetic'):
                for orientation, width in (('Portrait', 320), ('Landscape', 568)):
                    doc = json.loads((SKIN / theme / (layout + orientation + '.yaml')).read_text(encoding='utf-8'))
                    original = deepcopy(doc)
                    for padding in (0, 8, 12, 16, 20, 24):
                        doc['keyboardStyle']['insets'] = {'left': padding, 'right': padding}
                        available_width, height = keyboard_content_size(doc, width)
                        self.assertEqual(available_width, width - 2 * padding)
                        self.assertEqual(height, doc['keyboardHeight'])
                        rectangles = dict(layout_rectangles(doc, 'keyboardLayout', available_width, height))
                        for letter in 'qwertyuiopasdfghjklzxcvbnm':
                            self.assertEqual(doc[letter + 'Button'], original[letter + 'Button'])
                            self.assertAlmostEqual(rectangles[letter + 'Button'][3], height / 4)
                        self.assertAlmostEqual(rectangles['qButton'][2], available_width / 10)
                        self.assertAlmostEqual(rectangles['pButton'][0] + rectangles['pButton'][2], available_width)

    def test_invalid_or_consuming_keyboard_insets_are_rejected(self):
        doc = {'keyboardHeight': 216, 'keyboardStyle': {}}
        for insets in ({'left': -1}, {'left': float('nan')}, {'right': '24'}, {'left': True},
                       {'left': 160, 'right': 160}, {'top': 216}):
            with self.subTest(insets=insets), self.assertRaises(SkinError):
                doc['keyboardStyle']['insets'] = insets
                keyboard_content_size(doc, 320)

    def test_named_archive_preserves_source_padding_and_compiled_files(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.tools') as temporary:
            skin = Path(temporary) / 'skin'
            shutil.copytree(SKIN, skin)
            config = json.loads((skin / 'config.yaml').read_text(encoding='utf-8'))
            config['name'] = '扁平灰白·留白16pt'
            (skin / 'config.yaml').write_text(json.dumps(config, ensure_ascii=False), encoding='utf-8')
            (skin / 'jsonnet/Constants/MainKeyboard.json').write_text('{"sidePadding":16}', encoding='utf-8')
            output = Path(temporary) / 'variant.cskin'
            package_skin(output, skin)
            with zipfile.ZipFile(output) as archive:
                self.assertIsNone(archive.testzip())
                self.assertTrue(all(name.startswith(config['name'] + '/') for name in archive.namelist()))
                for relative in ('jsonnet/Constants/MainKeyboard.json', 'light/pinyinPortrait.yaml', 'demo.png'):
                    self.assertEqual(archive.read(config['name'] + '/' + relative), (skin / relative).read_bytes())
            for name in ('../escape', '..', 'bad/name', 'bad\\name', ''):
                config['name'] = name
                (skin / 'config.yaml').write_text(json.dumps(config), encoding='utf-8')
                with self.subTest(name=name), self.assertRaisesRegex(SkinError, 'invalid skin name'):
                    package_skin(output, skin)

    def test_skin_validation_checks_the_reduced_content_area(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.tools') as temporary:
            skin = Path(temporary) / 'skin'
            shutil.copytree(SKIN, skin)
            filename = skin / 'light/pinyinPortrait.yaml'
            doc = json.loads(filename.read_text(encoding='utf-8'))
            doc['keyboardStyle']['insets'] = {'left': 160, 'right': 160}
            filename.write_text(json.dumps(doc), encoding='utf-8')
            with self.assertRaisesRegex(SkinError, 'insets consume content area'):
                validate_skin(skin)

    @unittest.skipUnless(importlib.util.find_spec('PIL'), 'Pillow unavailable')
    def test_variant_builder_rejects_invalid_padding_before_writing(self):
        from build_skin_variants import build_variants
        with tempfile.TemporaryDirectory(dir=ROOT / '.tools') as temporary:
            output = Path(temporary) / 'output'
            for padding in ([], [-1], [25], [True], [8.5]):
                with self.subTest(padding=padding), self.assertRaises(SkinError):
                    build_variants(output, Path('unused'), padding)
                self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
