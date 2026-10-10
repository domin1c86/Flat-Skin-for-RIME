from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from edit_learning_probe import analyze


def commit(text, code='', time=100):
    return {'event':'commit','text':text,'code':code,'time':time}


def backspace(input='', time=101):
    return {'event':'key','key':'BackSpace','preedit_input':input,'time':time}


class EditProbeTests(unittest.TestCase):
    def test_recent_suffix_reconstruction_is_never_a_verified_new_word(self):
        result=analyze([commit('库里姆','kulimu'),backspace(),backspace(),
                        commit('莉','li',101),commit('姆','mu',101)])
        self.assertEqual(result['assumed_text'],'库莉姆')
        self.assertEqual(result['status'],'partial_reconstruction')
        self.assertFalse(result['learn_allowed'])
        self.assertEqual(result['writes_to_user_dictionary'],0)

    def test_preedit_backspace_is_not_a_host_deletion(self):
        result=analyze([commit('哪个'),backspace('nage'),commit('那个')])
        self.assertEqual(result['assumed_text'],'哪个那个')
        self.assertEqual(result['status'],'commit_sequence_only')

    def test_homophone_replacement_and_continuous_suffix_edits(self):
        result=analyze([commit('哪个'),backspace(),backspace(),commit('那个',time=101)])
        self.assertEqual(result['assumed_text'],'那个')
        result=analyze([commit('库里姆'),backspace(),backspace(),commit('莉姆',time=101),
                        backspace(time=102),backspace(time=102),commit('里姆',time=102)])
        self.assertEqual(result['assumed_text'],'库里姆')
        self.assertFalse(result['learn_allowed'])

    def test_cursor_selection_focus_external_change_and_timeout_refuse_reconstruction(self):
        for event in ({'event':'key','key':'Left'}, {'event':'host_selection'},
                      {'event':'host_focus_changed'}, {'event':'external_text_changed'},
                      {'event':'context_boundary'}, backspace(time=104)):
            with self.subTest(event=event):
                result=analyze([commit('库里姆'),event,commit('莉')])
                self.assertIsNone(result['assumed_text'])
                self.assertFalse(result['learn_allowed'])

    def test_identical_rime_commits_are_compatible_with_different_host_results(self):
        trace=[commit('库里姆','kulimu'),commit('莉','li')]
        append_world='库里姆'+'莉'
        replace_world='库里姆'.replace('里','莉')
        self.assertNotEqual(append_world,replace_world)
        self.assertEqual(analyze(trace)['assumed_text'],append_world)
        self.assertFalse(analyze(trace)['learn_allowed'])

    def test_new_session_drops_previous_shadow(self):
        result=analyze([commit('库里姆'),{'event':'init'},commit('莉')])
        self.assertEqual(result['assumed_text'],'莉')
