"""Exact output, ordering, uniqueness, and Unicode coverage of scrollable lists."""
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audit_symbol_catalog import REPORT, check_skin_catalog, load_catalog, render_report
from build_skin import SkinError


class SymbolCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog()
        self.categories = {item['label']: item['symbols'] for item in self.catalog['categories']}

    def test_numeric_sequence_preserves_all_literal_backslashes(self):
        expected = r'+-\*/%:#=<>;()[]{}&|\\^\_\~\`@?!'
        self.assertEqual(self.catalog['numericOperators'], expected)
        self.assertEqual(len(expected), 32)
        self.assertEqual([index for index, value in enumerate(expected, 1) if value == '\\'], [3, 21, 22, 24, 26, 28])
        self.assertFalse(any(value.isspace() for value in expected))

    def test_static_common_list_is_unchanged(self):
        self.assertEqual(self.categories['常用'], ['《', '，', '。', '？', '！', '、', '…', '(', ')', '》', '“', '”', '@', '#', '.', '/', '.com', '~', '—', ':'])

    def test_ascii_punctuation_and_independent_unicode_ranges(self):
        english = [chr(point) for start, end in ((0x21, 0x2f), (0x3a, 0x40), (0x5b, 0x60), (0x7b, 0x7e))
                   for point in range(start, end + 1)]
        self.assertEqual(self.categories['英文'], english)
        japanese = [chr(point) for start, end in ((0x3041, 0x3096), (0x30a1, 0x30fa))
                    for point in range(start, end + 1)] + list('ーゝゞヽヾ')
        self.assertEqual(self.categories['日文'], japanese)
        self.assertEqual(self.categories['注音'], [chr(point) for point in range(0x3105, 0x312a)] + list('ˉˊˇˋ˙'))
        numbers = [chr(point) for start, end in ((0x2460, 0x2473), (0x2474, 0x2487),
                   (0x3220, 0x3229), (0x2160, 0x216b), (0x2170, 0x217b)) for point in range(start, end + 1)]
        self.assertEqual(self.categories['序号'], numbers)
        self.assertEqual(''.join(self.categories['希腊']), 'ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩαβγδεζηθικλμνξοπρστυφχψως')
        self.assertEqual(''.join(self.categories['拼音']), 'aāáǎàeēéěèiīíǐìoōóǒòuūúǔùüǖǘǚǜnńňǹmḿê')

    def test_native_and_offline_catalogs_match(self):
        self.assertEqual(check_skin_catalog(), 8)
        source = (ROOT / 'preview/index.html').read_text(encoding='utf-8')
        embedded = json.loads(re.search(r'const symbolCatalog = (.*);', source).group(1))
        self.assertEqual(embedded, self.catalog)

    def test_duplicate_or_blank_category_symbols_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'catalog.json'
            for value in (' ', '，'):
                catalog = deepcopy(self.catalog)
                catalog['categories'][0]['symbols'].append(value)
                path.write_text(json.dumps(catalog, ensure_ascii=False), encoding='utf-8')
                with self.assertRaises(SkinError):
                    load_catalog(path)

    def test_review_document_matches_source_and_escapes_table_delimiters(self):
        report = render_report(self.catalog)
        self.assertEqual(REPORT.read_text(encoding='utf-8'), report)
        self.assertIn('<code>&#124;</code>', report)
        self.assertIn('<code>&#92;</code>', report)
        self.assertIn('<code>&#96;</code>', report)
        self.assertIn('动态最近符号暂缓', report)
        for category in self.catalog['categories']:
            self.assertIn(f"## {category['label']}：{len(category['symbols'])}项", report)


if __name__ == '__main__':
    unittest.main()
