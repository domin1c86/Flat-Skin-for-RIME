"""Regression checks for silent blank keys, layout overflow, and skin behavior."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_skin import SkinError, layout_rectangles, validate_document, validate_image_resources, validate_skin


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

    def test_mixed_foreground_array_fails(self):
        self.doc['qButton']['foregroundStyle'] = [
            'qButtonSwipeLabelForegroundStyle',
            {'conditionKey': 'rime$ascii_mode', 'conditionValue': False,
             'styleName': 'qButtonUppercaseForegroundStyle'},
        ]
        with self.assertRaisesRegex(SkinError, 'mixed style reference array'):
            validate_document(self.doc)

    def test_conditional_style_names_are_validated(self):
        for value, message in ((['qButtonSwipeLabelForegroundStyle', 'missingLetter'], 'missing reference'),
                               (['qButtonSwipeLabelForegroundStyle', {}], 'conditional style names')):
            with self.subTest(value=value):
                doc = load('pinyinPortrait')
                doc['qButton']['foregroundStyle'] = [
                    {'conditionKey': 'rime$ascii_mode', 'conditionValue': False, 'styleName': value}]
                with self.assertRaisesRegex(SkinError, message):
                    validate_document(doc)

    def test_missing_swipe_callout_reference_fails(self):
        for direction in ('Up', 'Down'):
            with self.subTest(direction=direction):
                doc = load('pinyinPortrait')
                doc['qButtonHintStyle']['swipe' + direction + 'ForegroundStyle'] = 'missingCallout'
                with self.assertRaisesRegex(SkinError, 'missing reference missingCallout'):
                    validate_document(doc)

    def test_invalid_hold_grid_fails(self):
        for kind in ('reference', 'selection', 'step'):
            with self.subTest(kind=kind):
                doc = load('pinyinPortrait')
                grid = doc[doc['qButton']['hintSymbolsGridStyle']]
                if kind == 'reference':
                    grid['symbolRows'][0][0] = 'missingHoldOption'
                elif kind == 'selection':
                    grid['selected']['col'] = 3
                else:
                    grid['moveStep']['horizontal'] = 0
                with self.assertRaises(SkinError):
                    validate_document(doc)

    def test_missing_hold_list_reference_fails(self):
        doc = load('pinyinPortrait')
        doc[doc['qButton']['hintSymbolsStyle']]['symbolStyles'][0] = 'missingHoldOption'
        with self.assertRaisesRegex(SkinError, 'missing reference missingHoldOption'):
            validate_document(doc)

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

    def test_missing_language_sprite_fails(self):
        self.doc['phoneChineseModeIcon']['normalImage']['image'] = 'missing'
        with self.assertRaisesRegex(SkinError, 'missing sprite'):
            validate_image_resources(self.doc, ROOT / 'default/light/resources')

    def test_stretched_language_image_fails(self):
        self.doc['phoneChineseModeIcon']['contentMode'] = 'scaleToFill'
        with self.assertRaisesRegex(SkinError, 'preserve aspect ratio'):
            validate_image_resources(self.doc, ROOT / 'default/light/resources')


class GeneratedSkinTests(unittest.TestCase):
    def test_phone_preedit_is_smaller_than_candidates(self):
        for scheme in ('light', 'dark'):
            for name in ('pinyin', 'numeric', 'symbolic'):
                for orientation in ('Portrait', 'Landscape'):
                    doc = load(name + orientation, scheme)
                    self.assertEqual(doc['preeditForegroundStyle']['fontSize'], 12)
                    self.assertEqual(doc['horizontalCandidateStyle']['textFontSize'], 16)
                    self.assertEqual(doc['preeditHeight'], 25)
            for name in ('iPadPinyin', 'iPadNumeric'):
                for orientation in ('Portrait', 'Landscape'):
                    doc = load(name + orientation, scheme)
                    self.assertEqual(doc['preeditForegroundStyle']['fontSize'], 17)

    def test_hold_options_order_default_and_literal_actions(self):
        letters = 'qwertyuiopasdfghjklzxcvbnm'
        hints = '1234567890～！＠＃％“”＊？（）－＿：；｀'
        for scheme in ('light', 'dark'):
            for orientation in ('Portrait', 'Landscape'):
                doc = load('pinyin' + orientation, scheme)
                left = 'qwa' if orientation == 'Portrait' else 'q'
                right = 'pol' if orientation == 'Portrait' else 'p'
                for letter, hint in zip(letters, hints):
                    with self.subTest(scheme=scheme, orientation=orientation, letter=letter):
                        node = doc[letter + 'Button']
                        grid = doc[node['hintSymbolsGridStyle']]
                        refs = grid['symbolRows'][0]
                        values = [doc[doc[ref]['foregroundStyle']]['text'] for ref in refs]
                        expected = [hint, letter.upper(), letter] if letter in left else (
                            [letter, letter.upper(), hint] if letter in right else [letter.upper(), hint, letter])
                        self.assertEqual(values, expected)
                        self.assertEqual(grid['selected'], grid['anchor'])
                        self.assertEqual(values[grid['selected']['col']], hint)
                        self.assertEqual(grid['moveStep'], {'horizontal': 24, 'vertical': 44})
                        self.assertEqual(grid['moveThreshold'], 10)
                        self.assertEqual(doc[node['hintSymbolsStyle']]['symbolStyles'], refs)
                        self.assertEqual(doc[node['hintSymbolsStyle']]['selectedIndex'], grid['selected']['col'])
                        for ref, value in zip(refs, values):
                            self.assertEqual(doc[ref]['action'], {'symbol': value})
                            self.assertEqual(doc[ref]['uppercasedStateAction'], {'symbol': value})
                        for notification in node.get('notification', []):
                            notified = doc[notification]
                            state_grid = doc[notified['hintSymbolsGridStyle']]
                            for field in ('size', 'insets', 'anchor', 'selected', 'offset', 'moveStep', 'moveThreshold'):
                                self.assertEqual(state_grid[field], grid[field])
                background = doc['phoneHoldBackground']
                self.assertEqual(background['cornerRadius'], doc['alphabeticButtonBackgroundStyle']['cornerRadius'])
                self.assertNotIn('normalBorderColor', background)
                self.assertGreater(background['shadowOpacity'], 0)
                self.assertGreater(background['shadowRadius'], 0)

    def test_hold_feature_does_not_change_ipad_or_other_pages(self):
        for scheme in ('light', 'dark'):
            for name in ('numericPortrait', 'numericLandscape', 'symbolicPortrait', 'symbolicLandscape',
                         'iPadPinyinPortrait', 'iPadPinyinLandscape', 'iPadNumericPortrait', 'iPadNumericLandscape'):
                doc = load(name, scheme)
                self.assertNotIn('phoneHoldBackground', doc)
                self.assertFalse(any(isinstance(node, dict) and 'hintSymbolsGridStyle' in node for node in doc.values()))

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
                        for style_name, node in doc.items():
                            if isinstance(node, dict) and node.get('buttonStyleType') == 'geometry':
                                self.assertFalse({'normalLowerEdgeColor', 'highlightLowerEdgeColor'} & node.keys())
                                if style_name != 'phoneHoldBackground':
                                    self.assertNotIn('shadowRadius', node)

    def test_twenty_six_hints_survive_uppercase(self):
        letters = 'qwertyuiopasdfghjklzxcvbnm'
        hints = '1234567890～！＠＃％“”＊？（）－＿：；｀'
        english_hints = '1234567890~!@#%""*?()-_:;`'
        for orientation in ('Portrait', 'Landscape'):
            doc = load('pinyin' + orientation)
            for letter, hint in zip(letters, hints):
                node = doc[letter + 'Button']
                self.assertEqual(next(iter(node['swipeUpAction'].values())), hint)
                for field in ('foregroundStyle', 'uppercasedStateForegroundStyle'):
                    for english in (False, True):
                        refs = selected_styles(node[field], {'rime$ascii_mode': english})
                        expected_hint = english_hints[letters.index(letter)] if english else hint
                        self.assertIn(expected_hint, [doc[name]['text'] for name in refs])
                        expected_letter = letter.upper() if not english or field == 'uppercasedStateForegroundStyle' else letter
                        self.assertIn(expected_letter, [doc[name]['text'] for name in refs])
                for index, ref in enumerate(node['notification']):
                    notification = doc[ref]
                    self.assertEqual(notification['rimeOptionValue'], bool(index))
                    # Native replacements must retain every geometry/interaction field.
                    for key, value in node.items():
                        if key not in ('notification', 'foregroundStyle', 'uppercasedStateForegroundStyle',
                                       'capsLockedStateForegroundStyle', 'swipeUpAction', 'hintStyle',
                                       'hintSymbolsGridStyle', 'hintSymbolsStyle'):
                            self.assertEqual(notification[key], value)
                    self.assertNotIn('notification', notification)
                self.assertEqual(node['action'], {'character': letter})
                self.assertEqual(node['uppercasedStateAction'], {'character': letter.upper()})

    def test_swipe_callouts_match_all_twenty_six_actions(self):
        for scheme in ('light', 'dark'):
            for orientation in ('Portrait', 'Landscape'):
                doc = load('pinyin' + orientation, scheme)
                for letter in 'qwertyuiopasdfghjklzxcvbnm':
                    with self.subTest(scheme=scheme, orientation=orientation, letter=letter):
                        node = doc[letter + 'Button']
                        callout = doc[node['hintStyle']]
                        swipe = doc[selected_styles(callout['swipeUpForegroundStyle'], {'rime$ascii_mode': False})[0]]
                        normal = doc[selected_styles(callout['foregroundStyle'], {'rime$ascii_mode': False})[0]]
                        self.assertEqual(swipe['buttonStyleType'], 'text')
                        self.assertEqual(swipe['text'], next(iter(node['swipeUpAction'].values())))
                        self.assertEqual(normal['text'], letter.upper())
                        self.assertEqual(swipe['fontSize'], normal['fontSize'])
                        self.assertEqual(swipe['normalColor'], normal['normalColor'])
                        for notification in node.get('notification', []):
                            notified = doc[notification]
                            hint = doc[notified['hintStyle']]
                            self.assertEqual(doc[hint['swipeUpForegroundStyle']]['text'], notified['swipeUpAction']['symbol'])

    def test_bubbles_and_symbol_actions_follow_language_and_case(self):
        catalog = json.loads((ROOT / 'default/jsonnet/Constants/LetterSymbols.json').read_text(encoding='utf-8'))
        for scheme in ('light', 'dark'):
            for orientation in ('Portrait', 'Landscape'):
                doc = load('pinyin' + orientation, scheme)
                for i, letter in enumerate(catalog['letters']):
                    base = doc[letter + 'Button']
                    for english in (False, True):
                        symbol = catalog['english' if english else 'chinese'][i]
                        notified = doc[base['notification'][int(english)]]
                        for node in (base, notified):
                            hint = doc[node['hintStyle']]
                            # Initial conditional bubble and notified fixed bubble agree.
                            self.assertEqual(doc[selected_styles(hint['swipeUpForegroundStyle'], {'rime$ascii_mode': english})[0]]['text'], symbol)
                            for field in ('foregroundStyle', 'uppercasedStateForegroundStyle', 'capsLockedStateForegroundStyle'):
                                expected = letter if english and field == 'foregroundStyle' else letter.upper()
                                ref = selected_styles(hint[field], {'rime$ascii_mode': english})[0]
                                self.assertEqual(doc[ref]['text'], expected)
                            self.assertEqual(hint['backgroundStyle'], doc[base['hintStyle']]['backgroundStyle'])
                            self.assertEqual(hint['size'], doc[base['hintStyle']]['size'])
                        self.assertEqual(notified['swipeUpAction'], {'symbol': symbol})
                        grid = doc[notified['hintSymbolsGridStyle']]
                        option = doc[grid['symbolRows'][0][grid['selected']['col']]]
                        self.assertEqual(option['action'], {'symbol': symbol})
                        self.assertEqual(option['uppercasedStateAction'], option['action'])
                        self.assertEqual(doc[option['foregroundStyle']]['text'], symbol)
                        self.assertEqual(doc[notified['hintSymbolsStyle']]['symbolStyles'], grid['symbolRows'][0])
                        actual = []
                        for ref in grid['symbolRows'][0]:
                            item = doc[ref]
                            label = doc[item['foregroundStyle']]['text']
                            actual.append(label)
                            self.assertEqual(item['action'], {'symbol': label})
                            self.assertEqual(item['uppercasedStateAction'], {'symbol': label})
                        self.assertCountEqual(actual, [letter.upper(), symbol, letter])
                        self.assertEqual(notified.get('bounds'), base.get('bounds'))

    def test_symbol_mapping_matches_offline_preview(self):
        import re
        catalog = json.loads((ROOT / 'default/jsonnet/Constants/LetterSymbols.json').read_text(encoding='utf-8'))
        self.assertEqual(catalog['letters'], 'qwertyuiopasdfghjklzxcvbnm')
        self.assertEqual(catalog['chinese'], '1234567890～！＠＃％“”＊？（）－＿：；｀')
        self.assertEqual(catalog['english'], '1234567890~!@#%""*?()-_:;`')
        html = (ROOT / 'preview/index.html').read_text(encoding='utf-8')
        declaration = re.search(r'const letterSymbols = (.*);', html).group(1)
        self.assertEqual(json.loads(declaration), catalog)

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
        for scheme in ('light', 'dark'):
            for orientation in ('Portrait', 'Landscape'):
                doc = load('pinyin' + orientation, scheme)
                for english in (False, True):
                    refs = selected_styles(doc['asciiModeButton']['foregroundStyle'], {'rime$ascii_mode': english})
                    self.assertEqual(len(refs), 1)
                    icon = doc[refs[0]]
                    self.assertEqual(icon['buttonStyleType'], 'fileImage')
                    self.assertEqual(icon['contentMode'], 'scaleAspectFit')
                    self.assertEqual(icon['normalImage'], {'file': 'language', 'image': 'english' if english else 'chinese'})
                    self.assertEqual(icon['highlightImage'], icon['normalImage'])
                    self.assertEqual(icon['insets']['top'], 15.4 if orientation == 'Portrait' else 9.8)
                    self.assertEqual(icon['insets']['top'], icon['insets']['bottom'])
                    self.assertEqual(doc['phoneAsciiNotification']['foregroundStyle'], doc['asciiModeButton']['foregroundStyle'])
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

    def test_chinese_punctuation_uses_centered_artwork_with_original_actions(self):
        for scheme in ('light', 'dark'):
            for orientation in ('Portrait', 'Landscape'):
                doc = load('pinyin' + orientation, scheme)
                for key, image, character, english in (
                    ('chineseCommaButton', 'comma', '，', ','),
                    ('chinesePeriodButton', 'period', '。', '.'),
                ):
                    node = doc[key]
                    self.assertEqual(node['action'], {'symbol': character})
                    cn = doc[selected_styles(node['foregroundStyle'], {'rime$ascii_mode': False})[0]]
                    self.assertEqual(cn['buttonStyleType'], 'fileImage')
                    self.assertEqual(cn['normalImage'], {'file': 'punctuation', 'image': image})
                    self.assertEqual(cn['normalImage'], cn['highlightImage'])
                    self.assertEqual(cn['contentMode'], 'scaleAspectFit')
                    drop = 28 / 3 if image == 'comma' else 8.5
                    self.assertAlmostEqual((cn['insets']['top'] - cn['insets']['bottom']) / 2, drop)
                    self.assertEqual(cn['insets']['left'], cn['insets']['right'])
                    en = doc[selected_styles(node['foregroundStyle'], {'rime$ascii_mode': True})[0]]
                    self.assertEqual(en['text'], english)
                    self.assertEqual(doc[node['notification'][0]]['action'], {'symbol': english})
            self.assertEqual(doc['phoneReturnPreeditNotification']['backgroundStyle'], 'blueButtonBackgroundStyle')

    def test_toolbar_actions_are_real_entrances(self):
        doc = load('pinyinPortrait')
        self.assertEqual(doc['toolbarEmojiButton']['action'], {'keyboardType': 'emojis'})
        self.assertEqual(doc['toolbarPasteboardButton']['action'], {'shortcut': '#showPasteboardView'})
        self.assertNotIn('toolbarScriptButton', doc)

    def test_main_toolbar_order_actions_and_small_width(self):
        expected = ['toolbarMenuButton', 'toolbarSpacer', 'toolbarSymbolicButton', 'toolbarEmojiButton',
                    'toolbarPasteboardButton', 'toolbarSchemaButton']
        for scheme in ('light', 'dark'):
            for orientation in ('Portrait', 'Landscape'):
                doc = load('pinyin' + orientation, scheme)
                self.assertEqual([node['Cell'] for node in doc['toolbarLayout'][0]['HStack']['subviews']], expected)
                self.assertEqual(doc['toolbarSymbolicButton']['action'], {'keyboardType': 'symbolic'})
                self.assertEqual(doc['toolbarSchemaButton']['action'], {'shortcut': '#方案切换'})
                self.assertEqual(doc[doc['toolbarSymbolicButton']['foregroundStyle']]['systemImageName'], 'number')
                self.assertEqual(doc[doc['toolbarSchemaButton']['foregroundStyle']]['systemImageName'], 'arrow.triangle.2.circlepath')
                self.assertNotIn('toolbarDismissButton', doc)
                for name in expected:
                    if name != 'toolbarSpacer':
                        self.assertEqual(doc[name]['size']['width'], 38)
                for width in (320, 390, 430, 568, 680, 844):
                    rects = dict(layout_rectangles(doc, 'toolbarLayout', width - 18, doc['toolbarHeight']))
                    self.assertGreater(rects['toolbarSpacer'][2], 0)

    def test_secondary_and_ipad_toolbars_keep_existing_buttons(self):
        for scheme in ('light', 'dark'):
            for name in ('numericPortrait', 'numericLandscape', 'symbolicPortrait', 'symbolicLandscape'):
                doc = load(name, scheme)
                self.assertEqual([node['Cell'] for node in doc['toolbarLayout'][0]['HStack']['subviews']], [
                    'toolbarMenuButton', 'toolbarSpacer', 'toolbarEmojiButton', 'toolbarPasteboardButton',
                    'toolbarScriptButton', 'toolbarDismissButton'
                ])
                self.assertEqual(doc['toolbarDismissButton']['action'], 'dismissKeyboard')
                self.assertNotIn('toolbarSchemaButton', doc)
                self.assertNotIn('toolbarSymbolicButton', doc)
            for name in ('iPadPinyinPortrait', 'iPadPinyinLandscape', 'iPadNumericPortrait', 'iPadNumericLandscape'):
                doc = load(name, scheme)
                self.assertEqual([node['Cell'] for node in doc['toolbarLayout'][0]['HStack']['subviews']], [
                    'toolbarMenuButton', 'toolbarSplitToggleButton', 'toolbarSpacer', 'toolbarDismissButton'
                ])
                self.assertNotIn('toolbarSchemaButton', doc)
                self.assertNotIn('toolbarSymbolicButton', doc)


if __name__ == '__main__':
    unittest.main()
