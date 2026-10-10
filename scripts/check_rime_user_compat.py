"""Static checks for the supplied RIME files; NOT a librime deployer.

Requires PyYAML and lupa (Lua 5.4). Reads user files without modifying them.
Only simulates the scalar/map/list-index patches used by this delivery.
"""
from copy import deepcopy
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
LOCAL_DEPS = ROOT / '.tools/rime-check-deps'
if LOCAL_DEPS.is_dir():
    sys.path.insert(0, str(LOCAL_DEPS))
import yaml
from lupa.lua54 import LuaRuntime


class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate mapping keys rather than silently dropping a patch."""


def unique_map(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f'duplicate YAML key: {key}')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_map)


def load(path, dictionary=False):
    if dictionary:
        lines = []
        with path.open(encoding='utf-8-sig') as source:
            for line in source:
                lines.append(line)
                if line.strip() == '...':
                    break
            else:
                raise ValueError(f'{path.name}: missing dictionary header terminator')
        text = ''.join(lines)
    else:
        text = path.read_text(encoding='utf-8-sig')
    return yaml.load(text, Loader=UniqueLoader)


def overlay(base, updates):
    result = deepcopy(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = overlay(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def patch_copy(source, patches):
    result = deepcopy(source)
    for path, value in patches.items():
        parts = path.split('/')
        current = result
        for part in parts[:-1]:
            if part.startswith('@'):
                current = current[int(part[1:])]
            else:
                current = current.setdefault(part, {})
        if parts[-1].startswith('@before '):
            current.insert(int(parts[-1].split()[1]), deepcopy(value))
        elif parts[-1] == '+':
            current.extend(deepcopy(value))
        else:
            current[parts[-1]] = deepcopy(value)
    return result


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_lua(path):
    runtime = LuaRuntime(unpack_returned_tuples=True)
    runtime.execute('''
        collected = {}
        function yield(cand) table.insert(collected, cand.text) end
        function Candidate(kind, first, last, text, comment)
            return {type=kind, start=first, _end=last, text=text, comment=comment}
        end
        function run_filter(filter, code, text, kind)
            collected = {}
            local input = {}
            function input:iter()
                local done = false
                return function()
                    if done then return nil end
                    done = true
                    return {text=text, type=kind, comment=''}
                end
            end
            filter(input, {engine={context={input=code}}})
            return collected[1], #collected
        end
    ''')
    function = runtime.execute(path.read_text(encoding='utf-8-sig'))
    cases = [
        ('hel', 'hello', 'completion', 'hello'),
        ('Hel', 'hello', 'completion', 'Hello'),
        ('HE', 'hello', 'completion', 'HELLO'),
        ('HEL', 'hello', 'completion', 'HELLO'),
        ('hello', 'hello', 'table', 'hello'),
        ('Hello', 'hello', 'table', 'Hello'),
        ('HELLO', 'hello', 'table', 'HELLO'),
        ('H', 'hello', 'completion', 'hello'),
        ('NASA', 'NASA', 'table', 'NASA'),
        ('PS', 'Photoshop', 'table', 'Photoshop'),
        ('He', 'hello world', 'completion', 'hello world'),
        ('He', '你好', 'completion', '你好'),
    ]
    for code, text, kind, expected in cases:
        actual, count = runtime.globals().run_filter(function, code, text, kind)
        require(actual == expected and count == 1, f'Lua candidate mismatch for {code}')
    return len(cases)


def check(folder):
    routes = json.loads((ROOT / 'default/jsonnet/Constants/InputRoutes.json').read_text(encoding='utf-8'))
    ids = [item['id'] for item in routes['schemes']]
    defaults = load(folder / 'default.yaml')
    selection = load(folder / 'default.custom.yaml')['patch']['schema_list']
    require([item['schema'] for item in selection] == ids, 'enabled list does not match skin picker')
    common = {
        'engine/processors/@before 0': 'lua_processor@*skin_scheme_memory',
        'ascii_composer/good_old_caps_lock': False,
        'ascii_composer/switch_key': {key: 'noop' for key in
            ('Caps_Lock', 'Shift_L', 'Shift_R', 'Control_L', 'Control_R')},
    }
    english_patch = {
        **common,
        'switches/@0/reset': -1,
        'translator/enable_completion': True,
        'translator/enable_sentence': False,
        'translator/enable_user_dict': True,
        'recognizer/patterns/uppercase': '^$',
        'engine/filters': ['lua_filter@*autocap_filter', 'uniquifier'],
    }
    chinese_patch = {**common,
        'engine/processors/@before 1': 'lua_processor@*skin_context_processor',
        'engine/translators/@before 0': 'lua_translator@*skin_context_translator',
        'engine/filters/+': ['lua_filter@*skin_context_filter'],
        'recognizer/patterns/skin_predict': '^›$',
        'switches/+': [
            {'name': 'context_learning', 'reset': 1, 'states': ['关闭关联学习', '开启关联学习']},
            {'name': 'prediction', 'reset': 1, 'states': ['关闭联想', '开启联想']}],
        'skin_context': {'timeout_seconds': 30, 'min_count': 2, 'max_predictions': 5}}
    schemas, dictionaries, lua_files, missing = set(), set(), set(), set()

    def dictionary(name):
        if name in dictionaries:
            return
        dictionaries.add(name)
        path = folder / (name + '.dict.yaml')
        if not path.is_file():
            missing.add(name + '.dict.yaml')
            return
        header = load(path, dictionary=True)
        require(header['name'] == name.rsplit('/', 1)[-1], f'dictionary name mismatch: {name}')
        for dependency in header.get('import_tables', []):
            dictionary(dependency)

    def dependencies(schema_id):
        if schema_id in schemas:
            return
        schemas.add(schema_id)
        path = folder / (schema_id + '.schema.yaml')
        if not path.is_file():
            missing.add(schema_id + '.schema.yaml')
            return
        doc = load(path)
        require(doc['schema']['schema_id'] == schema_id, f'schema ID mismatch: {schema_id}')
        for dependency in doc['schema'].get('dependencies', []):
            dependencies(dependency)
        for node in doc.values():
            if isinstance(node, dict) and node.get('dictionary'):
                dictionary(node['dictionary'])
            if isinstance(node, dict) and node.get('user_dict') and node.get('db_class') == 'stabledb':
                require((folder / (node['user_dict'] + '.txt')).is_file(), 'missing stabledb source')
        for category in ('processors', 'translators', 'filters'):
            for entry in doc['engine'].get(category, []):
                if entry.startswith('lua_') and '@*' in entry:
                    module = entry.split('@*', 1)[1].split('@', 1)[0]
                    require((folder / 'lua' / (module + '.lua')).is_file(), f'missing Lua module: {module}')
                    lua_files.add(module)

    for schema_id in ids:
        dependencies(schema_id)
        source = load(folder / (schema_id + '.schema.yaml'))
        require('__patch' not in source, f'{schema_id}: custom auto-patching would be disabled')
        require(source['switches'][0]['name'] == 'ascii_mode' and source['switches'][0]['reset'] == 0,
                f'{schema_id}: ASCII index/default changed')
        changes = load(folder / (schema_id + '.custom.yaml'))['patch']
        require(changes == (english_patch if schema_id == routes['english'] else chinese_patch),
                f'{schema_id}: unexpected patch scope')
        effective = deepcopy(source)
        # Resolve only import_preset components needed for these checks.
        for component in ('recognizer', 'key_binder', 'punctuator'):
            node = source.get(component, {})
            if node.get('import_preset') == 'default':
                effective[component] = overlay(defaults[component], node)
        effective = patch_copy(effective, changes)
        for field in ('speller', 'schema'):
            require(effective[field] == source[field], f'{schema_id}: altered {field}')
        if schema_id != routes['english']:
            for field in ('translator', 'melt_eng', 'cn_en'):
                require(effective[field] == source[field], f'{schema_id}: altered Chinese {field}')
            require(effective['switches'][:-2] == source['switches'], 'changed original switches')
            require(effective['engine']['processors'][2:] == source['engine']['processors'], 'changed original processors')
            require(effective['engine']['translators'][1:] == source['engine']['translators'], 'changed original translators')
            require(effective['engine']['filters'][:-1] == source['engine']['filters'], 'changed original filters')
            require(effective['engine']['segmentors'] == source['engine']['segmentors'], 'changed original segmentors')
        else:
            patterns = effective['recognizer']['patterns']
            for word in ('hello', 'Hello', 'HELLO', 'Hel'):
                require(not re.search(patterns['uppercase'], word), 'uppercase bypass still matches')
            require(patterns['email'] == defaults['recognizer']['patterns']['email'], 'changed email')
            require(patterns['url'] == defaults['recognizer']['patterns']['url'], 'changed URL')
    lua_files.add('autocap_filter')
    require((folder / 'lua/skin_scheme_memory.lua').is_file(), 'missing scheme-memory processor')
    require((folder / 'lua/skin_scheme_memory.lua').read_bytes() ==
            (ROOT / 'scripts/rime/skin_scheme_memory.lua').read_bytes(), 'stale scheme-memory processor copy')
    lua_files.add('skin_scheme_memory')
    for name in ('skin_context', 'skin_context_processor', 'skin_context_translator', 'skin_context_filter'):
        require((folder / 'lua' / (name + '.lua')).read_bytes() ==
                (ROOT / 'scripts/rime' / (name + '.lua')).read_bytes(), f'stale {name} copy')
        lua_files.add(name)
    return {'schemes': len(ids), 'dependency_schemas_present': len(schemas) - sum(name.endswith('.schema.yaml') for name in missing),
            'dictionary_headers': len(dictionaries) - sum(name.endswith('.dict.yaml') for name in missing),
            'missing_from_user_folder': sorted(missing), 'lua_modules_present': len(lua_files),
            'lua_candidate_cases': check_lua(folder / 'lua/autocap_filter.lua'),
            'native_deployment': 'not_run', 'iOS_device': 'not_tested'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', nargs='?', type=Path, default=ROOT / 'external_files/oh-my-rime')
    args = parser.parse_args()
    print(json.dumps(check(args.folder), ensure_ascii=False, indent=2))
