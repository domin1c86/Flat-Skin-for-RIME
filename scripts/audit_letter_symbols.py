"""Audit compiled symbol routes independently of the shared catalog.

Initial nodes and option-notification replacements are deliberately separate.
Each language selects its own complete file. This checks configuration only.
Exit 1 when unresolved mismatches remain; always write the requested report.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re
import zipfile

from build_skin import ROOT, SKIN, validate_skin
from render_skin_preview import effective_button, selected, button_foreground
from rime_skin_actions import semantic_action, semantic_document

# Independent, explicit Unicode oracle from the approved requirements, rather
# than using LetterSymbols.json as both the implementation and the expectation.
EXPECTED = {
    **{key: (str(index % 10), str(index % 10))
       for index, key in enumerate('qwertyuiop', 1)},
    'a': ('\uff5e', '~'), 's': ('\uff01', '!'), 'd': ('\uff20', '@'),
    'f': ('\uff03', '#'), 'g': ('\uff05', '%'),
    'h': ('\u201c', '"'), 'j': ('\u201d', '"'),
    'k': ('\uff0a', '*'), 'l': ('\uff1f', '?'),
    'z': ('\uff08', '('), 'x': ('\uff09', ')'),
    'c': ('\uff0d', '-'), 'v': ('\uff3f', '_'),
    'b': ('\uff1a', ':'), 'n': ('\uff1b', ';'), 'm': ('\uff40', '\x60'),
}
CASE_STATES = [('普通', False, False), ('Shift', True, False), ('大写锁定', False, True)]
COMPONENTS = ('键面上标', '上滑气泡', '上滑动作', '长按符号显示',
              '长按符号动作', '长按大写态符号动作', '旧版长按列表', '普通气泡', '长按字母选项', '键面区域')


def texts(doc, refs, english):
    return [doc[ref].get('text') for ref in selected(refs, english)]


def inspect_letter(doc, letter, english, notified=False, shift=False, caps=False, option_english=None):
    doc = semantic_document(doc)
    option_english = english if option_english is None else option_english
    base = doc[letter + 'Button']
    node = effective_button(doc, base, option_english, notified)
    symbol = EXPECTED[letter][int(english)]
    hint = doc[node['hintStyle']]
    grid = doc[node['hintSymbolsGridStyle']]
    refs = grid['symbolRows'][grid['selected']['row']]
    option = doc[refs[grid['selected']['col']]]
    fallback = doc[node['hintSymbolsStyle']]
    fallback_refs = fallback['symbolStyles']
    fallback_option = doc[fallback_refs[fallback['selectedIndex']]]
    ordinary = letter.upper() if not english or shift or caps else letter
    chosen = sorted(((doc[ref]['action'], doc[ref].get('uppercasedStateAction'),
                      texts(doc, doc[ref]['foregroundStyle'], option_english)) for ref in refs
                     if doc[ref]['action'].get('symbol') in (letter, letter.upper())),
                    key=lambda item: item[0]['symbol'])
    expected_chosen = sorted((({'symbol': value}, {'symbol': value}, [value])
                              for value in (letter, letter.upper())), key=lambda item: item[0]['symbol'])
    actual = {
        '键面上标': texts(doc, button_foreground(node, shift, caps), option_english)[0],
        '上滑气泡': texts(doc, hint['swipeUpForegroundStyle'], option_english),
        '上滑动作': node.get('swipeUpAction'),
        '长按符号显示': texts(doc, option['foregroundStyle'], option_english),
        '长按符号动作': option.get('action'),
        '长按大写态符号动作': option.get('uppercasedStateAction'),
        '旧版长按列表': (fallback_refs == refs, fallback['selectedIndex'] == grid['selected']['col'],
                         fallback_option.get('action'), texts(doc, fallback_option['foregroundStyle'], option_english)),
        '普通气泡': texts(doc, button_foreground(hint, shift, caps), option_english),
        '长按字母选项': chosen,
        '键面区域': (node.get('bounds'), node.get('size'), node.get('backgroundStyle')),
    }
    expected = {
        '键面上标': symbol, '上滑气泡': [symbol], '上滑动作': {'symbol': symbol},
        '长按符号显示': [symbol], '长按符号动作': {'symbol': symbol},
        '长按大写态符号动作': {'symbol': symbol},
        '旧版长按列表': (True, True, {'symbol': symbol}, [symbol]),
        '普通气泡': [ordinary], '长按字母选项': expected_chosen,
        '键面区域': (base.get('bounds'), base.get('size'), base.get('backgroundStyle')),
    }
    return {name: {'actual': actual[name], 'expected': expected[name]}
            for name in COMPONENTS if actual[name] != expected[name]}


def inspect_punctuation(doc, english, notified=False):
    failures = {}
    for name, values in [('chineseCommaButton', ('\uff0c', ',')),
                         ('chinesePeriodButton', ('\u3002', '.'))]:
        node = effective_button(doc, doc[name], english, notified)
        expected = {'symbol': values[int(english)]}
        if semantic_action(node.get('action')) != expected:
            failures[name] = {'actual': node.get('action'), 'expected': expected}
    return failures


def audit_documents(documents):
    rows, punctuation, cycles, english_schema = [], [], [], []
    for filename, doc in documents.items():
        english = '/alphabetic' in filename
        for notified in (False, True):
            for option in (False, True):
                for case, shift, caps in CASE_STATES:
                    for letter in EXPECTED:
                        rows.append(dict(file=filename, letter=letter, english=english, notified=notified,
                            option=option, case=case, failures=inspect_letter(doc, letter, english, notified, shift, caps, option)))
                    punctuation.append(dict(file=filename, english=english, notified=notified, option=option,
                        case=case, failures=inspect_punctuation(doc, english, notified)))
        if english:
            for case, shift, caps in CASE_STATES:
                for letter in EXPECTED:
                    english_schema.append(dict(file=filename, letter=letter, case=case,
                        failures=inspect_letter(doc, letter, True, False, shift, caps, option_english=False)))
    # Explicit primary-file transitions. This does not simulate the iOS dispatcher.
    for theme in ('light', 'dark'):
        for orientation in ('Portrait', 'Landscape'):
            names = [f'{theme}/{kind}{orientation}.yaml' for kind in ('pinyin', 'alphabetic')]
            if not all(name in documents for name in names):
                continue
            for sequence in ((False, True, False), (True, False, True)):
                for step, english in enumerate(sequence):
                    doc = documents[names[int(english)]]
                    for case, shift, caps in CASE_STATES:
                        for letter in EXPECTED:
                            cycles.append(dict(sequence=sequence, step=step, case=case, letter=letter,
                                failures=inspect_letter(doc, letter, english, False, shift, caps, option_english=False)))
    return dict(letters=rows, punctuation=punctuation, cycles=cycles, english_schema=english_schema)


def code(value):
    return '<code>' + value.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') + '</code>'


def unicode_label(value):
    return code(value) + ' ' + ' '.join(f'U+{ord(char):04X}' for char in value)


def inspect_routes(config, routes):
    failures = []
    for theme in ('light', 'dark'):
        for orientation in ('portrait', 'landscape'):
            for kind in ('pinyin', 'alphabetic'):
                name=config[kind]['iPhone'][orientation]
                doc=json.loads((SKIN/theme/(name+'.yaml')).read_text(encoding='utf-8'))
                expected={'combine':[{'keyboardType':'alphabetic' if kind=='pinyin' else 'pinyin'}, {'sendKeys':routes['toggleKeys']}]}
                if semantic_action(doc['asciiModeButton']['action']) != expected:
                    failures.append(f'{theme}/{name}: language route')
                if semantic_action(doc['toolbarSchemaButton']['action']) != {'keyboardType':'skinSchemes'}:
                    failures.append(f'{theme}/{name}: scheme panel route')
            name=config['skinSchemes']['iPhone'][orientation]
            doc=json.loads((SKIN/theme/(name+'.yaml')).read_text(encoding='utf-8'))
            for item in routes['schemes']:
                expected={'combine':[{'keyboardType':'alphabetic' if item['language']=='en' else 'pinyin'}, {'switchRimeSchema':item['id']}]}
                if semantic_action(doc['scheme'+item['id']]['action']) != expected:
                    failures.append(f'{theme}/{name}: {item["id"]}')
            if semantic_action(doc['schemeBack']['action']) != 'returnLastKeyboard':
                failures.append(f'{theme}/{name}: scheme cancel return')
            for kind, button, action in [('numeric','pinyinButton','returnPrimaryKeyboard'),
                                         ('symbolic','symbolReturnButton','returnLastKeyboard')]:
                doc=json.loads((SKIN/theme/(config[kind]['iPhone'][orientation]+'.yaml')).read_text(encoding='utf-8'))
                if semantic_action(doc[button]['action']) != action:
                    failures.append(f'{theme}/{kind}: return action')
    return failures


def write_report(result, documents, output):
    config=json.loads((SKIN/'config.yaml').read_text(encoding='utf-8'))
    routes=json.loads((SKIN/'jsonnet/Constants/InputRoutes.json').read_text(encoding='utf-8'))
    route_failures=inspect_routes(config, routes)
    catalog=json.loads((SKIN/'jsonnet/Constants/LetterSymbols.json').read_text(encoding='utf-8'))
    oracle={'letters':''.join(EXPECTED), 'chinese':''.join(v[0] for v in EXPECTED.values()),
            'english':''.join(v[1] for v in EXPECTED.values())}
    html=(ROOT/'preview/index.html').read_text(encoding='utf-8')
    embedded=json.loads(re.search(r'const letterSymbols = (.*);',html).group(1))
    embedded_routes=json.loads(re.search(r'const inputRoutes = (.*);',html).group(1))
    archive=ROOT/'dist/扁平灰白.cskin'
    package_ok=False
    count=0
    if archive.exists():
        with zipfile.ZipFile(archive) as z:
            count=len(z.namelist())
            files={path.relative_to(SKIN).as_posix():path.read_bytes() for path in SKIN.rglob('*') if path.is_file()}
            package_ok=z.testzip() is None and set(z.namelist())=={'扁平灰白/'+name for name in files}
            package_ok=package_ok and all(z.read('扁平灰白/'+name)==data for name,data in files.items())
    mismatches=sum(bool(row['failures']) for group in result.values() for row in group)
    ok=not mismatches and not route_failures and catalog==embedded==oracle and routes==embedded_routes and package_ok
    stamp=datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M UTC+8')
    lines=['# 中英文符号逐键核对报告', '', f'核对时间：{stamp}。', '',
        '## 当前结果', '',
        f'**配置审计：{"通过" if ok else "未通过"}；iOS 实机验收：待验证。**', '',
        '已拆分 pinyin 中文主键盘与 alphabetic 英文主键盘。每份文件在首次加载时就包含对应语言的上标、上滑动作、普通气泡、长按网格及回退列表，字母与标点不再依赖 ascii_mode 通知来更新。', '',
        '中英按钮通过 sendKeys 专用组合键调用配套 RIME Lua 处理器，并同步选择布局：中文→alphabetic + melt_eng；英文→pinyin + 最近一次中文方案。无记忆时默认小鹤双拼。必须安装配套四份补丁与 lua/skin_scheme_memory.lua 并重新部署；仅导入皮肤不会安装处理器。', '',
        '## 逐键结果', '',
        '| 按键 | 中文目标及码点 | 英文目标及码点 | 初始上标/上滑气泡 | 上滑动作 | 长按网格/回退 |',
        '| --- | --- | --- | --- | --- | --- |']
    for letter,(zh,en) in EXPECTED.items():
        rows=[row for row in result['letters'] if row['letter']==letter]
        def status(names):
            return '通过' if all(not any(name in row['failures'] for name in names) for row in rows) else '失败'
        lines.append(f'| {letter.upper()} | {unicode_label(zh)} | {unicode_label(en)} | '
            f'{status(["键面上标","上滑气泡"])} | {status(["上滑动作"])} | '
            f'{status(["长按符号显示","长按符号动作","长按大写态符号动作","旧版长按列表"])} |')
    lines += ['', '数字按约定保持半角；中文 H/J 分别为弯引号 “ / ”，英文均为直双引号 U+0022；V 中文为全角低线 U+FF3F，M 中文为全角反引号 U+FF40。长按仍保留大小写拉丁字母选项。', '',
        '## 自动核对范围', '',
        f'- 8 份主键盘配置 × 26 键 × 普通/Shift/大写锁定 × 两种 ascii_mode × 初始/通知阶段，共 {len(result["letters"])} 组，每组检查 {len(COMPONENTS)} 项。',
        f'- 显式中文→英文→中文及反向布局切换：{len(result["cycles"])} 组；英文方案 ASCII-OFF：{len(result["english_schema"])} 组。',
        f'- 逗号、句号动作：{len(result["punctuation"])} 组。以上共 {mismatches} 组不一致。',
        f'- 中英按钮、4 个方案选项、数字/符号返回动作检查：{len(route_failures)} 项不一致。',
        f'- 独立 Unicode 基准、原生映射、HTML 映射：{"一致" if catalog==embedded==oracle else "不一致"}；HTML 方案列表：{"一致" if routes==embedded_routes else "不一致"}。',
        f'- .cskin 共 {count} 个文件，CRC、文件集合和内容与当前源码：{"一致" if package_ok else "不一致"}。',
        '- 全部 28 份配置通过结构、引用、动作和布局校验。自动切换测试是配置模型，不是元书事件派发的实测。', '',
        '## 方案与入口', '', '| 方案 ID | 键盘类型 |', '| --- | --- |']
    lines += [f'| {item["id"]} | {"alphabetic" if item["language"]=="en" else "pinyin"} |' for item in routes['schemes']]
    lines += ['', '工具栏方案入口改为皮肤自己的选择面板，选项会同时切换布局与方案；它只列出上述约定方案，不扫描手机已安装方案。元书中需安装并启用这些方案。', '',
        '数字页继续调用 returnPrimaryKeyboard，符号页继续调用 returnLastKeyboard；网页返回也保留当前语言和方案。英文符号、数字字面值使用 symbol 直接上屏，普通字母通过 character 输入；英文候选开启时使用词库，关闭时 ASCII 直通。', '',
        '## 实机待验与支持边界', '',
        '- **尚未完成最小实机验证。** 此环境无法运行元书 iOS。已生成完整验证包与配置示意，不能将 Windows 配置/网页结果记为实机通过。',
        '- 先测 Q、F、H、J、A/L 与逗号句号：冷启动中文/英文、中英往返、普通/Shift/大写锁定、有/无预编辑；复制实际字符核对 Unicode。再验全部 26 键及横竖屏、深浅色。',
        '- 冷启动是否恢复匹配的键盘类型和方案、组合动作执行顺序、英文单词候选、候选上屏以及英文状态下数字/符号返回，均需元书 1.11.0(558) 实机确认。',
        '- melt_eng 使用词库时为 ASCII-OFF；英文逗号长按可切为 ASCII-ON 直接输入。配套 Lua 恢复已保存的候选开关，英文 reset 为 -1，中文仍关闭 ASCII 直通。状态显示与原生长按执行仍需实机确认。',
        '- 通过元书应用或原生菜单独立更换方案/ASCII 选项不在皮肤路由控制内，不能保证同时改变布局。使用本皮肤的中英按钮或方案面板重新同步；没有声称支持这些外部入口的自动同步。',
        '- iPad 普通键盘沿用已有布局与动作；浮动键盘使用 iPhone 配置。iPad 普通键盘的英文符号不在本轮验收范围内。',
        '- HTML 为离线交互演示，不运行 RIME、不生成真实英文候选；300ms 是网页长按时间，原生长按时间由元书决定。', '',
        '## 配置证据', '', '| 文件 | SHA-256 |', '| --- | --- |']
    lines += [f'| {name} | `{hashlib.sha256((SKIN/name).read_bytes()).hexdigest()}` |' for name in documents]
    if mismatches or route_failures:
        lines += ['', '## 未通过明细', '', code(json.dumps(route_failures,ensure_ascii=False))]
        for group,rows in result.items():
            for row in rows:
                if row['failures']:
                    lines.append('- '+group+': '+code(json.dumps(row,ensure_ascii=False)))
    lines += ['', '## 复核与依据', '', '```powershell',
        'python scripts/build_skin.py', 'python -m unittest discover -s tests -v',
        'python scripts/audit_letter_symbols.py', '```', '',
        '退出码 0 表示上述配置审计通过，仍不代表实机验收通过。修复前的检查结果保存在同目录的《中英文符号核对报告-修复前.md》。', '',
        '- [元书动作与键盘/方案组合切换](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/action/)',
        '- [元书配置类型与气泡引用](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/keys-reference/)',
        '- [元书通知机制](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/notifications/)',
        '- [薄荷 melt_eng 默认方案](https://github.com/Mintimate/oh-my-rime/blob/main/melt_eng.schema.yaml)', '']
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text('\n'.join(lines),encoding='utf-8')
    return ok


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'docs/中英文符号核对报告.md')
    args=parser.parse_args()
    validate_skin()
    documents={f'{theme}/{kind}{orientation}.yaml':json.loads(
        (SKIN/theme/f'{kind}{orientation}.yaml').read_text(encoding='utf-8'))
        for theme in ('light','dark') for orientation in ('Portrait','Landscape') for kind in ('pinyin','alphabetic')}
    result=audit_documents(documents)
    ok=write_report(result,documents,args.output)
    print(f'Report: {args.output}')
    print(f'Letter cases: {len(result["letters"])}; mismatches: {sum(bool(row["failures"]) for row in result["letters"])}')
    return 0 if ok else 1


if __name__=='__main__':
    raise SystemExit(main())
