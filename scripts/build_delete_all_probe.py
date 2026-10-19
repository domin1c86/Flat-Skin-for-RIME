"""Build an isolated native delete-all experiment without changing release skins."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile

from PIL import Image

from build_skin import ROOT, SKIN, SkinError, compile_skin, package_skin, require, validate_skin
from render_skin_preview import render_keyboard

EXPERIMENT = ROOT / 'experiments/delete-all'


def build_probe(output_dir, binary, padding=0):
    require(type(padding) is int and 0 <= padding <= 24, 'side padding must be an integer from 0 to 24pt')
    output_dir = Path(output_dir)
    scratch = ROOT / '.tools'
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='delete-all-probe-', dir=scratch) as temporary:
        skin = Path(temporary) / 'default'
        shutil.copytree(SKIN, skin)
        source = skin / 'jsonnet'
        (source / 'main.jsonnet').rename(source / 'main.standard.jsonnet')
        shutil.copyfile(EXPERIMENT / 'main.jsonnet', source / 'main.jsonnet')
        settings = source / 'Constants/MainKeyboard.json'
        settings.write_text(json.dumps({'sidePadding': padding}, indent=2) + '\n', encoding='utf-8', newline='\n')
        compile_skin(binary, skin)
        guide = (EXPERIMENT / 'README.md').read_text(encoding='utf-8')
        heading = f'本验证版主键盘每侧额外留白 {padding}pt，左右相同。\n\n'
        (skin / 'README.md').write_text(heading + guide, encoding='utf-8', newline='\n')
        light = render_keyboard('pinyinPortrait', 'light', skin=skin)
        dark = render_keyboard('pinyinPortrait', 'dark', skin=skin)
        demo = Image.new('RGB', (light.width * 2, light.height), '#f7f7f5')
        demo.paste(light, (0, 0))
        demo.paste(dark, (light.width, 0))
        demo.save(skin / 'demo.png', optimize=True)
        count = validate_skin(skin)
        name = json.loads((skin / 'config.yaml').read_text(encoding='utf-8'))['name']
        output_dir.mkdir(parents=True, exist_ok=True)
        output = output_dir / (name + '.cskin')
        package_skin(output, skin)
        (output_dir / '验证说明.md').write_text(guide, encoding='utf-8', newline='\n')
    return output, count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jsonnet', type=Path, help='Jsonnet executable path')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'dist/删除全部验证版')
    parser.add_argument('--padding', type=int, choices=range(25), default=0)
    args = parser.parse_args()
    binary = args.jsonnet or shutil.which('jsonnet') or ROOT / '.tools' / ('jsonnet.exe' if sys.platform == 'win32' else 'jsonnet')
    try:
        require(Path(binary).is_file(), 'Jsonnet CLI not found; install jsonnet or pass --jsonnet PATH')
        output, count = build_probe(args.output_dir, binary, args.padding)
        print(f'Validated {count} keyboard files. Packaged: {output}')
    except (SkinError, OSError, ValueError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
