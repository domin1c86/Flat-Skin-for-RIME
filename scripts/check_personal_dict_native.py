"""Verify the maintenance tool's output is imported by real Rime schemas."""
import sys
from manage_personal_dict import edit
from rime_native import Engine, prepare
from check_rime_learning import CHINESE


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    work = prepare()
    edit(work, 'add', '库莉姆', 'ku li mu')
    edit(work, 'update', '库莉姆', 'ku li mu', 120)
    engine = Engine(work)
    try:
        engine.deploy(('melt_eng',) + CHINESE)
        engine.start()
        for schema in CHINESE:
            engine.select_schema(schema)
            engine.type('kulimu')
            assert '库莉姆' in [w for w, _ in engine.page()[0]], (schema, engine.page())
            engine.type('keyi')
            assert '可以' in [w for w, _ in engine.page()[0]], (schema, engine.page())
        print('PASS: personal entry imported by three schemas; existing entry preserved')
    finally:
        engine.close()
    edit(work, 'remove', '库莉姆', 'ku li mu')
    assert '库莉姆' not in (work / 'dicts/custom_simple.dict.yaml').read_text(encoding='utf-8')
    print('PASS: removal; all personal edits confined to', work)


if __name__ == '__main__':
    main()
