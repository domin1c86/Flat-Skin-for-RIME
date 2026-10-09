"""Pixel regressions for the native classification highlight's rounded inset."""
import importlib.util
from pathlib import Path
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


if __name__ == '__main__':
    unittest.main()
