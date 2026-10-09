"""Regression checks for silent blank keys, layout overflow, and skin behavior."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_skin import SkinError, layout_rectangles, validate_document, validate_skin


def load(name, scheme='light'):
    return json.loads((ROOT / 'default' / scheme / (name + '.yaml')).read_text(encoding='utf-8'))


def selected_styles(value, conditions):
    if isinstance(value, str):
        return [value]
    result = []
    for item in value:
        if isinstance(item, str):
            result.append(item)
        elif conditions[item['conditionKey']] == item['conditionValue'] or (
            isinstance(item['conditionValue'], list) and conditions[item['conditionKey']] in item['conditionValue']
        ):
            name = item['styleName']
            result.extend([name] if isinstance(name, str) else name)
    return result


class ValidatorRegressionTests(unittest.TestCase):
    def setUp(self):
        self.doc = load('pinyinPortrait')

    def test_missing_reference_fails(self):
        self.doc['qButton']['foregroundStyle'] = 'typo'
        with self.assertRaisesRegex(SkinError, 'missing reference typo'):
            validate_document(self.doc)

    def test_invalid_color_fails(self):
        self.doc['alphabeticButtonBackgroundStyle']['normalColor'] = '#fff'
        with self.assertRaisesRegex(SkinError, 'invalid color'):
            validate_document(self.doc)

    def test_mixed_layout_fails(self):
        self.doc['keyboardLayout'].append({'Cell': 'qButton'})
        with self.assertRaisesRegex(SkinError, 'mixed/unknown'):
            validate_document(self.doc)

    def test_overflow_fails(self):
        self.doc['qButton']['size']['width'] = '9/10'
        with self.assertRaisesRegex(SkinError, 'overflow'):
            validate_document(self.doc)

    def test_incomplete_widths_fail(self):
        self.doc['qButton']['size']['width'] = '1/20'
        with self.assertRaisesRegex(SkinError, 'unused'):
            validate_document(self.doc)

    def test_unknown_action_fails(self):
        self.doc['qButton']['action'] = 'inventedAction'
        with self.assertRaisesRegex(SkinError, 'unknown action'):
            validate_document(self.doc)

    def test_missing_category_data_fails(self):
        doc = load('symbolicPortrait')
        del doc['中文']
        with self.assertRaisesRegex(SkinError, 'has no symbols'):
            validate_document(doc)


class GeneratedSkinTests(unittest.TestCase):
    def test_all_device_mappings_and_split_layouts(self):
        self.assertEqual(validate_skin(), 20)

    def test_all_phone_pages_use_selected_palette_without_edges(self):
        expected = {
            'light': ('#E4E5E7', '#FFFFFF', '#CFD0D2', '#007AFF'),
            'dark': ('#1B1C1F', '#37383C', '#292A2E', '#0A84FF'),
        }
        for scheme, palette in expected.items():
            for name in ('pinyin', 'numeric', 'symbolic'):
                for orientation in ('Portrait', 'Landscape'):
                    with self.subTest(scheme=scheme, name=name, orientation=orientation):
                        doc = load(name + orientation, scheme)
                        actual = tuple(doc[key]['normalColor'] for key in (
                            'keyboardBackgroundStyle', 'alphabeticButtonBackgroundStyle',
                            'systemButtonBackgroundStyle', 'blueButtonBackgroundStyle'
                        )) if name != 'symbolic' else tuple(doc[key]['normalColor'] for key in (
                            'keyboardBackgroundStyle', 'alphabeticButtonBackgroundStyle', 'systemButtonBackgroundStyle'
                        ))
                        self.assertEqual(actual, palette if name != 'symbolic' else palette[:3])
                        for node in doc.values():
                            if isinstance(node, dict) and node.get('buttonStyleType') == 'geometry':
                                self.assertFalse({'normalLowerEdgeColor', 'highlightLowerEdgeColor', 'shadowRadius'} & node.keys())

    def test_twenty_six_hints_survive_uppercase(self):
        letters = 'qwertyuiopasdfghjklzxcvbnm'
        hints = '1234567890~!@#%“”*?()-_:;`'
        for orientation in ('Portrait', 'Landscape'):
            doc = load('pinyin' + orientation)
            for letter, hint in zip(letters, hints):
                node = doc[letter + 'Button']
                self.assertEqual(next(iter(node['swipeUpAction'].values())), hint)
                for field in ('foregroundStyle', 'uppercasedStateForegroundStyle'):
                    self.assertIn(hint, [doc[name]['text'] for name in node[field]])
                self.assertEqual(node['action'], {'character': letter})
                self.assertEqual(node['uppercasedStateAction'], {'character': letter.upper()})

    def test_function_row_order(self):
        doc = load('pinyinPortrait')
        self.assertEqual([node['Cell'] for node in doc['keyboardLayout'][-1]['HStack']['subviews']], [
            'symbolicButton', 'numericButton', 'chineseCommaButton', 'spaceButton',
            'chinesePeriodButton', 'asciiModeButton', 'enterButton'
        ])

    def test_numeric_key_positions_and_operator_data(self):
        for orientation in ('Portrait', 'Landscape'):
            doc = load('numeric' + orientation)
            rects = dict(layout_rectangles(doc, 'keyboardLayout', 390, doc['keyboardHeight']))
            self.assertLess(rects['oneButton'][0], rects['twoButton'][0])
            self.assertLess(rects['twoButton'][0], rects['threeButton'][0])
            self.assertLess(rects['oneButton'][1], rects['fourButton'][1])
            self.assertLess(rects['fourButton'][1], rects['sevenButton'][1])
            self.assertEqual(rects['oneButton'][0], rects['fourButton'][0])
            self.assertAlmostEqual(rects['twoButton'][0], rects['zeroButton'][0])
            self.assertEqual(doc['numericOperatorData'], ['+', '-', '*', '/'])
            self.assertEqual(doc['pinyinButton']['action'], 'returnPrimaryKeyboard')

    def test_symbol_category_grid_and_lock(self):
        doc = load('symbolicPortrait')
        self.assertEqual(doc['symbolCategories']['maximumRow'], 3)
        self.assertEqual((doc['symbolCollection']['maximumRow'], doc['symbolCollection']['maximumColumn']), (5, 4))
        for category in doc['symbolCategoryData']:
            self.assertEqual(len(doc[category]), 20)
        self.assertEqual(doc['symbolLockButton']['action'], 'symbolicKeyboardLockStateToggle')
        for locked, name in ((False, 'lock.open'), (True, 'lock')):
            refs = selected_styles(doc['symbolLockButton']['foregroundStyle'], {'$symbolicKeyboardLockState': locked})
            self.assertEqual(doc[refs[0]]['systemImageName'], name)
        self.assertEqual(doc['symbolReturnButton']['action'], 'returnLastKeyboard')

    def test_language_initial_states_and_notifications(self):
        doc = load('pinyinPortrait')
        for english, text in ((False, '中'), (True, '英')):
            refs = selected_styles(doc['asciiModeButton']['foregroundStyle'], {'rime$ascii_mode': english})
            self.assertEqual(doc[refs[0]]['text'], text)
        self.assertEqual(doc['phoneAsciiNotification']['rimeOptionName'], 'ascii_mode')
        self.assertEqual(doc['phoneCommaNotification']['action'], {'symbol': ','})
        self.assertEqual(doc['phonePeriodNotification']['action'], {'symbol': '.'})

    def test_enter_styles_cover_all_system_return_types(self):
        for page in ('pinyin', 'numeric'):
            doc = load(page + 'Portrait')
            for return_type in range(12):
                refs = selected_styles(doc['enterButton']['foregroundStyle'], {'$returnKeyType': return_type})
                self.assertEqual(len(refs), 1)
                self.assertEqual(doc[refs[0]]['normalColor'], '#FFFFFF')
            self.assertEqual(doc['enterButton']['backgroundStyle'], 'blueButtonBackgroundStyle')
            self.assertEqual(doc['phoneReturnPreeditNotification']['backgroundStyle'], 'blueButtonBackgroundStyle')

    def test_toolbar_actions_are_real_entrances(self):
        doc = load('pinyinPortrait')
        self.assertEqual(doc['toolbarEmojiButton']['action'], {'keyboardType': 'emojis'})
        self.assertEqual(doc['toolbarPasteboardButton']['action'], {'shortcut': '#showPasteboardView'})
        self.assertEqual(doc['toolbarScriptButton']['action'], {'shortcut': '#toggleScriptView'})


if __name__ == '__main__':
    unittest.main()
