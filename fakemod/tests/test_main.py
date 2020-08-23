import fakemod
from fakemod.tests import tkfs
import unittest
import tempfile
import shutil
from pprint import pprint
import sys



class TestFakemod(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp()
        self.kf = tkfs.TinyKeyFS(self.base)
        self.reg = fakemod.registry.FakeModuleRegistry()
        self.lib = self.reg._load_file(self.base)

    def tearDown(self):
        shutil.rmtree(self.base)
        self.reg.finder._remove_meta_path()

    def test_simple(self):
        files = {'main/__init__.py': 'x=123'}
        self.kf.update(files)
        lib = self.lib
        self.assertEqual(lib.main.x, 123)

    def test_loadtime(self):
        files = {'main/__init__.py': 'x=123'}
        self.kf.update(files)
        lib = self.lib

        lt0 = lib.main.__fakeload__
        lt1 = lib.main.__fakeload__

        self.assertEqual(lt0, lt1)

        lt2 = lib.main.__fakeload__ = ''
        self.reg.reload(lib.main.__file__)
        lt3 = lib.main.__fakeload__

        self.assertNotEqual(lt2, lt3)

    def test_relative(self):
        files = {'main/__init__.py': '',
                 'main/a.py': 'from . import b',
                 'main/b.py': 'B=1',
                 }
        self.kf.update(files)
        lib = self.lib

        self.assertEqual(lib.main.a.b.B, 1)

    def test_deep_relative(self):
        files = {'main/__init__.py': '',
                 'main/sub/a.py': 'from .. import b',
                 'main/sub/sub/a.py': 'from ... import b',
                 'main/b.py': 'B=1',
                 }
        self.kf.update(files)
        lib = self.lib

        self.assertEqual(lib.main.sub.a.b.B, 1)
        self.assertEqual(lib.main.sub.sub.a.b.B, 1)

    def test_deep_relative_loadtime(self):
        files = {'main/__init__.py': '',
                 'main/sub/a.py': 'from .. import b',
                 'main/sub/sub/a.py': 'from ... import b',
                 'main/b.py': 'B=1',
                 }
        self.kf.update(files)
        lib = self.lib

        lt0 = lib.main.sub.a.__fakeload__ = ''
        self.reg.cache.invalidate(lib.main.b.__file__)
        lt1 = lib.main.sub.a.__fakeload__

        self.assertNotEqual(lt0, lt1)

    def test_browse(self):
        kf = self.kf
        lib = self.lib

        self.assertFalse(hasattr(lib, 'main'))
        kf['main/__init__.py'] = 'x=123'
        self.assertTrue(hasattr(lib, 'main'))
        self.assertEqual(lib.main.x, 123)

    def test_stale(self):
        files = {'main/__init__.py': '',
                 'main/a.py':'''def A(): pass'''}
        self.kf.update(files)
        lib = self.lib

        a = lib.main.a

        def stale(mod, wd):
            self.assertIs(mod, a)
            self.assertFalse('A' in wd)

        a.__stale__ = stale
        self.reg.reload(a.__file__)


        hold_ref = a.A

        def stale(mod, wd):
            self.assertIs(mod, a)
            self.assertTrue('A' in wd)

        a.__stale__ = stale
        self.reg.reload(a.__file__)

    def test_fakeimp(self):
        files = {'main/__init__.py': '',
                  'main/x.py':'X=1',
                  'main/a.py':'''if 1:
                    import fakemod
                    local=fakemod.install(globals())
                    ''',
                  }
        self.kf.update(files)
        self.kf['main/sub/sub/a.py'] = self.kf['main/a.py']
        lib = self.lib

        mod = lib.main.a

        self.assertFalse(hasattr(mod, 'x'))
        mod.fimport('.x')
        self.assertTrue(hasattr(mod, 'x'))

        mod.ffrom('.x', 'X', 'Y')
        self.assertEqual(mod.Y, 1)

        mod = lib.main.sub.sub.a
        self.assertFalse(hasattr(mod, 'x'))
        mod.fimport('...x', as_='y')
        self.assertTrue(hasattr(mod, 'y'))

        mod.ffrom('...x', 'X', 'Y')
        self.assertEqual(mod.Y, 1)

    def test_spaces(self):
        files = {'main/__init__.py': """if 1:
                import fakemod; fakemod.install(globals())
                """,
                  'main/x x.py':'X=1',
                  }
        self.kf.update(files)
        mod = self.lib.main
        mod.fimport('./x x.py', 'x')
        self.assertEqual(mod.x.X, 1)

        with self.assertRaises(ImportError):
            mod.fimport('./x x.py')

        x = mod['x x']
        self.assertEqual(x.X, 1)

    def test_register(self):
        files = {'showcase/__init__.py':'',
                 'showcase/x.py': 'def x(x): return x'}
        self.kf.update(files)
        lib = self.lib
        self.reg.finder.register(
            'fm_showcase', lib.showcase.__file__
        )
        try:
            import fm_showcase
            self.assertEqual(fm_showcase.x.x(123), 123)

            # cycle __init__.py presence
            self.reg.reload(fm_showcase)
            self.assertTrue(fm_showcase.__file__ is not None)
            del self.kf['showcase/__init__.py']
            self.reg.reload(fm_showcase)
            self.assertTrue(fm_showcase.__file__ is None)

            self.kf['showcase/__init__.py']  = ''
            self.reg.reload(fm_showcase)
            self.assertTrue(fm_showcase.__file__ is not None)


        finally:
            sys.modules.pop('fm_showcase', None)

    def test_register_file(self):
        files = {'showcase/x.py': 'def x(x): return x'}
        self.kf.update(files)
        lib = self.lib
        self.reg.finder.register(
            'fm_showcase', lib.showcase.x.__file__
        )
        try:
            import fm_showcase
            self.assertEqual(fm_showcase.x(123), 123)
        finally:
            sys.modules.pop('fm_showcase', None)


    def test_proxy(self):
        files = {'showcase/__init__.py':'',
                 'showcase/x.py': 'def x(x): return x'}
        self.kf.update(files)
        p = self.reg.at(self.lib.showcase.__file__)
        self.assertEqual(p.x.x(123), 123)


    def test_auto(self):
        self.assertIs(fakemod.auto.pprint.pprint, pprint)

    def test_relative_getitem(self):
        files = {'main/__init__.py': '',
                 'main/sub/a.py': '''if 1:
                     import fakemod;
                     local = fakemod.install(globals())
                     x = local['../']
                     b = local['../b.py']
                     #c = local['..b']
                    ''',
                 'main/b.py': 'B=2',
                 }
        self.kf.update(files)
        lib = self.lib

        self.assertEqual(lib.main.sub.a.x.b.B, 2)
        self.assertEqual(lib.main.sub.a.b.B, 2)
        #self.assertEqual(lib.main.sub.a.c.B, 2)

    def test_delete(self):
        files = {'main/__init__.py': '',
                'main/b.py': 'B=2',
                 }
        self.kf.update(files)
        lib = self.lib

        self.assertEqual(lib.main.b.B, 2)

        del self.kf['main/b.py']

        with self.assertRaises(AttributeError):
            lib.main.b

    def test_init_grab(self):
        files = {'main/__init__.py': '',
                'ns/a.py':'',
                 }
        self.kf.update(files)
        lib = self.lib
        self.assertTrue(lib.main.__file__.endswith('__init__.py'))
        self.assertTrue(lib.ns.__file__ is None)

        del self.kf['main/__init__.py']
        self.assertTrue(lib.main.__file__ is None)


def run():
    unittest.main(__name__, verbosity=2)


if __name__ == '__main__':
    run()
