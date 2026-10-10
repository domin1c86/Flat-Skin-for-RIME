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


if __name__=='__main__':
    unittest.main()
