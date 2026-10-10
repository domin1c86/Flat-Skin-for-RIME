"""Package only companion patches, canonical Lua, maintenance tool and guide."""
import argparse
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PATCHES = ('double_pinyin_flypy', 'rime_mint', 'rime_mint_flypy', 'melt_eng')
LUA = ('skin_scheme_memory', 'skin_context', 'skin_context_processor',
       'skin_context_translator', 'skin_context_filter')


def build(output):
    files = {name + '.custom.yaml': ROOT / 'external_files/oh-my-rime' / (name + '.custom.yaml')
             for name in PATCHES}
    files.update({'lua/' + name + '.lua': ROOT / 'scripts/rime' / (name + '.lua') for name in LUA})
    files['输入法学习与联想.md'] = ROOT / 'docs/输入法学习与联想.md'
    files['tools/manage_personal_dict.py'] = ROOT / 'scripts/manage_personal_dict.py'
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, path in sorted(files.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == set(files)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/元书皮肤配套补丁.zip')
    print(build(parser.parse_args().output))
