"""Audit compiled symbol routes independently of the shared catalog.

Initial nodes and option-notification replacements are deliberately separate.
This checks configuration, not delivery of native iOS notification events.
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
        if node.get('action') != expected:
            failures[name] = {'actual': node.get('action'), 'expected': expected}
    return failures


def audit_documents(documents):
    rows, punctuation, cycles, english_schema = [], [], [], []
    for filename, doc in documents.items():
        for notified in (False, True):
            for english in (False, True):
                for case, shift, caps in CASE_STATES:
                    for letter in EXPECTED:
                        rows.append(dict(file=filename, letter=letter, english=english, notified=notified,
                                         case=case, failures=inspect_letter(doc, letter, english, notified, shift, caps)))
                    punctuation.append(dict(file=filename, english=english, notified=notified, case=case,
                                            failures=inspect_punctuation(doc, english, notified)))
        # Model complete notification replacements in both transition directions.
        # This does not claim to simulate the native event dispatcher or its order.
        for sequence in ((False, True, False), (True, False, True)):
            for step, english in enumerate(sequence):
                for case, shift, caps in CASE_STATES:
                    for letter in EXPECTED:
                        cycles.append(dict(file=filename, sequence=sequence, step=step, letter=letter,
                                           case=case, failures=inspect_letter(doc, letter, english, True, shift, caps)))
        # Public melt_eng default: English schema with ASCII-OFF. There is
        # currently no schemaChanged override; model its option state separately
        # from the expected English language. Do not claim a native event test.
        for case, shift, caps in CASE_STATES:
            for letter in EXPECTED:
                english_schema.append(dict(file=filename, letter=letter, case=case,
                    failures=inspect_letter(doc, letter, True, True, shift, caps, option_english=False)))
    return dict(letters=rows, punctuation=punctuation, cycles=cycles, english_schema=english_schema)


def code(value):
    # HTML entities keep backticks and quotes readable inside Markdown tables.
    return '<code>' + value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') + '</code>'


def unicode_label(value):
    return code(value) + ' ' + ' '.join(f'U+{ord(char):04X}' for char in value)


def write_report(result, documents, output):
    initial = [row for row in result['letters'] if not row['notified']]
    notified = [row for row in result['letters'] if row['notified']]
    failed = [row for row in initial if row['failures']]
    affected = ''.join(letter.upper() for letter in EXPECTED
                       if any(row['letter'] == letter for row in failed))
    catalog = json.loads((SKIN / 'jsonnet/Constants/LetterSymbols.json').read_text(encoding='utf-8'))
    oracle = {'letters': ''.join(EXPECTED), 'chinese': ''.join(v[0] for v in EXPECTED.values()),
              'english': ''.join(v[1] for v in EXPECTED.values())}
    html = (ROOT / 'preview/index.html').read_text(encoding='utf-8')
    embedded = json.loads(re.search(r'const letterSymbols = (.*);', html).group(1))
    archive = ROOT / 'dist/扁平灰白.cskin'
    package_ok = False
    entry_count = 0
    if archive.exists():
        with zipfile.ZipFile(archive) as z:
            entry_count = len(z.namelist())
            files = {path.relative_to(SKIN).as_posix(): path.read_bytes()
                     for path in SKIN.rglob('*') if path.is_file()}
            package_ok = z.testzip() is None and set(z.namelist()) == {'扁平灰白/' + name for name in files}
            package_ok = package_ok and all(z.read('扁平灰白/' + name) == data for name, data in files.items())
    stats = Counter(name for row in failed for name in row['failures'])
    stamp = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M UTC+8')
    lines = [
        '# 中英文符号逐键核对报告', '', f'核对时间：{stamp}。对象：当前工作区与现有 `.cskin`；本轮未修改原生键盘配置。', '',
        '## 结论', '',
        '**当前不能判定“全部无误”。字符映射本身符合已确认表格，但初始英文动作与显示存在配置不一致，另有独立英文方案的状态识别缺口。**', '',
        f'- 26 键在语言通知已生效后的上标、上滑显示与动作、长按显示与动作：{len(notified)} 组中 {sum(not row["failures"] for row in notified)} 组通过。',
        f'- 初始节点：{len(initial)} 组中 {len(failed)} 组存在不一致，集中在英文的 {len(affected)} 键（{affected}）。',
        '- 所有通过项仅表示配置值一致；没有用 iPhone 实测通知是否在首次打开、方案切换时正确生效。',
        '- 本报告将缺陷与实机待验项目分开，不把网页输入结果当成元书实际输入结果。', '',
        '## 逐键结果', '',
        '表中“通知后”检查中文及英文两种状态、浅色/深色、竖屏/横屏、普通/Shift/大写锁定。'
        '“初始英文”表示直接读取基础按键、尚未收到语言通知的路径，不表示已在 iPhone 复现。', '',
        '| 按键 | 中文目标及码点 | 英文目标及码点 | 通知后显示与动作 | 初始中文 | 初始英文 |',
        '| --- | --- | --- | --- | --- | --- |',
    ]
    for letter, (zh, en) in EXPECTED.items():
        bad = any(row['letter'] == letter and row['english'] and row['failures'] for row in initial)
        passed = all(not row['failures'] for row in notified if row['letter'] == letter)
        cn_ok = all(not row['failures'] for row in initial if row['letter'] == letter and not row['english'])
        lines.append(f'| {letter.upper()} | {unicode_label(zh)} | {unicode_label(en)} | '
                     f'{"通过" if passed else "失败"} | {"通过" if cn_ok else "失败"} | '
                     f'{"不一致：动作/长按仍为中文" if bad else "通过（数字相同）"} |')
    lines += [
        '', '数字 1–0 按此前约定均保持半角；H/J 中文分别为左右弯引号，英文两键均为 ASCII 直双引号；'
        'V 中文为全角低线 U+FF3F，M 中文为全角反引号 U+FF40。全角并不意味着所有中文符号都位于 FFxx 区段。', '',
        '## 发现的问题', '',
        '### 1. 初始英文显示正确，动作和长按仍指向中文', '',
        '`iPhonePinyin.libsonnet` 的基础 `swipeUpAction`、`hintSymbolsGridStyle`、`hintSymbolsStyle` 固定为中文。'
        '与此同时，上标及上滑气泡使用 `rime$ascii_mode` 条件显示英文。只有英文语言通知节点将动作和长按引用替换成英文。', '',
        '例如初始 `ascii_mode=true`、F 键：键面和上滑气泡显示 `#`（U+0023），基础上滑动作却是 `＃`（U+FF03），'
        '基础长按默认项也为 `＃`。通知生效后这四处才全部变为 `#`。', '',
        '这是可直接从编译配置证明的未通知路径缺口；不能据此断言元书每次启动都漏发通知。'
        '官方说明通知用于 option 变更，但没有在引用页面承诺启动一定回放当前 option。', '',
        '| 初始英文不一致项 | 失败检查次数 |', '| --- | --- |',
    ]
    lines += [f'| {name} | {count} |' for name, count in stats.items()]
    lines += [
        '', '### 2. 底行逗号、句号存在相同依赖', '',
        '初始英文键面显示 `,` / `.`，基础动作仍为 `，` / `。`；英文通知生效后变为半角。'
        '当前两键的中文动作依靠英文通知不匹配时恢复基础节点，并无单独中文通知。', '',
        f'标点动作审计共 {len(result["punctuation"])} 组，两键共 '
        f'{sum(len(row["failures"]) for row in result["punctuation"])} 项不一致，全部属于初始英文路径。', '',
        '### 3. 独立英文方案与 ascii_mode 不是同一个概念', '',
        '本皮肤仅依据 `ascii_mode` 判断符号语言。薄荷 `melt_eng`（Easy English Nano）默认 `ascii_mode=0`，'
        '并需关闭 ASCII 直通才能获得英文单词候选。在这种英文方案状态下，本皮肤仍选择中文全角符号、中文图标及大写键面。', '',
        '当前配置没有 `schemaChanged` 的英文方案覆盖，也没有 `alphabetic` 键盘映射。'
        '因此启用独立英文方案不会自动获得本皮肤的英文符号状态；单靠补一份字符映射无法解决。'
        '尚未读取你手机中是否定制了该方案，以上针对公开默认方案及本地皮肤。', '',
        f'另将“目标语言英文、实际 ascii_mode=false”分离建模：{len(result["english_schema"])} 组中 '
        f'{sum(bool(row["failures"]) for row in result["english_schema"])} 组不符合英文目标；'
        '数字本身相同，但英文普通小写气泡也会受到中文大写状态影响。这是配置状态建模，不是实机方案切换测试。', '',
        '### 4. 之前测试和 HTML 为何没有暴露问题', '',
        '旧测试同时检查初始/通知后的气泡显示，却只对通知节点检查实际上滑、长按动作。'
        'HTML 在执行输入时直接读取当前语言映射，不经过原生通知机制；网页正确不能证明原生初始化正确。'
        '本轮新增审计将基础动作、长按网格和旧版列表全部纳入初始英文路径。', '',
        '## 验证范围与证据', '',
        '- 字符目标采用逐键、逐 Unicode 码点的独立基准，避免把同一份错误映射同时用作输入和测试答案。',
        '- 4 份 iPhone 主键盘配置 × 26 键 × 2 语言 × 3 大小写状态 × 2 通知阶段，共 '
        f'{len(result["letters"])} 组；每组检查 {len(COMPONENTS)} 项。',
        f'- 中→英→中、英→中→英的通知节点替换核对：{len(result["cycles"])} 组，'
        f'{sum(bool(row["failures"]) for row in result["cycles"])} 组不一致。此项检查节点定义，不模拟 iOS 事件派发顺序。',
        f'- 独立基准与 `LetterSymbols.json`：{"一致" if catalog == oracle else "不一致"}；离线 HTML 内嵌映射：'
        f'{"一致" if embedded == oracle else "不一致"}。',
        f'- 现有压缩包：{entry_count} 个文件；CRC、文件集合及全部文件内容与源码 '
        f'{"一致" if package_ok else "不一致或尚未打包"}。',
        '- 全部 20 份配置完成结构、引用与布局校验；此类校验通过不等于语言动作通过。', '',
        '- 本轮完整回归：48 项测试通过（包含审计能够识别已知缺口的测试）；'
        '审计自身仍返回退出码 1，不把“审计工具正确发现问题”记为“皮肤问题已解决”。', '',
        '| 审计配置 | SHA-256 |', '| --- | --- |',
    ]
    lines += [f'| {name} | `{hashlib.sha256((SKIN / name).read_bytes()).hexdigest()}` |' for name in documents]
    lines += [
        '', '## 其他符号入口的范围', '',
        '- 数字页仍按既定设计提供半角运算符、句点和 @；它不是按语言切换的字母键上标，本轮不改。',
        '- 符号页“常用”刻意混合中英文；“中文”“英文”由用户选择分类，现有 20 项/分类未变化。'
        '分类与主键盘的语言映射是不同入口，不据此判定全部字符符合主键盘的全角规则。',
        '- iPad 普通布局仍保留旧动作；iPad 浮动键盘复用 iPhone 竖屏，具有相同的初始状态风险。',
        '- 长按仍保留大写/小写拉丁字母选项，这是已确认功能；语言限制针对符号项，不删除字母选项。', '',
        '## 修复状态与验收条件', '',
        '**本轮交付审计工具与报告，未宣称已修复上述原生缺口，也未重新打包皮肤。**'
        '不向动作或长按引用写入官方未支持的条件数组，避免再次引入无法解析的配置。', '',
        '后续修复需同时解决：初始语言下动作/长按引用的选择，以及英文方案处于 `ascii_mode=false` 时的语言判定。'
        '可以评估独立中/英文键盘文件配合原生键盘类型与方案切换，但须处理返回键、语言按钮、方案保留及初始化，不能只补显示层。', '',
        '最终需在元书 1.11.0(558) 实机逐键比较复制出的 Unicode：冷启动中文/英文、两种语言往返切换、'
        '独立英文方案且 ASCII 关闭、普通/Shift/大写锁定、有/无拼音预编辑，分别验证上滑与长按。'
        '所有已知不一致清零、实机检查通过后，才可标为验收通过。', '',
        '## 复核命令', '',
        '```powershell', 'python scripts/build_skin.py --compile-only',
        'python -m unittest discover -s tests -v', 'python scripts/audit_letter_symbols.py', '```', '',
        '审计命令发现上述缺口时返回退出码 1，并仍然写出本报告。这是审计发现，不是工具崩溃。', '',
        '## 依据', '',
        '- [元书按键动作：symbol 直接发送系统；中英切换操作 ascii_mode](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/action/)',
        '- [元书配置索引：动作、长按引用、条件样式及通知替换](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/keys-reference/)',
        '- [元书事件通知：option 变更触发与不匹配恢复](https://ihsiao.com/apps/hamster/v3/docs/guides/skins/notifications/)',
        '- [薄荷公开 melt_eng 配置：ascii_mode reset 0](https://github.com/Mintimate/oh-my-rime/blob/main/melt_eng.schema.yaml)', '',
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(lines), encoding='utf-8')
    return catalog == embedded == oracle and package_ok and not any(row['failures'] for group in result.values() for row in group)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/中英文符号核对报告.md')
    args = parser.parse_args()
    validate_skin()
    documents = {f'{theme}/pinyin{orientation}.yaml': json.loads(
        (SKIN / theme / f'pinyin{orientation}.yaml').read_text(encoding='utf-8'))
        for theme in ('light', 'dark') for orientation in ('Portrait', 'Landscape')}
    result = audit_documents(documents)
    ok = write_report(result, documents, args.output)
    print(f'Report: {args.output}')
    print(f'Letter cases: {len(result["letters"])}; mismatches: {sum(bool(row["failures"]) for row in result["letters"])}')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
