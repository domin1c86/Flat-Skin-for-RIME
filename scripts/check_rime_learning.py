"""Deploy a fresh, isolated native Rime fixture and verify actual word learning."""
from pathlib import Path
import sys

from check_rime_user_compat import load, yaml
from rime_native import Engine, prepare

CHINESE = ('double_pinyin_flypy', 'rime_mint', 'rime_mint_flypy')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    work = prepare()
    print('Isolated fixture:', work, flush=True)
    # Add an observation-only final filter: existing formatters otherwise remove
    # comments, hiding the difference between sentence and user_phrase.
    for schema in CHINESE:
        path = work / (schema + '.custom.yaml')
        patch = load(path)
        patch['patch']['engine/filters/+'] = ['lua_filter@*tag_user_dict']
        patch['patch']['tag_user_dict'] = {'user_phrase': 'USER', 'sentence': 'SENTENCE'}
        path.write_text(yaml.safe_dump(patch, allow_unicode=True), encoding='utf-8')
    engine = Engine(work)
    try:
        engine.deploy(('melt_eng',) + CHINESE)
        engine.start()
        engine.type('kuli')
        engine.choose('库')
        engine.choose('莉')
        assert engine.commit() == '库莉'
        engine.type('mu')
        engine.choose('姆')
        assert engine.commit() == '姆'
        engine.type('kulimu')
        assert engine.page()[0][0] == ('库莉姆', 'SENTENCE'), engine.page()
        engine.type('kulimu')
        engine.choose('库莉')
        assert engine.commit() is None
        engine.choose('姆')
        assert engine.commit() == '库莉姆'
        for schema in CHINESE:
            engine.select_schema(schema)
            engine.type('kulimu')
            assert engine.page()[0][0] == ('库莉姆', 'USER'), (schema, engine.page())
        engine.start()
        engine.type('kulimu')
        assert engine.page()[0][0] == ('库莉姆', 'USER')
        # An existing ambiguous word must be promoted by actual selection.
        engine.type('nage')
        engine.choose('哪个')
        assert engine.commit() == '哪个'
        engine.type('nage')
        assert engine.page()[0][0] == ('哪个', 'USER'), engine.page()
        print('PASS: partial selections, genuine user word, shared schemas, new session, frequency', flush=True)
    finally:
        engine.close()
    # Reinitialize the engine, proving persistence beyond a session cache.
    engine = Engine(work)
    try:
        engine.start()
        engine.type('kulimu')
        assert engine.page()[0][0] == ('库莉姆', 'USER')
        print('PASS: learned word survives engine restart', flush=True)
    finally:
        engine.close()


if __name__ == '__main__':
    main()
