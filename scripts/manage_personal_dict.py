"""Maintain the existing personal Rime dictionary, backing up every real edit.

Example: python scripts/manage_personal_dict.py add --text 新词 --code 'xin ci'
The tool never deploys Rime and never modifies userdb directories.
"""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_USER_DIR = ROOT / 'external_files/oh-my-rime'


def validate_entry(text, code, weight):
    if not text or text.startswith('#') or any(c in text for c in '\t\r\n'):
        raise ValueError('词语不能为空、以 # 开头或包含制表符/换行')
    if not re.fullmatch(r'[a-zv]+(?: [a-zv]+)*', code):
        raise ValueError('编码须为小写无声调全拼，音节用一个空格分隔，ü 写作 v')
    if not isinstance(weight, int) or weight < 0:
        raise ValueError('权重须为非负整数')


def read_dictionary(path):
    raw = path.read_bytes()
    bom = raw.startswith(b'\xef\xbb\xbf')
    lines = raw.decode('utf-8-sig').splitlines(keepends=True)
    end = next((i for i, line in enumerate(lines) if line.strip() == '...'), None)
    if end is None or not any(line.strip() == '---' for line in lines[:end]):
        raise ValueError('词典缺少 YAML 头部或 ... 结束标记')
    if not any(re.fullmatch(r'name:\s*custom_simple\s*(?:#.*)?', line.strip()) for line in lines[:end]):
        raise ValueError('目标必须是现有的 custom_simple 个人词典')
    entries = {}
    for i, line in enumerate(lines[end + 1:], end + 1):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        fields = line.rstrip('\r\n').split('\t')
        if len(fields) not in (2, 3) or not fields[0] or not fields[1]:
            raise ValueError(f'第 {i + 1} 行不是有效的制表符分隔词条')
        if len(fields) == 3 and not re.fullmatch(r'\d+', fields[2]):
            raise ValueError(f'第 {i + 1} 行权重不是非负整数')
        key = (fields[0], fields[1])
        if key in entries:
            raise ValueError(f'第 {i + 1} 行存在重复的词语与编码')
        entries[key] = i
    return raw, bom, lines, entries


def edit(user_dir, operation, text, code, weight=100, dry_run=False):
    validate_entry(text, code, weight)
    path = Path(user_dir) / 'dicts/custom_simple.dict.yaml'
    raw, bom, lines, entries = read_dictionary(path)
    key = (text, code)
    if operation == 'add' and key in entries:
        raise ValueError('词条已存在，请用 update 修改权重')
    if operation in ('update', 'remove') and key not in entries:
        raise ValueError('指定词语与编码不存在')
    newline = '\r\n' if b'\r\n' in raw else '\n'
    row = f'{text}\t{code}\t{weight}{newline}'
    if operation == 'add':
        if lines and not lines[-1].endswith(('\n', '\r')):
            lines[-1] += newline
        lines.append(row)
    elif operation == 'update':
        lines[entries[key]] = row
    elif operation == 'remove':
        del lines[entries[key]]
    else:
        raise ValueError('未知操作')
    new = (b'\xef\xbb\xbf' if bom else b'') + ''.join(lines).encode('utf-8')
    if dry_run or new == raw:
        return path, None, new != raw
    backups = path.parent / '.backups'
    backups.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = backups / f'custom_simple.{stamp}.{uuid.uuid4().hex[:8]}.dict.yaml'
    with backup.open('xb') as target:
        target.write(raw)
    fd, temporary = tempfile.mkstemp(prefix='.custom_simple-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as target:
            target.write(new)
            target.flush()
            os.fsync(target.fileno())
        # Do not overwrite an edit made after this process read the file.
        if path.read_bytes() != raw:
            raise ValueError('词典在操作期间被其他程序修改，请重新执行')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return path, backup, True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('add', 'update', 'remove'))
    parser.add_argument('--user-dir', type=Path, default=DEFAULT_USER_DIR)
    parser.add_argument('--text', required=True)
    parser.add_argument('--code', required=True)
    parser.add_argument('--weight', type=int, default=100)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    try:
        path, backup, changed = edit(args.user_dir, args.operation, args.text,
                                     args.code, args.weight, args.dry_run)
    except (ValueError, OSError, UnicodeError) as exc:
        parser.exit(1, f'失败：{exc}\n')
    if args.dry_run:
        print('预检查通过；未修改文件。')
    elif not changed:
        print('词条已经符合要求；未修改文件。')
    else:
        print(f'已更新：{path}\n备份：{backup}\n请在元书中重新部署输入方案。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
