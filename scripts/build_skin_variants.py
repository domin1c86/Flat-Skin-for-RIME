"""Build separately named skins with symmetric main-keyboard padding. Requires Pillow."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

from PIL import Image, ImageDraw

from build_skin import ROOT, SKIN, SkinError, compile_skin, package_skin, require, validate_skin
from render_skin_preview import SCALE, font, render_keyboard

PADDINGS = (0, 8, 12, 16, 20, 24)


def build_variant(padding, output_dir, binary):
    require(type(padding) is int and 0 <= padding <= 24, 'side padding must be an integer from 0 to 24pt')
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    scratch = ROOT / '.tools'
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='skin-padding-', dir=scratch) as temporary:
        skin = Path(temporary) / 'default'
        shutil.copytree(SKIN, skin)
        settings = skin / 'jsonnet/Constants/MainKeyboard.json'
        settings.write_text(json.dumps({'sidePadding': padding}, indent=2) + '\n', encoding='utf-8', newline='\n')
        compile_skin(binary, skin)
        readme = skin / 'README.md'
        heading = f'本版本主键盘每侧额外留白 {padding}pt，左右相同。适用于 iPhone 中英文、横竖屏和 iPad 浮动键盘；按键高度与工具栏不变。\n\n'
        readme.write_text(heading + readme.read_text(encoding='utf-8'), encoding='utf-8', newline='\n')
        light = render_keyboard('pinyinPortrait', 'light', skin=skin)
        dark = render_keyboard('pinyinPortrait', 'dark', skin=skin)
        demo = Image.new('RGB', (light.width * 2, light.height), '#f7f7f5')
        demo.paste(light, (0, 0))
        demo.paste(dark, (light.width, 0))
        demo.save(skin / 'demo.png', optimize=True)
        count = validate_skin(skin)
        name = json.loads((skin / 'config.yaml').read_text(encoding='utf-8'))['name']
        output = output_dir / (name + '.cskin')
        package_skin(output, skin)
    return output, light, count


def build_variants(output_dir, binary, paddings=PADDINGS):
    require(bool(paddings), 'at least one side-padding value is required')
    require(all(type(padding) is int and 0 <= padding <= 24 for padding in paddings),
            'side padding must be an integer from 0 to 24pt')
    results = []
    for padding in sorted(set(paddings)):
        output, preview, count = build_variant(padding, output_dir, binary)
        results.append((padding, output, preview))
        print(f'Built {output.name}: {padding}pt per side; {count} keyboard files validated.', flush=True)
    margin, gap, label_height = 18 * SCALE, 16 * SCALE, 30 * SCALE
    columns = min(3, len(results))
    rows = (len(results) + columns - 1) // columns
    tile_width, tile_height = results[0][2].size
    comparison = Image.new('RGB', (2 * margin + columns * tile_width + (columns - 1) * gap,
                                  2 * margin + rows * (tile_height + label_height) + (rows - 1) * gap), '#f7f7f5')
    draw = ImageDraw.Draw(comparison)
    for index, (padding, output, preview) in enumerate(results):
        left = margin + index % columns * (tile_width + gap)
        top = margin + index // columns * (tile_height + label_height + gap)
        draw.text((left, top), f'每侧留白 {padding}pt', font=font(14, '每侧留白'), fill='#242725')
        comparison.paste(preview, (left, top + label_height))
    output_dir = Path(output_dir)
    comparison.save(output_dir / '留白宽度对比.png', optimize=True)
    guide = ['# 主键盘留白版本', '',
             '每个版本只收窄主键盘的四行按键，左右额外留白共用同一个数值，单位为 pt。按键高度、工具栏、候选栏、数字页、符号页和 iPad 普通键盘保持原样；iPad 浮动键盘复用对应的 iPhone 配置。', '',
             '所有版本均包含中文 C/V/M 的半角连字符、低线和反引号；上标、上滑和长按保持一致。', '',
             '| 安装文件 | 每侧额外留白 | 按键区总收窄 |', '| --- | --- | --- |']
    guide += [f'| {output.name} | {padding}pt | {padding * 2}pt |' for padding, output, preview in results]
    guide += ['', '通过文件或分享菜单用元书打开所需 .cskin，再选择对应名称启用。不同留白宽度使用不同皮肤名称，可分别导入后切换；0pt 的名称为「扁平灰白」。无需更新 RIME 方案或个人词库。', '',
              '可先试每侧 12pt 或 16pt。数值越大，键盘越窄；实机舒适度需自行试用。示意图来自配置渲染，并非 iOS 截图。', '',
              '每份皮肤保留对应的 MainKeyboard.json，手机端重新运行 main.jsonnet 仍保留该版本宽度。', '']
    (output_dir / '安装说明.md').write_text('\n'.join(guide), encoding='utf-8', newline='\n')
    bundle = output_dir.parent / '主键盘留白版本合集.zip'
    with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for output in [output for padding, output, preview in results] + [output_dir / '安装说明.md', output_dir / '留白宽度对比.png']:
            archive.write(output, output.name)
    print(f'Bundle: {bundle}', flush=True)
    return [output for padding, output, preview in results]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jsonnet', type=Path, help='Jsonnet executable path')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'dist/留白版本')
    parser.add_argument('--padding', type=int, nargs='+', choices=range(25), default=PADDINGS, help='extra padding per side in pt')
    args = parser.parse_args()
    binary = args.jsonnet or shutil.which('jsonnet') or ROOT / '.tools' / ('jsonnet.exe' if sys.platform == 'win32' else 'jsonnet')
    try:
        require(Path(binary).is_file(), 'Jsonnet CLI not found; install jsonnet or pass --jsonnet PATH')
        build_variants(args.output_dir, binary, args.padding)
    except (SkinError, OSError, ValueError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
