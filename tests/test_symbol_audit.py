"""The audit must expose initialization gaps, not silently mark them as passed."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audit_letter_symbols import EXPECTED, inspect_letter, inspect_punctuation, audit_documents


class SymbolAuditTests(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads((ROOT / 'default/light/pinyinPortrait.yaml').read_text(encoding='utf-8'))
        self.en = json.loads((ROOT / 'default/light/alphabeticPortrait.yaml').read_text(encoding='utf-8'))

    def test_initial_english_actions_are_not_hidden_by_correct_labels(self):
        doc = deepcopy(self.en)
        doc['fButton']['swipeUpAction'] = {'symbol': '\uff03'}
        failures = inspect_letter(doc, 'f', True)
        self.assertNotIn('键面上标', failures)
        self.assertNotIn('上滑气泡', failures)
        self.assertEqual(failures['上滑动作']['actual'], {'symbol': '\uff03'})
        self.assertEqual(failures['上滑动作']['expected'], {'symbol': '#'})
        self.assertNotIn('长按符号动作', failures)
        self.assertNotIn('旧版长按列表', failures)

    def test_all_notification_symbols_match_independent_unicode_oracle(self):
        for english in (False, True):
            for letter in EXPECTED:
                for shift, caps in ((False, False), (True, False), (False, True)):
                    with self.subTest(letter=letter, english=english, shift=shift, caps=caps):
                        doc = self.en if english else self.doc
                        for option in (False, True):
                            self.assertEqual(inspect_letter(doc, letter, english, True, shift, caps, option), {})

    def test_equal_digits_are_not_falsely_flagged(self):
        for letter in 'qwertyuiop':
            self.assertEqual(inspect_letter(self.en, letter, True), {})

    def test_initial_punctuation_gap_and_notification_recovery(self):
        self.assertEqual(inspect_punctuation(self.en, True), {})
        self.assertEqual(inspect_punctuation(self.doc, False), {})
        self.assertEqual(inspect_punctuation(self.en, True, True), {})
        doc = deepcopy(self.en)
        doc['chineseCommaButton']['action'] = {'symbol': '，'}
        self.assertEqual(set(inspect_punctuation(doc, True)), {'chineseCommaButton'})

    def test_wrong_ascii_quotes_are_detected_on_each_route(self):
        for letter in 'hj':
            for route in ('hint', 'swipe', 'hold', 'upper_hold'):
                doc = deepcopy(self.en)
                node = doc[letter + 'Button']
                if route == 'hint':
                    doc[node['foregroundStyle'][0]]['text'] = '\u201d'
                    field = '键面上标'
                elif route == 'swipe':
                    node['swipeUpAction'] = {'symbol': '\u201d'}
                    field = '上滑动作'
                else:
                    grid = doc[node['hintSymbolsGridStyle']]
                    item = doc[grid['symbolRows'][0][grid['selected']['col']]]
                    item['uppercasedStateAction' if route == 'upper_hold' else 'action'] = {'symbol': '\u201d'}
                    field = '长按大写态符号动作' if route == 'upper_hold' else '长按符号动作'
                self.assertIn(field, inspect_letter(doc, letter, True, True))

    def test_matrix_separates_initial_and_notified_results(self):
        result = audit_documents({'light/pinyinPortrait.yaml': self.doc, 'light/alphabeticPortrait.yaml': self.en})
        self.assertEqual(len(result['letters']), 624)
        self.assertEqual(sum(bool(row['failures']) for row in result['letters']), 0)
        self.assertTrue(all(not row['failures'] for row in result['letters'] if row['notified']))
        self.assertTrue(all(not row['failures'] for row in result['cycles']))
        self.assertEqual(len(result['english_schema']), 78)
        self.assertEqual(sum(bool(row['failures']) for row in result['english_schema']), 0)


if __name__ == '__main__':
    unittest.main()
