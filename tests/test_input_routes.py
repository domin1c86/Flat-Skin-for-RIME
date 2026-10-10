"""Configuration graph checks for explicit keyboard + scheme selection."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_skin import validate_action, SkinError
from audit_letter_symbols import inspect_routes


def load(name,theme='light'):
    return json.loads((ROOT/'default'/theme/(name+'.yaml')).read_text(encoding='utf-8'))


class InputRouteTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads((ROOT/'default/config.yaml').read_text(encoding='utf-8'))
        self.routes=json.loads((ROOT/'default/jsonnet/Constants/InputRoutes.json').read_text(encoding='utf-8'))

    def test_all_scheme_and_language_routes_and_returns(self):
        self.assertEqual(inspect_routes(self.config,self.routes),[])

    def test_primary_geometry_and_language_specific_initial_actions(self):
        for theme in ('light','dark'):
            for orientation in ('Portrait','Landscape'):
                cn,en=load('pinyin'+orientation,theme),load('alphabetic'+orientation,theme)
                self.assertEqual(cn['keyboardLayout'],en['keyboardLayout'])
                for letter in 'qwertyuiopasdfghjklzxcvbnm':
                    for field in ('size','bounds','backgroundStyle','action','uppercasedStateAction'):
                        self.assertEqual(cn[letter+'Button'].get(field),en[letter+'Button'].get(field))
                    self.assertEqual(cn[letter+'Button']['notification'],[])
                    self.assertEqual(en[letter+'Button']['notification'],[])
                self.assertEqual(cn['fButton']['swipeUpAction'],{'symbol':'＃'})
                self.assertEqual(en['fButton']['swipeUpAction'],{'symbol':'#'})

    def test_picker_ids_and_labels_have_exactly_four_supported_routes(self):
        ids={item['id'] for item in self.routes['schemes']}
        self.assertEqual(ids,{'double_pinyin_flypy','rime_mint','rime_mint_flypy','melt_eng'})
        for orientation in ('Portrait','Landscape'):
            doc=load('schemes'+orientation)
            cells=[row['HStack']['subviews'][0]['Cell'] for row in doc['keyboardLayout']]
            self.assertEqual(cells,['scheme'+item['id'] for item in self.routes['schemes']]+['schemeBack'])
            for item in self.routes['schemes']:
                node=doc['scheme'+item['id']]
                self.assertEqual(doc[node['foregroundStyle']]['text'],item['label'])

    def test_keyboard_route_mapping_is_checked_not_just_symbols(self):
        broken=deepcopy(self.config)
        broken['alphabetic']['iPhone']['portrait']='pinyinPortrait'
        self.assertTrue(inspect_routes(broken,self.routes))

    def test_scheme_action_requires_valid_nonempty_string(self):
        validate_action({'combine':[{'keyboardType':'alphabetic'},{'switchRimeSchema':'melt_eng'}]},'route')
        for value in ('',None,[],True):
            with self.assertRaises(SkinError):
                validate_action({'switchRimeSchema':value},'route')

    def test_language_toggle_uses_reserved_memory_processor_key(self):
        self.assertEqual(self.routes['toggleKeys'], 'Control+Shift+F12')
        for orientation in ('Portrait', 'Landscape'):
            for kind, target in (('pinyin', 'alphabetic'), ('alphabetic', 'pinyin')):
                action = load(kind + orientation)['asciiModeButton']['action']
                self.assertEqual(action, {'combine': [
                    {'keyboardType': target}, {'sendKeys': self.routes['toggleKeys']}]})
                validate_action(action, 'memory toggle')
        with self.assertRaises(SkinError):
            validate_action({'sendKeys': ''}, 'empty keys')

    def test_english_comma_has_complete_single_action_hold_and_both_statuses(self):
        from render_skin_preview import selected, effective_button
        self.assertEqual(self.routes['candidateToggleKeys'], 'Control+Shift+F11')
        for theme in ('light', 'dark'):
            for orientation in ('Portrait', 'Landscape'):
                doc = load('alphabetic' + orientation, theme)
                original = doc['chineseCommaButton']
                self.assertNotIn('repeatAction', original)
                for ascii_mode in (False, True):
                    for notified in (False, True):
                        node = effective_button(doc, original, ascii_mode, notified)
                        self.assertEqual(node['action'], {'symbol': ','})
                        for field in ('size', 'backgroundStyle', 'hintSymbolsGridStyle', 'hintSymbolsStyle', 'swipeUpAction'):
                            self.assertEqual(node[field], original[field])
                        refs = selected(node['foregroundStyle'], ascii_mode)
                        self.assertEqual(refs, ['phoneEnglishCommaLabel',
                            'phoneCandidatesOffLabel' if ascii_mode else 'phoneCandidatesOnLabel'])
                        self.assertEqual(doc[refs[0]]['text'], ',')
                        self.assertEqual(doc[refs[1]]['fontSize'], 9)
                grid = doc[original['hintSymbolsGridStyle']]
                self.assertEqual(grid['size'], {'width': 88, 'height': 44})
                self.assertEqual(grid['symbolRows'], [['phoneCandidateToggleOption']])
                option = doc[grid['symbolRows'][0][0]]
                self.assertEqual(option['action'], {'sendKeys': self.routes['candidateToggleKeys']})
                self.assertEqual(doc[option['foregroundStyle']]['fontSize'], 12)
                self.assertNotIn('hintSymbolsGridStyle', load('pinyin' + orientation, theme)['chineseCommaButton'])


if __name__=='__main__':
    unittest.main()
