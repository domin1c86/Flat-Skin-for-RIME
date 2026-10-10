"""Small ctypes harness for isolated tests against the installed Weasel engine.

Never opens the supplied user's databases. All deployment and learning happen
in a new .tools directory, retained so failures can be inspected.
"""
import ctypes as C
import os
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]


class Traits(C.Structure):
    _fields_ = [('data_size', C.c_int)] + [(k, C.c_char_p) for k in (
        'shared_data_dir', 'user_data_dir', 'distribution_name',
        'distribution_code_name', 'distribution_version', 'app_name')]
    _fields_ += [('modules', C.POINTER(C.c_char_p)), ('min_log_level', C.c_int)]
    _fields_ += [(k, C.c_char_p) for k in ('log_dir', 'prebuilt_data_dir', 'staging_dir')]


class Composition(C.Structure):
    _fields_ = [(k, C.c_int) for k in ('length', 'cursor_pos', 'sel_start', 'sel_end')]
    _fields_ += [('preedit', C.c_char_p)]


class Candidate(C.Structure):
    _fields_ = [('text', C.c_char_p), ('comment', C.c_char_p), ('reserved', C.c_void_p)]


class Menu(C.Structure):
    _fields_ = [(k, C.c_int) for k in (
        'page_size', 'page_no', 'is_last_page', 'highlighted_candidate_index', 'num_candidates')]
    _fields_ += [('candidates', C.POINTER(Candidate)), ('select_keys', C.c_char_p)]


class Context(C.Structure):
    _fields_ = [('data_size', C.c_int), ('composition', Composition), ('menu', Menu),
               ('commit_text_preview', C.c_char_p), ('select_labels', C.POINTER(C.c_char_p))]


class Commit(C.Structure):
    _fields_ = [('data_size', C.c_int), ('text', C.c_char_p)]


def prepare(source=ROOT / 'external_files/oh-my-rime'):
    (ROOT / '.tools').mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='rime-learning-', dir=ROOT / '.tools'))
    for p in source.glob('*.yaml'):
        if p.name not in ('user.yaml', 'installation.yaml'):
            shutil.copy2(p, work / p.name)
    for name in ('lua', 'dicts', 'opencc'):
        shutil.copytree(source / name, work / name)
    return work


class Engine:
    def __init__(self, work, native=Path('C:/Program Files/Rime/weasel-0.17.4')):
        self.work = Path(work)
        self.directory = os.add_dll_directory(str(native))
        self.lib = lib = C.CDLL(str(native / 'rime.dll'))
        self.session = 0
        self.traits = t = Traits()
        t.data_size = C.sizeof(Traits) - C.sizeof(C.c_int)
        t.shared_data_dir = str(native / 'data').encode()
        t.user_data_dir = str(work).encode()
        t.log_dir = str(work).encode()
        t.app_name = b'rime.isolated_learning_check'
        t.min_log_level = 2
        signatures = {
            'RimeSetup': ([C.POINTER(Traits)], None),
            'RimeInitialize': ([C.POINTER(Traits)], None),
            'RimeDeployerInitialize': ([C.POINTER(Traits)], None),
            'RimeDeployConfigFile': ([C.c_char_p, C.c_char_p], C.c_int),
            'RimeDeploySchema': ([C.c_char_p], C.c_int),
            'RimeCreateSession': ([], C.c_size_t),
            'RimeDestroySession': ([C.c_size_t], C.c_int),
            'RimeSelectSchema': ([C.c_size_t, C.c_char_p], C.c_int),
            'RimeSetOption': ([C.c_size_t, C.c_char_p, C.c_int], None),
            'RimeGetOption': ([C.c_size_t, C.c_char_p], C.c_int),
            'RimeProcessKey': ([C.c_size_t, C.c_int, C.c_int], C.c_int),
            'RimeClearComposition': ([C.c_size_t], None),
            'RimeSelectCandidateOnCurrentPage': ([C.c_size_t, C.c_int], C.c_int),
            'RimeGetContext': ([C.c_size_t, C.POINTER(Context)], C.c_int),
            'RimeFreeContext': ([C.POINTER(Context)], C.c_int),
            'RimeGetCommit': ([C.c_size_t, C.POINTER(Commit)], C.c_int),
            'RimeFreeCommit': ([C.POINTER(Commit)], C.c_int),
            'RimeFinalize': ([], None),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(lib, name)
            fn.argtypes, fn.restype = args, result
        lib.RimeSetup(C.byref(t))
        lib.RimeInitialize(C.byref(t))
        lib.RimeDeployerInitialize(C.byref(t))

    def deploy(self, schemas):
        assert self.lib.RimeDeployConfigFile(b'default.yaml', b'config_version')
        for schema in schemas:
            assert self.lib.RimeDeploySchema(str(self.work / (schema + '.schema.yaml')).encode()), schema

    def start(self, schema='double_pinyin_flypy'):
        if self.session:
            self.lib.RimeDestroySession(self.session)
        self.session = self.lib.RimeCreateSession()
        assert self.session
        self.select_schema(schema)

    def select_schema(self, schema):
        assert self.lib.RimeSelectSchema(self.session, schema.encode())

    def option(self, name, value=None):
        if value is not None:
            self.lib.RimeSetOption(self.session, name.encode(), value)
        return bool(self.lib.RimeGetOption(self.session, name.encode()))

    def clear(self):
        self.lib.RimeClearComposition(self.session)

    def key(self, code, modifiers=0):
        return bool(self.lib.RimeProcessKey(self.session, code, modifiers))

    def type(self, code, clear=True):
        if clear:
            self.clear()
        for ch in code:
            self.key(ord(ch))

    def page(self):
        ctx = Context()
        ctx.data_size = C.sizeof(Context) - C.sizeof(C.c_int)
        assert self.lib.RimeGetContext(self.session, C.byref(ctx))
        try:
            rows = [(ctx.menu.candidates[i].text.decode(),
                     (ctx.menu.candidates[i].comment or b'').decode())
                    for i in range(ctx.menu.num_candidates)]
            return rows, bool(ctx.menu.is_last_page), (ctx.composition.preedit or b'').decode()
        finally:
            self.lib.RimeFreeContext(C.byref(ctx))

    def choose(self, target, pages=50):
        for _ in range(pages):
            rows, last, _ = self.page()
            for i, (text, _) in enumerate(rows):
                if text == target:
                    assert self.lib.RimeSelectCandidateOnCurrentPage(self.session, i)
                    return
            if last or not self.key(0xff56):
                break
        raise AssertionError(f'candidate missing: {target!r}')

    def commit(self):
        c = Commit()
        c.data_size = C.sizeof(Commit) - C.sizeof(C.c_int)
        if not self.lib.RimeGetCommit(self.session, C.byref(c)):
            return None
        try:
            return c.text.decode()
        finally:
            self.lib.RimeFreeCommit(C.byref(c))

    def close(self):
        if self.session:
            self.lib.RimeDestroySession(self.session)
            self.session = 0
        self.lib.RimeFinalize()
        self.directory.close()
