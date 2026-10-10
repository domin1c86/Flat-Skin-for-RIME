"""Embed the native symbol catalog into the offline, single-file preview."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def sync():
    catalog = json.loads((ROOT / 'default/jsonnet/Constants/LetterSymbols.json').read_text(encoding='utf-8'))
    assert all(len(catalog[name]) == 26 for name in ('letters', 'chinese', 'english'))
    path = ROOT / 'preview/index.html'
    source = path.read_text(encoding='utf-8')
    declaration = 'const letterSymbols = ' + json.dumps(catalog, ensure_ascii=False) + ';'
    result, count = re.subn(r'const letterSymbols = [^\n]*;', lambda _: declaration, source, count=1)
    if count != 1:
        raise ValueError('Missing preview symbol catalog declaration')
    path.write_text(result, encoding='utf-8', newline='\n')


if __name__ == '__main__':
    sync()
    print('Embedded native symbol catalog into preview/index.html')
