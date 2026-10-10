"""Pixel regressions for the native classification highlight's rounded inset."""
import importlib.util
import base64
import io
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
HAS_PILLOW = importlib.util.find_spec('PIL') is not None
if HAS_PILLOW:
    from PIL import ImageColor
    from render_skin_preview import SCALE, inset, render_keyboard
from test_skin import load
from build_skin import layout_rectangles


@unittest.skipUnless(HAS_PILLOW, 'Pillow is optional; install it to test preview pixels')
class ClassificationHighlightTests(unittest.TestCase):
    def test_selected_categories_have_rounded_corners_and_interior_fill(self):
        for scheme in ('light', 'dark'):
            for orientation, width in (('Portrait', 390), ('Landscape', 680)):
                name = 'symbolic' + orientation
                doc = load(name, scheme)
                rects = dict(layout_rectangles(doc, 'keyboardLayout', width, doc['keyboardHeight']))
                x, y, w, h = inset(rects['symbolCategories'], doc['symbolCategories']['insets'])
                y += doc['preeditHeight'] + doc['toolbarHeight']
                row_height = h / len(doc['symbolCategoryData'])
                highlight = doc['symbolCategoryHighlight']
                color = ImageColor.getrgb(highlight['highlightColor'])
                for index, category in enumerate(doc['symbolCategoryData']):
                    with self.subTest(scheme=scheme, orientation=orientation, category=category):
                        image = render_keyboard(name, scheme, width=width, category=category)
                        hx, hy, hw, hh = inset((x, y + row_height * index, w, row_height), highlight['insets'])
                        # A square full-cell highlight would color the top-left corner.
                        self.assertNotEqual(image.getpixel((round(hx * SCALE), round(hy * SCALE))), color)
                        # Just below the top edge, away from text, must be visibly selected.
                        self.assertEqual(image.getpixel((round((hx + hw / 2) * SCALE), round((hy + 1) * SCALE))), color)
                        for other in range(3):
                            if other != index:
                                sample = (round((x + w / 2) * SCALE), round((y + row_height * other + 3) * SCALE))
                                self.assertNotEqual(image.getpixel(sample), color)

    def test_unknown_category_fails(self):
        with self.assertRaisesRegex(ValueError, 'Unknown symbol category'):
            render_keyboard('symbolicPortrait', 'light', category='missing')

    def test_language_atlas_keeps_geometry_and_same_active_colors(self):
        from PIL import Image
        for scheme, active, inactive in (('light', '#000000', '#A1A3A6'), ('dark', '#F4F4F6', '#91939B')):
            atlas = Image.open(ROOT / 'default' / scheme / 'resources' / 'language.png').convert('RGBA')
            self.assertEqual(atlas.size, (760, 410))
            chinese, english = atlas.crop((0, 0, 380, 410)), atlas.crop((380, 0, 760, 410))
            self.assertEqual(chinese.getchannel('A').tobytes(), english.getchannel('A').tobytes())
            self.assertEqual(chinese.getpixel((0, 0))[3], 0)
            for tile in (chinese, english):
                opaque_colors = {pixel[:3] for _, pixel in tile.getcolors(tile.width * tile.height) if pixel[3] == 255}
                self.assertEqual(opaque_colors, {ImageColor.getrgb(active), ImageColor.getrgb(inactive)})
            for orientation in ('Portrait', 'Landscape'):
                doc = load('pinyin' + orientation, scheme)
                self.assertEqual(doc['phoneChineseModeIcon']['insets'], doc['phoneEnglishModeIcon']['insets'])

    def test_preview_language_images_are_isolated_native_tiles(self):
        """Wider aspect-fit viewports must never reveal the adjacent language."""
        from PIL import Image
        html = (ROOT / 'preview' / 'index.html').read_text(encoding='utf-8')
        match = re.search(r'const languageImages = (\{[^\n]+\});', html)
        self.assertIsNotNone(match)
        images = json.loads(match.group(1))
        for scheme in ('light', 'dark'):
            atlas = Image.open(ROOT / 'default' / scheme / 'resources' / 'language.png').convert('RGBA')
            for index, language in enumerate(('zh', 'en')):
                with self.subTest(scheme=scheme, language=language):
                    uri = images[scheme][language]
                    self.assertTrue(uri.startswith('data:image/png;base64,'))
                    tile = Image.open(io.BytesIO(base64.b64decode(uri.split(',', 1)[1]))).convert('RGBA')
                    self.assertEqual(tile.size, (380, 410))
                    expected = atlas.crop((index * 380, 0, (index + 1) * 380, 410))
                    self.assertEqual(tile.tobytes(), expected.tobytes())

    def test_chinese_punctuation_is_horizontally_centered_at_english_height(self):
        from PIL import Image
        for scheme in ('light', 'dark'):
            atlas = Image.open(ROOT / 'default' / scheme / 'resources' / 'punctuation.png').convert('RGBA')
            for index in range(2):
                tile = atlas.crop((index * 200, 0, (index + 1) * 200, 200))
                left, top, right, bottom = tile.getchannel('A').getbbox()
                self.assertAlmostEqual((left + right) / 2, 100, delta=.5)
                self.assertAlmostEqual((top + bottom) / 2, 100, delta=.5)
            for orientation, width in (('Portrait', 320), ('Portrait', 390), ('Landscape', 680)):
                doc = load('pinyin' + orientation, scheme)
                rects = dict(layout_rectangles(doc, 'keyboardLayout', width, doc['keyboardHeight']))
                image = render_keyboard('pinyin' + orientation, scheme, width=width)
                english_image = render_keyboard('pinyin' + orientation, scheme, width=width, ascii_mode=True)
                for key in ('chineseCommaButton', 'chinesePeriodButton'):
                    x, y, w, h = rects[key]
                    y += doc['preeditHeight'] + doc['toolbarHeight']
                    crop = image.crop(tuple(round(v * SCALE) for v in (x, y, x + w, y + h)))
                    foreground = ImageColor.getrgb('#000000' if scheme == 'light' else '#F4F4F6')
                    mask = Image.new('L', crop.size)
                    # Antialiasing can leave no pixel exactly at the foreground tint.
                    mask.putdata([255 if max(abs(pixel[i] - foreground[i]) for i in range(3)) < 64 else 0
                                  for pixel in crop.get_flattened_data()])
                    left, top, right, bottom = mask.getbbox()
                    self.assertAlmostEqual((left + right) / 2, crop.width / 2, delta=1)
                    english_crop = english_image.crop(tuple(round(v * SCALE) for v in (x, y, x + w, y + h)))
                    english_mask = Image.new('L', english_crop.size)
                    english_mask.putdata([255 if max(abs(pixel[i] - foreground[i]) for i in range(3)) < 64 else 0
                                          for pixel in english_crop.get_flattened_data()])
                    _, english_top, _, english_bottom = english_mask.getbbox()
                    # Chinese punctuation keeps its ink centered horizontally,
                    # but uses the same vertical ink center as English , and .
                    self.assertAlmostEqual((top + bottom) / 2, (english_top + english_bottom) / 2, delta=1.5)


if __name__ == '__main__':
    unittest.main()
