"""Rebuild both padding families, audit their contents, and bundle review documents."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import zipfile

from PIL import Image, ImageDraw

from audit_symbol_catalog import LABELS, REPORT, check_skin_catalog, load_catalog, render_report
from build_delete_all_probe import build_probe
from build_skin import ROOT, SkinError, require, validate_document
from build_skin_variants import PADDINGS, build_variants
from render_skin_preview import SCALE, font, render_keyboard
from rime_skin_actions import semantic_action


def check_package(path, padding, experimental):
    with zipfile.ZipFile(path) as archive:
        require(archive.testzip() is None, f'{path}: CRC failed')
        roots = {name.split('/', 1)[0] for name in archive.namelist()}
        require(len(roots) == 1, f'{path}: expected one skin root')
        root = roots.pop() + '/'
        config = json.loads(archive.read(root + 'config.yaml'))
        expected_name = '扁平灰白' + (f'·留白{padding}pt' if padding else '')
        if experimental:
            expected_name += '·删除全部验证'
        require(config['name'] == root[:-1] == expected_name, f'{path}: incorrect skin name')
        require(json.loads(archive.read(root + 'jsonnet/Constants/MainKeyboard.json')) == {'sidePadding': padding},
                f'{path}: incorrect source padding')
        catalog = load_catalog()
        require(json.loads(archive.read(root + 'jsonnet/Constants/SymbolCatalog.json')) == catalog,
                f'{path}: stale source catalog')
        documents = {name[len(root):]: json.loads(archive.read(name)) for name in archive.namelist()
                     if name.startswith((root + 'light/', root + 'dark/')) and name.count('/') == 2 and name.endswith('.yaml')}
        require(len(documents) == 28, f'{path}: expected 28 keyboard files')
        for name, document in documents.items():
            validate_document(document)
            if name.split('/')[1].startswith(('pinyin', 'alphabetic')):
                require(document['keyboardStyle']['insets'] == {'left': padding, 'right': padding},
                        f'{path}/{name}: incorrect compiled padding')
                english = '/alphabetic' in name
                for letter, expected in zip('hjm', ("'", '&', '/') if english else ('“', '”', '`')):
                    require(semantic_action(document[letter + 'Button']['swipeUpAction']) == {'symbol': expected},
                            f'{path}/{name}: stale swipe mapping')
                require(('deleteAllProbeGrid' in document) is experimental, f'{path}/{name}: wrong experiment state')
                if experimental:
                    grid = document['deleteAllProbeGrid']
                    require(grid['symbolRows'] == [['deleteAllProbeOption'], [None]] and 'selected' not in grid,
                            f'{path}/{name}: changed clear bubble selection')
                    require(document['deleteAllProbeSelectedBackground']['normalColor'] == '#D32F2F'
                            and document['deleteAllProbeLabel']['highlightColor'] == '#FFFFFF',
                            f'{path}/{name}: changed clear bubble colors')
            if '/numeric' in name:
                require(document['numericOperatorData'] == list(catalog['numericOperators']), f'{path}: stale numeric list')
            if '/symbolic' in name:
                require(document['symbolCategoryData'] == LABELS, f'{path}: stale category list')
                for category in catalog['categories']:
                    values = [item['value'] if isinstance(item, dict) else item for item in document[category['label']]]
                    require(values == category['symbols'], f'{path}: stale symbols')
        return len(documents)


def write_bundle(path, files):
    require(len({file.name for file in files}) == len(files), 'duplicate bundle filename')
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            archive.write(file, file.name)
    with zipfile.ZipFile(path) as archive:
        require(archive.testzip() is None, f'{path}: bundle CRC failed')
        require(set(archive.namelist()) == {file.name for file in files}, f'{path}: bundle entries mismatch')
        require(all(archive.read(file.name) == file.read_bytes() for file in files), f'{path}: bundle contents mismatch')


def render_categories(output, scheme, catalog):
    width, gap, heading = 390 * SCALE, 12 * SCALE, 26 * SCALE
    tiles = [render_keyboard('symbolicPortrait', scheme, category=item['label']) for item in catalog['categories']]
    height = tiles[0].height
    columns = 3
    rows = (len(tiles) + columns - 1) // columns
    image = Image.new('RGB', (columns * (width + gap) + gap, rows * (height + heading + gap) + gap), '#f7f7f5')
    draw = ImageDraw.Draw(image)
    for index, (tile, category) in enumerate(zip(tiles, catalog['categories'])):
        left = gap + index % columns * (width + gap)
        top = gap + index // columns * (height + heading + gap)
        label = f"{category['label']} · {len(category['symbols'])}项 · 配置示意，非实机"
        draw.text((left, top), label, font=font(12, label), fill='#242725')
        image.paste(tile, (left, top + heading))
    image.save(output, optimize=True)


def build_release(output_dir, binary, paddings=PADDINGS):
    require(bool(paddings) and all(type(value) is int and 0 <= value <= 24 for value in paddings), 'invalid padding list')
    paddings = sorted(set(paddings))
    catalog = load_catalog()
    check_skin_catalog(catalog=catalog)
    require(REPORT.read_text(encoding='utf-8') == render_report(catalog), 'review document is stale; run audit_symbol_catalog.py')
    output_dir = Path(output_dir)
    normal = build_variants(output_dir / '留白版本', binary, paddings)
    probes = []
    for padding in paddings:
        path, count = build_probe(output_dir / '删除全部验证版', binary, padding)
        probes.append(path)
        print(f'Built {path.name}: {count} keyboard files validated.', flush=True)
    total = 0
    for experimental, paths in ((False, normal), (True, probes)):
        for padding, path in zip(paddings, paths):
            total += check_package(path, padding, experimental)
    reports = []
    for source in (REPORT, ROOT / 'docs/键盘记忆检查报告.md'):
        target = output_dir / source.name
        shutil.copyfile(source, target)
        reports.append(target)
    diagrams = []
    for scheme, label in (('light', '浅色'), ('dark', '深色')):
        diagram = output_dir / f'符号分类示意-{label}.png'
        render_categories(diagram, scheme, catalog)
        diagrams.append(diagram)
    guide = output_dir / '符号面板更新安装说明.md'
    lines = ['# 键盘符号更新安装说明', '',
             '解压后选择一个 `.cskin`，通过分享或文件菜单用元书导入，再启用对应名称。留白数值是主键盘每侧额外宽度，左右相同，单位 pt；0pt 保留原宽。', '',
             '所有皮肤均更新英文 H/J/M、32项数字符号列及12类符号面板，包含浅深色及横竖屏；常用仍为20项静态列表，没有自动最近记录。符号页与数字页本身不按主键盘留白参数收窄。', '',
             '普通版保留常规删除；验证版保留单项删除气泡、红底白字和下滑取消配置，仍需元书实机验证。验证版不保证整框清空或可撤销，请先在无关紧要的文本中测试。', '',
             '已有配套 RIME 补丁无需因本次更新而更换；本次没有修改记忆逻辑，也没有新增手机端脚本。宿主冷启动恢复仍待错误案例，详见检查报告。', '',
             '| 每侧留白 | 普通版 | 删除验证版 |', '| --- | --- | --- |']
    lines += [f'| {padding}pt | {release.name} | {probe.name} |' for padding, release, probe in zip(paddings, normal, probes)]
    lines += ['', f'共{len(normal) + len(probes)}个安装包，{total}份键盘配置通过打包后检查。逐项字符与码位见《符号面板字符审核》，示意图不是原生截图。', '',
              '复现构建：`python scripts/build_release_variants.py --jsonnet .tools/jsonnet.exe`。', '']
    guide.write_text('\n'.join(lines), encoding='utf-8', newline='\n')
    shutil.copyfile(guide, output_dir / '删除全部验证版/六档留白安装说明.md')
    comparison = output_dir / '留白版本/留白宽度对比.png'
    probe_guide = output_dir / '删除全部验证版/验证说明.md'
    shared = [guide, *reports, *diagrams, comparison]
    write_bundle(output_dir / '主键盘留白版本合集.zip', [*normal, *shared])
    write_bundle(output_dir / '删除全部留白版本合集.zip', [*probes, *shared, probe_guide])
    bundle = output_dir / '键盘符号更新合集.zip'
    write_bundle(bundle, [*normal, *probes, *shared, probe_guide])
    print(f'Verified {total} keyboard files in {len(normal) + len(probes)} skins. Bundle: {bundle}', flush=True)
    return bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jsonnet', type=Path)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'dist')
    parser.add_argument('--padding', type=int, nargs='+', choices=range(25), default=PADDINGS)
    args = parser.parse_args()
    binary = args.jsonnet or shutil.which('jsonnet') or ROOT / '.tools' / ('jsonnet.exe' if sys.platform == 'win32' else 'jsonnet')
    try:
        require(Path(binary).is_file(), 'Jsonnet CLI not found')
        build_release(args.output_dir, binary, args.padding)
    except (SkinError, OSError, ValueError, KeyError) as error:
        parser.exit(1, f'ERROR: {error}\n')


if __name__ == '__main__':
    main()
