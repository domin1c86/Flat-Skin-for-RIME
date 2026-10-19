"""Distribution checks must inspect installed content, not only archive names."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_skin import SkinError, compile_skin, package_skin

HAS_PILLOW = importlib.util.find_spec('PIL') is not None
if HAS_PILLOW:
    from build_release_variants import build_release, check_package, write_bundle


class CompilationOutputTests(unittest.TestCase):
    def test_generated_config_uses_lf_on_every_platform(self):
        result = SimpleNamespace(returncode=0, stderr='', stdout=json.dumps({'config.yaml': '{"name":"test"}'}))
        with tempfile.TemporaryDirectory() as temporary, patch('build_skin.subprocess.run', return_value=result):
            skin = Path(temporary)
            compile_skin(Path('unused'), skin)
            self.assertEqual((skin / 'config.yaml').read_bytes(), b'{"name":"test"}\n')


@unittest.skipUnless(HAS_PILLOW, 'Pillow unavailable')
class ReleaseVariantTests(unittest.TestCase):
    def test_invalid_padding_rejected_before_any_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'output'
            for values in ([], [True], [-1], [25], [1.5]):
                with self.subTest(values=values), self.assertRaises(SkinError):
                    build_release(output, Path('unused'), values)
                self.assertFalse(output.exists())

    def test_bundle_has_exact_names_and_bytes_and_rejects_duplicate_names(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            files = [folder / 'first.cskin', folder / '审核.md']
            for index, file in enumerate(files):
                file.write_bytes(str(index).encode())
            output = folder / 'bundle.zip'
            write_bundle(output, files)
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(archive.namelist(), [file.name for file in files])
                self.assertEqual(archive.read('审核.md'), b'1')
            with self.assertRaisesRegex(SkinError, 'duplicate'):
                write_bundle(folder / 'invalid.zip', [files[0], files[0]])
            self.assertFalse((folder / 'invalid.zip').exists())

    def test_package_content_detects_wrong_family_padding_and_stale_catalog(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            original = folder / 'normal.cskin'
            package_skin(original)
            self.assertEqual(check_package(original, 0, False), 28)
            for padding, experimental in ((8, False), (0, True)):
                with self.subTest(padding=padding, experimental=experimental), self.assertRaises(SkinError):
                    check_package(original, padding, experimental)
            broken = folder / 'broken.cskin'
            with zipfile.ZipFile(original) as source, zipfile.ZipFile(broken, 'w') as target:
                for name in source.namelist():
                    contents = source.read(name)
                    if name.endswith('/light/numericPortrait.yaml'):
                        document = json.loads(contents)
                        document['numericOperatorData'] = ['+', '-', '*', '/']
                        contents = json.dumps(document).encode()
                    target.writestr(name, contents)
            with self.assertRaisesRegex(SkinError, 'stale numeric list'):
                check_package(broken, 0, False)


if __name__ == '__main__':
    unittest.main()
