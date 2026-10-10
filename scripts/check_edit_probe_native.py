"""Capture actual Rime traces, then test conservative suffix reconstruction.

Host editing is not simulated as observed engine data: ambiguous host outcomes
are reported separately. The diagnostic is only installed in this fresh fixture.
"""
from pathlib import Path
import json
import shutil
import sys
from check_rime_user_compat import load, yaml
from rime_native import Engine, prepare
from manage_personal_dict import edit
from edit_learning_probe import analyze
from check_rime_learning import CHINESE

ROOT = Path(__file__).resolve().parents[1]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    work = prepare()
    edit(work,'add','库里姆','ku li mu')
    shutil.copy2(ROOT/'scripts/rime/skin_edit_probe.lua',work/'lua/skin_edit_probe.lua')
    for schema in CHINESE:
        path=work/(schema+'.custom.yaml');patch=load(path)
        patch['patch']['engine/processors/@before 2']='lua_processor@*skin_edit_probe'
        patch['patch']['skin_edit_probe/enabled']=True
        # Keep single-character selection bounded in this diagnostic fixture.
        patch['patch']['translator/enable_word_completion']=False
        path.write_text(yaml.safe_dump(patch,allow_unicode=True),encoding='utf-8')
    trace=work/'edit-probe.jsonl'
    engine=Engine(work)
    results={}
    try:
        engine.deploy(('melt_eng',)+CHINESE)
        def begin():
            engine.start('rime_mint');engine.option('context_learning',False)
            return len(trace.read_text(encoding='utf-8').splitlines())
        def word(code,text):
            engine.type(code);engine.choose(text);assert engine.commit()==text
        def finish(start):
            events=[json.loads(line) for line in trace.read_text(encoding='utf-8').splitlines()[start:]]
            return analyze(events),events
        start=begin();word('nage','哪个');engine.key(0xff08);engine.key(0xff08);word('nage','那个')
        result,events=finish(start);assert result['assumed_text']=='那个' and not result['learn_allowed']
        results['homophone_suffix']=result
        start=begin();word('kulimu','库里姆');engine.key(0xff08);engine.key(0xff08)
        word('li','莉');word('mu','姆');result,events=finish(start)
        assert result['assumed_text']=='库莉姆' and not result['learn_allowed'];results['name_suffix']=result
        start=begin();word('kulimu','库里姆');engine.key(0xff51);engine.key(0xff08);word('li','莉')
        result,events=finish(start);assert result['status']=='unsupported_edit';results['cursor_edit']=result
        start=begin();word('kulimu','库里姆');word('li','莉');result,events=finish(start)
        assert result['assumed_text']=='库里姆莉' and not result['learn_allowed']
        results['selection_ambiguity']={'observed':result,
            'compatible_host_results':['库里姆莉','库莉姆'],
            'missing_event':'宿主选区变化不会由普通 Rime 提交事件说明'}
        assert all('host_text' not in row and 'host_cursor' not in row for row in events)
        print('PASS: real Rime suffix and cursor traces; ambiguous selection; no prototype dictionary writes')
    finally:
        engine.close()
    (work/'edit-probe-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Diagnostic traces and results:',work)


if __name__=='__main__':main()
