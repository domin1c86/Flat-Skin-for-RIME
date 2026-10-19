"""Check native collection data and generate the complete Unicode review document."""
import argparse
import html
import json
from pathlib import Path

from build_skin import ROOT, SKIN, SkinError, require

CATALOG = SKIN / 'jsonnet/Constants/SymbolCatalog.json'
REPORT = ROOT / 'docs/符号面板字符审核.md'
LABELS = ['常用', '中文', '英文', '网络', '数学', '括号', '序号', '特殊', '希腊', '拼音', '注音', '日文']


def load_catalog(path=CATALOG):
    catalog = json.loads(Path(path).read_text(encoding='utf-8'))
    operators = catalog['numericOperators']
    require(len(operators) == 32 and operators.count('\\') == 6,
            'numeric operators must retain all 32 entries and six backslashes')
    require(all(33 <= ord(symbol) <= 126 for symbol in operators), 'numeric operators must be ASCII punctuation')
    categories = catalog['categories']
    require([item['label'] for item in categories] == LABELS, 'incorrect category order')
    require(len({item['id'] for item in categories}) == len(categories), 'duplicate category ID')
    for item in categories:
        values = item['symbols']
        require(isinstance(values, list) and values, f"{item['label']}: empty symbols")
        require(all(isinstance(value, str) and value and not any(char.isspace() for char in value)
                    for value in values), f"{item['label']}: invalid symbol")
        require(len(values) == len(set(values)), f"{item['label']}: duplicate symbol")
        if item['id'] not in ('common', 'internet'):
            require(all(len(value) == 1 for value in values), f"{item['label']}: expected single characters")
    return catalog


def check_skin_catalog(skin=SKIN, catalog=None):
    catalog = load_catalog(skin / 'jsonnet/Constants/SymbolCatalog.json') if catalog is None else catalog
    for theme in ('light', 'dark'):
        for orientation in ('Portrait', 'Landscape'):
            numeric = json.loads((skin / theme / ('numeric' + orientation + '.yaml')).read_text(encoding='utf-8'))
            require(numeric['numericOperatorData'] == list(catalog['numericOperators']), 'numeric data mismatch')
            require(numeric['numericOperators']['maximumRow'] == 4, 'numeric visible rows changed')
            symbolic = json.loads((skin / theme / ('symbolic' + orientation + '.yaml')).read_text(encoding='utf-8'))
            require(symbolic['symbolCategoryData'] == LABELS, 'native category order mismatch')
            require(symbolic['symbolCategories']['maximumRow'] == 3, 'category visible rows changed')
            collection = symbolic['symbolCollection']
            require((collection['maximumRow'], collection['maximumColumn']) == (5, 4), 'symbol grid size changed')
            for category in catalog['categories']:
                expected = [value if len(value) <= 3 else {
                    'label': value, 'value': value, 'styleName': 'symbolShortTextCell',
                } for value in category['symbols']]
                require(symbolic[category['label']] == expected, f"{category['label']}: native output mismatch")
    return 8


def code(value):
    escaped = html.escape(value, quote=False).replace('|', '&#124;').replace('\\', '&#92;').replace('`', '&#96;')
    return '<code>' + escaped + '</code>'


def symbol_rows(values):
    rows = ['| 顺序 | 显示 | 点击输出 | Unicode 码位 |', '| --- | --- | --- | --- |']
    for index, value in enumerate(values, 1):
        points = ' '.join(f'U+{ord(char):04X}' for char in value)
        rows.append(f'| {index} | {code(value)} | {code(value)} | {points} |')
    return rows


def render_report(catalog):
    lines = ['# 符号面板字符审核', '',
             '本表由 `scripts/audit_symbol_catalog.py` 根据共享符号目录生成；显示和点击输出逐项列出，顺序从上到下、从左到右。', '',
             '## 行为与边界', '',
             '- 数字九宫格左列保持四个可见单元格，32项通过上下滑动访问。按用户确认保留原文全部6个反斜杠；重复项输出相同。末尾没有空格，也没有 HTML 空格实体。',
             '- 左侧12类按指定顺序上下滚动，每屏3项；锁定与返回固定。右侧四列五行，通过上下滚动访问更多符号。',
             '- 每类内部无重复；不同类别可以出现相同符号。括号左右分开输入，不自动配对或移动光标。',
             '- 常用保留原有20项静态内容，包含旧有 `.com` 短串；网络类别中的短串整体输入。其他类别每项一个字符。',
             '- **动态最近符号暂缓**：未实现自动记录、重复置顶、持久化或100项淘汰，网页也不模拟已完成这些能力。',
             '- 英文上滑 H/J/M 为 U+0027 单引号、U+0026 与号、U+002F 斜线；中文映射不变，中文 M 仍为 U+0060 反引号。',
             '- 数学负号 `−`（U+2212）不同于数字列及英文的 `-`（U+002D）；全角中文标点不同于英文半角。希腊字母与形似的拉丁字母是不同码位。',
             '- 日文包含小假名、浊音、半浊音、历史假名及重复标记；注音含基础37符号与5个声调标记。字体实际覆盖与手势行为仍需元书实机验收。', '',
             '## 数字列：32项', '', '```text', catalog['numericOperators'], '```', '']
    lines += symbol_rows(catalog['numericOperators'])
    lines += ['', '## 分类总览', '', '| 顺序 | 分类 | 项数 |', '| --- | --- | --- |']
    for index, category in enumerate(catalog['categories'], 1):
        lines.append(f"| {index} | {category['label']} | {len(category['symbols'])} |")
    for category in catalog['categories']:
        lines += ['', f"## {category['label']}：{len(category['symbols'])}项", '']
        lines += symbol_rows(category['symbols'])
    lines += ['', '## 复核方式', '',
              '运行 `python scripts/audit_symbol_catalog.py` 检查明暗色、横竖屏四组数字页与四组符号页的数据及输出，再重新生成本表。', '',
              '配置图和网页仅作核对，不代表 iOS 原生滚动、点击与恢复行为已实测。', '',
              '- [元书集合视图与数据源](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/collection/)', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=REPORT)
    args = parser.parse_args()
    try:
        catalog = load_catalog()
        count = check_skin_catalog(catalog=catalog)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render_report(catalog), encoding='utf-8', newline='\n')
        print(f'Validated {count} numeric/symbolic files; report: {args.output}')
    except (SkinError, OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f'ERROR: {error}\n')


if __name__ == '__main__':
    main()
