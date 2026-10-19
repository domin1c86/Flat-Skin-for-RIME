"""Pixel regressions for the native classification highlight's rounded inset."""
import importlib.util
import base64
import io
import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
HAS_PILLOW = importlib.util.find_spec('PIL') is not None
if HAS_PILLOW:
    from PIL import ImageColor
    from render_skin_preview import SCALE, inset, render_keyboard, selected, effective_button, button_foreground
from test_skin import load
from build_skin import layout_rectangles


@unittest.skipUnless(HAS_PILLOW, 'Pillow is optional; install it to test preview pixels')
class ClassificationHighlightTests(unittest.TestCase):
    @unittest.skipUnless(Path('C:/Windows/Fonts/seguisym.ttf').is_file(), 'Windows symbol fonts unavailable')
    def test_catalog_symbols_have_renderable_glyphs_with_font_fallback(self):
        from render_skin_preview import font
        catalog = json.loads((ROOT / 'default/jsonnet/Constants/SymbolCatalog.json').read_text(encoding='utf-8'))
        characters = {character for category in catalog['categories'] for value in category['symbols'] for character in value}
        for character in sorted(characters):
            with self.subTest(character=character, codepoint=f'U+{ord(character):04X}'):
                candidate = font(20, character)
                glyph, missing = candidate.getmask(character), candidate.getmask('\U0010ffff')
                self.assertTrue(glyph.size != missing.size or bytes(glyph) != bytes(missing))

    def test_offscreen_collection_entries_do_not_paint_outside_viewports(self):
        original_loads = json.loads
        for scheme in ('light', 'dark'):
            for orientation in ('Portrait', 'Landscape'):
                for kind, category in (('numeric', '常用'), ('symbolic', '日文')):
                    name = kind + orientation
                    complete = render_keyboard(name, scheme, category=category)

                    def visible_only(source):
                        document = original_loads(source)
                        if 'numericOperatorData' in document:
                            document['numericOperatorData'] = document['numericOperatorData'][:4]
                        if '日文' in document:
                            document['日文'] = document['日文'][:20]
                        return document

                    with patch('render_skin_preview.json.loads', side_effect=visible_only):
                        clipped = render_keyboard(name, scheme, category=category)
                    self.assertEqual(complete.tobytes(), clipped.tobytes())

    def test_short_callout_case_swipe_priority_and_notification_cycles(self):
        from render_callout_preview import callout_foreground, render_callout
        catalog = json.loads((ROOT / 'default/jsonnet/Constants/LetterSymbols.json').read_text(encoding='utf-8'))
        for scheme in ('light', 'dark'):
            for orientation in ('Portrait', 'Landscape'):
                doc = load('pinyin' + orientation, scheme)
                for initial in (False, True):
                    for step, english in enumerate((initial, not initial, initial, not initial, initial)):
                        doc = load(('alphabetic' if english else 'pinyin') + orientation, scheme)
                        for shift, caps in ((False, False), (True, False), (False, True), (True, True)):
                            for i, letter in enumerate(catalog['letters']):
                                for swipe in (False, True):
                                    hint, foreground = callout_foreground(doc, letter, english, shift, caps, swipe, step > 0)
                                    expected = catalog['english' if english else 'chinese'][i] if swipe else (
                                        letter if english and not shift and not caps else letter.upper())
                                    self.assertEqual(foreground['text'], expected)
                                    self.assertEqual(foreground['fontSize'], 26)
                                    self.assertEqual(hint['size'], {'width': 50, 'height': 50})
                for english in (False, True):
                    image = render_callout('f', scheme, english, orientation=orientation)
                    self.assertEqual(image.width, 390*SCALE)

    def test_renderer_rejects_mixed_native_style_arrays(self):
        from build_skin import SkinError
        with self.assertRaisesRegex(SkinError, 'mixed style reference array'):
            selected(['hint', {'conditionKey': 'rime$ascii_mode', 'conditionValue': False, 'styleName': 'letter'}])

    def test_letters_survive_initial_modes_and_language_cycles(self):
        for scheme in ('light', 'dark'):
            for orientation in ('Portrait', 'Landscape'):
                doc = load('pinyin' + orientation, scheme)
                for initial in (False, True):
                    for step, english in enumerate((initial, not initial, initial, not initial, initial)):
                        doc = load(('alphabetic' if english else 'pinyin') + orientation, scheme)
                        for shift, caps in ((False, False), (True, False), (False, True), (True, True)):
                            for letter in 'qwertyuiopasdfghjklzxcvbnm':
                                with self.subTest(scheme=scheme, orientation=orientation, initial=initial,
                                                  step=step, letter=letter, shift=shift, caps=caps):
                                    base = doc[letter + 'Button']
                                    node = effective_button(doc, base, english, step > 0)
                                    refs = selected(button_foreground(node, shift, caps), english)
                                    self.assertEqual(len(refs), 2)
                                    expected_hint = "1234567890~!@#%'&*?()-_:;/" if english else '1234567890～！＠＃％“”＊？（）-_：；`'
                                    self.assertEqual(doc[refs[0]]['text'], expected_hint['qwertyuiopasdfghjklzxcvbnm'.index(letter)])
                                    expected = letter.upper() if not english or shift or caps else letter
                                    self.assertEqual(doc[refs[1]]['text'], expected)
                                    for key in ('size', 'bounds', 'backgroundStyle', 'action', 'uppercasedStateAction'):
                                        self.assertEqual(node.get(key), base.get(key))
                                    self.assertEqual(doc[refs[0]]['center'], {'x': .5, 'y': .22})
                                    self.assertEqual(doc[refs[1]]['center'], {'x': .5, 'y': .59})

    def test_letter_pixels_match_before_and_after_language_changes(self):
        for scheme in ('light', 'dark'):
            for orientation, width in (('Portrait', 320), ('Portrait', 390), ('Landscape', 568), ('Landscape', 680)):
                name = 'pinyin' + orientation
                doc = load(name, scheme)
                rects = dict(layout_rectangles(doc, 'keyboardLayout', width, doc['keyboardHeight']))
                for english in (False, True):
                    for shift, caps in ((False, False), (True, False), (False, True)):
                        before = render_keyboard(name, scheme, width, ascii_mode=english, shift=shift, caps_locked=caps)
                        after = render_keyboard(name, scheme, width, ascii_mode=english, shift=shift,
                                                caps_locked=caps, after_language_change=True)
                        for letter in 'qwertyuiopasdfghjklzxcvbnm':
                            with self.subTest(scheme=scheme, orientation=orientation, width=width,
                                              letter=letter, english=english, shift=shift, caps=caps):
                                x, y, w, h = rects[letter + 'Button']
                                y += doc['preeditHeight'] + doc['toolbarHeight']
                                crop = tuple(round(v * SCALE) for v in (x, y, x + w, y + h))
                                initial, changed = before.crop(crop), after.crop(crop)
                                self.assertEqual(initial.tobytes(), changed.tobytes())
                                # Lower portion contains the letter, not the upper hint.
                                ink = ImageColor.getrgb(doc['aButtonUppercaseForegroundStyle']['normalColor'])
                                letter_area = changed.crop((0, round(h * .35 * SCALE), changed.width, round(h * .85 * SCALE)))
                                self.assertTrue(any(max(abs(pixel[i] - ink[i]) for i in range(3)) < 32
                                                    for pixel in letter_area.get_flattened_data()))

    def test_hold_anchor_centers_fit_phone_widths(self):
        from render_hold_preview import hold_geometry, render_hold
        from build_skin import length
        for orientation, widths in (('Portrait', (320, 390, 430)), ('Landscape', (568, 680, 932))):
            for scheme in ('light', 'dark'):
                doc = load('pinyin' + orientation, scheme)
                for width in widths:
                    rects = dict(layout_rectangles(doc, 'keyboardLayout', width, doc['keyboardHeight']))
                    for letter in 'qwertyuiopasdfghjklzxcvbnm':
                        with self.subTest(orientation=orientation, scheme=scheme, width=width, letter=letter):
                            grid, (px, py, pw, ph), (cw, ch) = hold_geometry(doc, letter, width)
                            _, english_panel, english_cell = hold_geometry(doc, letter, width, True)
                            self.assertEqual(english_panel, (px, py, pw, ph))
                            self.assertEqual(english_cell, (cw, ch))
                            self.assertGreaterEqual(px, 0)
                            self.assertLessEqual(px + pw, width + .01)
                            x, y, w, h = rects[letter + 'Button']
                            bounds = doc[letter + 'Button'].get('bounds', {})
                            visible = length(bounds.get('width'), w)
                            if visible is not None:
                                x += w - visible if bounds.get('alignment') == 'right' else 0
                                w = visible
                            self.assertAlmostEqual(px + grid['insets']['left'] + (grid['selected']['col'] + .5) * cw, x + w / 2)
                image = render_hold('f', scheme, orientation, width=widths[1])
                self.assertEqual(image.width, widths[1] * SCALE)

    def test_selected_categories_have_rounded_corners_and_interior_fill(self):
        for scheme in ('light', 'dark'):
            for orientation, width in (('Portrait', 390), ('Landscape', 680)):
                name = 'symbolic' + orientation
                doc = load(name, scheme)
                rects = dict(layout_rectangles(doc, 'keyboardLayout', width, doc['keyboardHeight']))
                x, y, w, h = inset(rects['symbolCategories'], doc['symbolCategories']['insets'])
                y += doc['preeditHeight'] + doc['toolbarHeight']
                row_height = h / doc['symbolCategories']['maximumRow']
                highlight = doc['symbolCategoryHighlight']
                color = ImageColor.getrgb(highlight['highlightColor'])
                for index, category in enumerate(doc['symbolCategoryData']):
                    with self.subTest(scheme=scheme, orientation=orientation, category=category):
                        image = render_keyboard(name, scheme, width=width, category=category)
                        visible_index = min(index, doc['symbolCategories']['maximumRow'] - 1)
                        hx, hy, hw, hh = inset((x, y + row_height * visible_index, w, row_height), highlight['insets'])
                        # A square full-cell highlight would color the top-left corner.
                        self.assertNotEqual(image.getpixel((round(hx * SCALE), round(hy * SCALE))), color)
                        # Just below the top edge, away from text, must be visibly selected.
                        self.assertEqual(image.getpixel((round((hx + hw / 2) * SCALE), round((hy + 1) * SCALE))), color)
                        for other in range(3):
                            if other != visible_index:
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
