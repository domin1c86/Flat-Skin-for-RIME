"""Real-engine integration checks for contextual ranking and post predictions."""
import sys
import subprocess
from pathlib import Path
from rime_native import Engine, prepare
from check_rime_learning import CHINESE


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) == 3 and sys.argv[1] == '--resume':
        work = Path(sys.argv[2]).resolve()
        assert work.is_relative_to(Path(__file__).resolve().parents[1] / '.tools')
        engine = Engine(work)
        try:
            engine.start('rime_mint');engine.option('prediction',False)
            engine.type('nihao');engine.choose('你好');assert engine.commit()=='你好'
            engine.type('nage');assert engine.page()[0][0][0]=='哪个',engine.page()
            print('PASS: process restart + full-pinyin shared context database',flush=True)
        finally:
            engine.close()
        return
    work = prepare()
    engine = Engine(work)
    try:
        engine.deploy(('melt_eng',) + CHINESE)
        engine.start()
        assert engine.option('context_learning') and engine.option('prediction')
        engine.option('prediction', False)
        def reset(): engine.key(0xffc7, 5)
        def select(code,word):
            engine.type(code);engine.choose(word);assert engine.commit()==word
        for _ in range(2):
            reset();select('nihc','你好');select('nage','哪个')
            reset();select('xpxp','谢谢');select('nage','那个')
        reset();select('nihc','你好');engine.type('nage')
        assert engine.page()[0][0][0]=='哪个', engine.page()
        reset();select('xpxp','谢谢');engine.type('nage')
        assert engine.page()[0][0][0]=='那个', engine.page()
        print('PASS: same code ranked differently by personal context',flush=True)
        # Choosing reordered candidates still updates the native user dictionary.
        engine.choose('那个');assert engine.commit()=='那个'
        reset();engine.option('prediction',True);select('nihc','你好')
        print('prediction page',engine.page(),flush=True)
        assert engine.option('skin_context_prediction')
        assert engine.page()[0][0][0]=='哪个',engine.page()
        assert engine.key(32);assert engine.commit()==' '
        assert engine.page()[0]==[] and not engine.option('skin_context_prediction')
        reset();select('nihc','你好');assert engine.key(0xff08)
        assert engine.commit() is None and engine.page()[0]==[]
        reset();select('nihc','你好');engine.type('nage',clear=False)
        assert engine.page()[0][0][0]=='哪个',engine.page()
        engine.choose('哪个');assert engine.commit()=='哪个'
        reset();select('nihc','你好');engine.choose('哪个');assert engine.commit()=='哪个'
        assert not engine.option('skin_context_prediction')
        print('PASS: post prediction, literal space, backspace, new input, one round',flush=True)
        engine.option('prediction',False)
        engine.start();engine.option('prediction',False)
        select('xpxp','谢谢');engine.type('nage');assert engine.page()[0][0][0]=='那个'
        engine.option('context_learning',False)
        engine.type('li');engine.choose('莉');assert engine.commit()=='莉'
        print('PASS: disabled learning preserves candidate pagination',flush=True)
        print('PASS: new session retains associations',flush=True)
    finally:
        engine.close()
    subprocess.run([sys.executable, __file__, '--resume', str(work)], check=True)
    assert (work / 'lua/skin_context.userdb').is_dir()
    assert not (work / 'skin_context.userdb').exists()
    print('PASS: custom association DB outside native user-dictionary enumeration',flush=True)
    print('Isolated database:',work)


if __name__ == '__main__':
    main()
