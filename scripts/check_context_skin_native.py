"""Emulate generated frontend actions against real Rime; not an iOS UI test."""
import json
from pathlib import Path
import sys
import ctypes as C
from rime_native import Engine, prepare
from check_rime_learning import CHINESE
from rime_skin_actions import semantic_action

ROOT = Path(__file__).resolve().parents[1]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    doc = json.loads((ROOT / 'default/light/pinyinPortrait.yaml').read_text(encoding='utf-8'))
    work = prepare()
    engine = Engine(work)
    try:
        engine.deploy(('melt_eng',) + CHINESE)
        engine.start();engine.option('prediction',False)
        def word(code,text):
            engine.type(code);engine.choose(text);assert engine.commit()==text
        for _ in range(2):
            engine.key(0xffc7,5);word('nihc','你好');word('nage','哪个')
        engine.option('prediction',True)
        def prediction():
            engine.key(0xffc7,5);word('nihc','你好')
            assert engine.option('skin_context_prediction'),engine.page()
        output=[]
        engine.lib.RimeCommitComposition.argtypes=[C.c_size_t]
        def execute(action):
            if isinstance(action,dict) and 'combine' in action:
                for part in action['combine']:execute(part)
            elif isinstance(action,dict) and 'sendKeys' in action:
                code=int(action['sendKeys'].rsplit('F',1)[1]);assert engine.key(0xffbd+code,5)
            elif isinstance(action,dict) and 'symbol' in action:
                # Simulate the frontend flushing preedit before direct insertion.
                engine.lib.RimeCommitComposition(engine.session)
                text=engine.commit()
                if text:output.append(text)
                output.append(action['symbol'])
            elif isinstance(action,dict) and 'keyboardType' in action:
                pass
            elif isinstance(action,dict) and 'switchRimeSchema' in action:
                engine.select_schema(action['switchRimeSchema'])
            elif action=='enter':
                if not engine.key(0xff0d):output.append('\n')
            else:raise AssertionError(action)
        prediction();execute(doc['fButton']['swipeUpAction'])
        assert output==['＃'] and engine.page()[0]==[],(output,engine.page())
        prediction();grid=doc[doc['fButton']['hintSymbolsGridStyle']]
        option=next(doc[n] for n in grid['symbolRows'][0]
                    if semantic_action(doc[n]['action']) == {'symbol':'f'})
        output.clear();execute(option['action']);assert output==['f'],output
        output.clear();engine.type('nihc');execute(doc['fButton']['swipeUpAction'])
        assert output==['你好','＃'],output
        prediction();output.clear();execute(doc['enterButton']['action']);assert output==['\n'],output
        prediction();execute(doc['numericButton']['action']);assert engine.page()[0]==[]
        prediction();execute(doc['asciiModeButton']['action']);assert engine.commit() is None
        assert not engine.option('skin_context_prediction')
        # English receives only the signal processor, preserving its word workflow.
        engine.type('hel');assert engine.page()[0]
        output.clear();execute({'combine':[{'sendKeys':'Control+Shift+F9'}, {'symbol':','},
                                            {'sendKeys':'Control+Shift+F10'}]})
        assert output[-1]==',' and output.count(',')==1,output
        engine.select_schema('double_pinyin_flypy')
        prediction();assert engine.key(0xffc9,5) # direct hardware binding, no skin guard
        assert engine.commit() is None and not engine.option('skin_context_prediction')
        schemes=json.loads((ROOT/'default/light/schemesPortrait.yaml').read_text(encoding='utf-8'))
        for schema in CHINESE+('melt_eng',):
            execute(schemes['scheme'+schema]['action'])
            assert not engine.option('skin_context_prediction')
        print('PASS: generated symbol/hold/enter/numeric/language/picker guards; English candidates')
    finally:
        engine.close()
    print('Frontend actions emulated; iOS still requires device checks. Fixture:',work)


if __name__=='__main__':main()
