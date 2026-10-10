"""Optional checks for the private user-file fixture and companion patches."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
try:
    from check_rime_user_compat import check, patch_copy, UniqueLoader, yaml
    AVAILABLE = True
except ModuleNotFoundError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, 'optional user-file checks need PyYAML + lupa')
class UserCompatTests(unittest.TestCase):
    @unittest.skipUnless((ROOT / 'external_files/oh-my-rime/default.yaml').is_file(),
                         'private user files are not committed with the skin')
    def test_supplied_schemes_dependencies_and_actual_lua(self):
        result = check(ROOT / 'external_files/oh-my-rime')
        self.assertEqual(result['schemes'], 4)
        self.assertEqual(result['lua_candidate_cases'], 12)
        self.assertEqual(result['native_deployment'], 'not_run')

    def test_duplicate_patch_key_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate YAML key'):
            yaml.load('patch:\n  x: 1\n  x: 2\n', Loader=UniqueLoader)

    def test_bad_switch_index_fails_and_source_is_not_mutated(self):
        source = {'switches': [{'name': 'ascii_mode', 'reset': 1}]}
        copy = patch_copy(source, {'switches/@0/reset': 0})
        self.assertEqual(copy['switches'][0]['reset'], 0)
        self.assertEqual(source['switches'][0]['reset'], 1)
        with self.assertRaises(IndexError):
            patch_copy(source, {'switches/@9/reset': 0})


if __name__ == '__main__':
    unittest.main()
