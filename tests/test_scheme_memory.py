"""Exercise the shipped Lua processor with isolated RIME API mocks."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools/rime-check-deps'))
try:
    from lupa.lua54 import LuaRuntime
    AVAILABLE = True
except ModuleNotFoundError:
    AVAILABLE = False
MODULE = ROOT / 'scripts/rime/skin_scheme_memory.lua'


@unittest.skipUnless(AVAILABLE and MODULE.is_file(), 'user-file Lua fixture/lupa unavailable')
class SchemeMemoryTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('''
            stored, writes, switches, commits = nil, 0, 0, 0
            writable, deployed = true, true
            rime_api = {get_user_data_dir=function() return '/private/user' end}
            function Config()
                local c = {}
                function c:load_from_file(path) self.value=stored end
                function c:get_string(key) return self.value end
                function c:set_string(key,id) self.value=id end
                function c:save_to_file(path)
                    if not writable then return false end
                    stored=self.value; writes=writes+1; return true
                end
                return c
            end
            function Schema(id)
                return {schema_id=id,config={get_string=function()
                    if deployed then return id end
                end}}
            end
            function make_env(id)
                local ctx = {}
                function ctx:commit() commits=commits+1 end
                function ctx:set_option(key,val) self[key]=val end
                local e={schema=Schema(id),context=ctx}
                function e:apply_schema(schema) self.schema=schema; switches=switches+1 end
                return {engine=e}
            end
            function key(release,ordinary)
                return {keycode=ordinary and 97 or 0xffc9,
                    release=function() return release or false end,
                    ctrl=function() return not ordinary end,
                    shift=function() return not ordinary end,
                    alt=function() return false end,super=function() return false end}
            end
        ''')
        self.module = self.lua.execute(MODULE.read_text(encoding='utf-8'))
        self.lua.globals().memory = self.module

    def run_lua(self, source):
        self.lua.execute(source)

    def test_all_chinese_pairs_and_selection_replaces_memory(self):
        self.run_lua('''
            for _,id in ipairs({'rime_mint','double_pinyin_flypy','rime_mint_flypy'}) do
                local env=make_env(id); memory.init(env)
                for i=1,3 do
                    assert(memory.func(key(),env)==1)
                    assert(env.engine.schema.schema_id=='melt_eng')
                    memory.init(env)
                    assert(memory.func(key(),env)==1)
                    assert(env.engine.schema.schema_id==id)
                    assert(env.engine.context.ascii_mode==false)
                end
                assert(stored==id)
            end
            assert(switches==18 and commits==18)
        ''')

    def test_cold_start_english_reads_persisted_chinese(self):
        self.run_lua('''
            stored='rime_mint'
            local env=make_env('melt_eng'); memory.init(env)
            assert(writes==0)
            assert(memory.func(key(),env)==1)
            assert(env.engine.schema.schema_id=='rime_mint')
        ''')

    def test_missing_or_unknown_memory_uses_default(self):
        for stored in ('nil', "'not_an_allowed_schema'"):
            self.setUp()
            self.run_lua(f"stored={stored}")
            self.run_lua('''
                local env=make_env('melt_eng'); memory.init(env)
                assert(memory.func(key(),env)==1)
                assert(env.engine.schema.schema_id=='double_pinyin_flypy')
            ''')

    def test_release_normal_keys_and_missing_target_do_not_switch(self):
        self.run_lua('''
            local env=make_env('rime_mint'); memory.init(env)
            assert(memory.func(key(true),env)==2)
            assert(memory.func(key(false,true),env)==2)
            deployed=false
            assert(memory.func(key(),env)==2)
            assert(switches==0 and commits==0)
        ''')

    def test_write_failure_keeps_session_memory_and_same_id_avoids_writes(self):
        self.run_lua('''
            local env=make_env('rime_mint'); memory.init(env)
            memory.init(env); assert(writes==1)
            writable=false
            env=make_env('rime_mint_flypy'); memory.init(env)
            assert(stored=='rime_mint')
            memory.func(key(),env); memory.init(env); memory.func(key(),env)
            assert(env.engine.schema.schema_id=='rime_mint_flypy')
        ''')


if __name__ == '__main__':
    unittest.main()
