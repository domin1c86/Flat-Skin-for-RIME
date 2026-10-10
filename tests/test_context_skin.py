"""Validate real generated guards, independently of semantic-action audits."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from rime_skin_actions import CANCEL, RESET, semantic_action


def actions(value):
    if isinstance(value, list):
        for child in value:
            yield from actions(child)
    elif isinstance(value, dict):
        for key, child in value.items():
            if key != 'notificationKeyboardAction' and (key == 'action' or key.endswith('Action')):
                yield child
            else:
                yield from actions(child)


def boundary(action):
    if isinstance(action, str):
        return action in {'enter', 'dismissKeyboard', 'nextKeyboard', 'returnPrimaryKeyboard',
                          'returnLastKeyboard', 'moveCursorBackward', 'moveCursorForward'}
    if isinstance(action, dict):
        if 'combine' in action:
            return any(boundary(a) for a in action['combine'])
        return any(k in action for k in ('symbol', 'keyboardType', 'switchRimeSchema')) or (
            action.get('shortcut') in {'#showPasteboardView', '#toggleScriptView', '#keyboardMenu',
                '#方案切换', '#行首', '#行尾', '#换行', '#Enter', '#重输'})
    return False


class ContextSkinTests(unittest.TestCase):
    def test_all_frontend_boundaries_guarded_once_with_original_middle_action(self):
        count = 0
        for theme in ('light', 'dark'):
            for path in (ROOT / 'default' / theme).glob('*.yaml'):
                doc = json.loads(path.read_text(encoding='utf-8'))
                for action in actions(doc):
                    original = semantic_action(action)
                    if boundary(original):
                        with self.subTest(path=path.name, action=original):
                            self.assertNotEqual(original, action)
                            self.assertEqual(action['combine'], [CANCEL, original, RESET])
                            # No second guard is hidden inside the original action.
                            self.assertEqual(semantic_action(original), original)
                            count += 1
        self.assertGreater(count, 500)

    def test_plain_letters_and_space_unchanged_and_prediction_space_is_labelled(self):
        for theme in ('light', 'dark'):
            for name in ('pinyinPortrait', 'pinyinLandscape', 'alphabeticPortrait', 'alphabeticLandscape'):
                doc = json.loads((ROOT / 'default' / theme / (name + '.yaml')).read_text(encoding='utf-8'))
                self.assertEqual(doc['qButton']['action'], {'character': 'q'})
                self.assertEqual(doc['spaceButton']['action'], 'space')
                notice = doc['skinPredictionSpaceNotification']
                self.assertEqual(notice['rimeOptionName'], 'skin_context_prediction')
                self.assertEqual(notice['foregroundStyle'], doc['spaceButton']['foregroundStyle'])
                self.assertEqual(notice['action'], 'space')

    def test_signal_protocol_matches_lua_and_invalid_guard_is_not_silently_unwrapped(self):
        routes = json.loads((ROOT / 'default/jsonnet/Constants/InputRoutes.json').read_text(encoding='utf-8'))
        self.assertEqual(routes['contextCancelKeys'], CANCEL['sendKeys'])
        self.assertEqual(routes['contextResetKeys'], RESET['sendKeys'])
        invalid = {'combine': [RESET, {'symbol': '，'}, CANCEL]}
        self.assertEqual(semantic_action(invalid), invalid)
