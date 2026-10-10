from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools/rime-check-deps'))
try:
    from lupa.lua54 import LuaRuntime
except ImportError:
    LuaRuntime = None


@unittest.skipUnless(LuaRuntime, 'lupa unavailable')
class ContextLearningTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('''
            clock, store, writes, closes, opens, raw, option_writes = 100, {}, 0, 0, 0, {}, 0
            failing = false
            os.time = function() return clock end
            rime_api = {get_user_data_dir=function() return 'fixture' end}
            function LevelDb()
                local db={}
                function db:open() opens=opens+1; return not failing end
                function db:close() closes=closes+1 end
                function db:fetch(key) if failing then error('unavailable') end; return store[key] end
                function db:update(key,value)
                    if failing then return false end
                    store[key]=value; writes=writes+1; return true
                end
                function db:erase(key) store[key]=nil; writes=writes+1; return true end
                return db
            end
            function signal()
                local n={callbacks={}}
                function n:connect(f)
                    local token={f=f}; self.callbacks[#self.callbacks+1]=token
                    function token:disconnect() self.f=nil end
                    return token
                end
                function n:emit(...)
                    for _,t in ipairs(self.callbacks) do if t.f then t.f(...) end end
                end
                return n
            end
            function make_env()
                local c={input='',props={},options={context_learning=true,prediction=false}}
                c.commit_notifier=signal(); c.update_notifier=signal(); c.option_update_notifier=signal()
                function c:get_property(k) return self.props[k] or '' end
                function c:set_property(k,v) self.props[k]=v end
                function c:get_option(k) return self.options[k] or false end
                function c:set_option(k,v)
                    self.options[k]=v;option_writes=option_writes+1
                    self.option_update_notifier:emit(self,k)
                end
                function c:get_commit_text() return self.text end
                function c:clear() self.input='';self.update_notifier:emit(self) end
                function c:push_input(t) self.input=t;self.update_notifier:emit(self) end
                local e={context=c,schema={schema_id='double_pinyin_flypy',config={}}}
                function e.schema.config:get_int() return nil end
                function e:commit_text(t) raw[#raw+1]=t end
                return {engine=e}
            end
            function commit(env,text)
                local c=env.engine.context;c.text=text;c.commit_notifier:emit(c);c:clear()
            end
            function key(code,repr,modifier)
                return {keycode=code, repr=function()return repr or ''end,
                    release=function()return false end,ctrl=function()return modifier or false end,
                    shift=function()return modifier or false end,alt=function()return false end,
                    super=function()return false end}
            end
            function Candidate(kind,start,finish,text,comment)
                local c={type=kind,start=start,_end=finish,text=text,comment=comment}
                function c:get_genuine() return self end
                return c
            end
            result={}
            function yield(c) result[#result+1]=c end
            function rank(env,candidates)
                result={};local inp={}
                function inp:iter()
                    local i=0;return function()i=i+1;return candidates[i]end
                end
                mod.filter.func(inp,env);return result
            end
            function break_context(env) mod.processor.func(key(0xffc7,'',true),env) end
            function pair(env,a,b) break_context(env);commit(env,a);commit(env,b) end
        ''')
        self.lua.globals().mod = self.lua.execute((ROOT / 'scripts/rime/skin_context.lua').read_text(encoding='utf-8'))
        self.lua.execute("env=make_env();mod.processor.init(env)")

    def test_threshold_context_specific_ranking_and_candidate_identity(self):
        self.lua.execute('''
            a=Candidate('user_phrase',0,4,'哪个','old'); b=Candidate('phrase',0,4,'那个','note')
            pair(env,'谢谢','那个');break_context(env);commit(env,'谢谢')
            assert(rank(env,{a,b})[1]==a)
            pair(env,'谢谢','那个');break_context(env);commit(env,'谢谢')
            local r=rank(env,{a,b});assert(r[1]==b and r[2]==a and b.comment=='note')
            pair(env,'你好','哪个');pair(env,'你好','哪个');break_context(env);commit(env,'你好')
            assert(rank(env,{b,a})[1]==a)
            local short=Candidate('phrase',0,2,'那个','')
            assert(rank(env,{a,short})[1]==a)
        ''')

    def test_timeout_punctuation_ascii_and_disable_break_associations(self):
        self.lua.execute('''
            commit(env,'你好');clock=clock+31;commit(env,'那个');assert(writes==0)
            break_context(env);commit(env,'你好');commit(env,'。');commit(env,'那个');assert(writes==0)
            break_context(env);commit(env,'你好');env.engine.context:set_option('ascii_mode',true)
            env.engine.context:set_option('ascii_mode',false);commit(env,'那个');assert(writes==0)
            env.engine.context:set_option('context_learning',false);commit(env,'你好');commit(env,'那个')
            assert(writes==0 and not env.engine.context:get_option('skin_context_prediction'))
        ''')

    def test_recent_host_backspace_rolls_back_only_latest_association(self):
        self.lua.execute('''
            pair(env,'你好','那个');local original=store['你好']
            pair(env,'你好','那个');assert(store['你好']~=original)
            assert(mod.processor.func(key(0xff08,'BackSpace'),env)==2)
            assert(store['你好']==original)
            commit(env,'哪个');assert(store['那个']==nil)
            pair(env,'你好','那个');clock=clock+4
            mod.processor.func(key(0xff08,'BackSpace'),env);assert(store['你好']~=original)
        ''')

    def test_predictions_one_round_space_cancel_and_letter_restart(self):
        self.lua.execute('''
            pair(env,'你好','那个');pair(env,'你好','那个');break_context(env)
            env.engine.context:set_option('prediction',true);commit(env,'你好')
            assert(env.engine.context.input=='›')
            result={};mod.translator.func('›',{start=0,_end=3},env)
            assert(#result==1 and result[1].text=='那个')
            assert(mod.processor.func(key(0xff08,'BackSpace'),env)==1)
            assert(env.engine.context.input=='' and #raw==0)
            break_context(env);commit(env,'你好');assert(mod.processor.func(key(32,'space'),env)==1)
            assert(raw[1]==' ' and #raw==1 and env.engine.context.input=='')
            break_context(env);commit(env,'你好');assert(mod.processor.func(key(110,'n'),env)==2)
            assert(env.engine.context.input=='');commit(env,'那个')
            assert(env.engine.context.input=='')
            pair(env,'那个','谢谢');pair(env,'那个','谢谢');break_context(env);commit(env,'你好')
            commit(env,'那个');assert(env.engine.context.input=='') -- predicted submission ends chain
        ''')

    def test_database_failure_and_shared_lifecycle(self):
        self.lua.execute('''
            other=make_env();mod.processor.init(other);assert(opens==1)
            pair(env,'你好','那个');break_context(other);commit(other,'你好')
            pair(env,'你好','那个');assert(store['你好']~=nil)
            failing=true;pair(env,'你好','哪个');assert(env.engine.context.input=='')
            mod.processor.fini(env);assert(closes==0)
            mod.processor.fini(other);assert(closes==1)
            local before=writes;env.engine.context.commit_notifier:emit(env.engine.context)
            assert(writes==before)
        ''')

    def test_disabled_learning_does_not_rewrite_options_during_normal_keys(self):
        self.lua.execute('''
            env.engine.context:set_option('context_learning',false)
            local before=option_writes
            env.engine.context.input='li'
            for i=1,5 do assert(mod.processor.func(key(0xff56,'Page_Down'),env)==2) end
            assert(option_writes==before)
        ''')
