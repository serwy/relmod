import fakemod
from fakemod.tests import tkfs
import unittest
import tempfile
import shutil
from pprint import pprint
import sys


class TestFunc(unittest.TestCase):

    def setUp(self):
        self.base = tempfile.mkdtemp()
        self.kf = tkfs.TinyKeyFS(self.base)
        self.reg = fakemod.registry.FakeModuleRegistry()
        self.lib = self.reg._load_file(self.base)

        # override registry
        self._old = fakemod._default
        fakemod._default = self.reg

    def tearDown(self):
        shutil.rmtree(self.base)
        self.reg.finder._remove_meta_path()

        # restore registry
        fakemod._default = self._old

    @unittest.skipIf(sys.version < '3.7', 'PEP562 in 3.7')
    def test_getattr(self):
        files = {'main/getattr.py':'''if 1:
    x = 1
    def __getattr__(name):
        if name == 'error':
            raise AttributeError(name)
        return name
    ''',
                 'main/other.py':''}
        self.kf.update(files)
        lib = self.lib
        self.assertEqual(lib.main.getattr.x, 1)
        self.assertEqual(lib.main.getattr.y, 'y')
        with self.assertRaises(AttributeError):
            lib.main.getattr.error

    def test_dir(self):
        files = {'main/dir.py':'''if 1:
    def __dir__():
        return ('x', 'y')
    ''',
                 'main/other.py': ''}
        self.kf.update(files)
        lib = self.lib
        mdir = dir(lib.main.dir)
        self.assertTrue('x' in mdir)
        self.assertTrue('y' in mdir)
        self.assertFalse('other' in mdir)

        lib.main.dir.__fakebrowse__ = True

        mdir = dir(lib.main.dir)
        self.assertTrue('x' in mdir)
        self.assertTrue('y' in mdir)
        self.assertTrue('other' in mdir)

    def test_fakeimp_star(self):
        files = {'main/__init__.py': '',
                  'main/x.py':'X=1; Y=2; Z=3 ',
                  'main/y.py':'X=4; Y=5; Z=6 ',
                  'main/a.py':'''if 1:
                    import fakemod
                    local=fakemod.install(globals())
                    ''',
                  }
        self.kf.update(files)
        lib = self.lib

        mod = lib.main.a
        mod.ffrom('.x', '*')
        self.assertEqual(mod.X, 1)
        self.assertEqual(mod.Y, 2)
        self.assertEqual(mod.Z, 3)

        mod.fimport('.y', '*')
        self.assertEqual(mod.X, 4)
        self.assertEqual(mod.Y, 5)
        self.assertEqual(mod.Z, 6)

    def test_init_api(self):
        files = {'main/__init__.py': '',
                  'main/x.py':'X=1; Y=2; Z=3 ',
                  'main/y.py':'X=4; Y=5; Z=6 ',
                  'main/a.py':'''if 1:
                    import fakemod
                    local=fakemod.install(globals())
                    ''',
                  }
        self.kf.update(files)

        p = self.kf.path('main/x.py')
        x = fakemod.at(p)
        self.assertEqual(x.X, 1)

        lib = fakemod.up(p)
        self.assertEqual(lib.x.X, 1)
        self.assertEqual(lib.y.X, 4)

        lib.y.X = 10
        self.assertEqual(lib.y.X, 10)
        fakemod.reload(lib.y.__file__)
        self.assertEqual(lib.y.X, 4)

        g = {'__name__':'__main__',
             '__file__':self.kf.path('main/__init__.py')}

        local = fakemod.install(g)
        self.assertTrue('fimport' in g)
        self.assertTrue('ffrom' in g)


        fakemod.toplevel('fm_main_x', lib.x.__file__)
        try:
            import fm_main_x
            self.assertEqual(fm_main_x.X, 1)
        finally:
            sys.modules.pop('fm_main_x')

    def test_deep_fimport(self):
        files = {'main/sub/sub/a.py': '''if 1:
    import fakemod; local = fakemod.install(globals())
    fimport('../x.py')
    fimport('../../y.py')
    ''',
                 'main/sub/sub/b.py': '''if 1:
    import fakemod; local = fakemod.install(globals())
    fimport('..x')
    fimport('...y')
    ''',
                 'main/sub/x.py': 'X=1',
                 'main/y.py': 'Y=2',
                 }
        self.kf.update(files)
        lib = self.lib

        self.assertEqual(lib.main.sub.sub.a.x.X, 1)
        self.assertEqual(lib.main.sub.sub.a.y.Y, 2)

        self.assertEqual(lib.main.sub.sub.b.x.X, 1)
        self.assertEqual(lib.main.sub.sub.b.y.Y, 2)

    def test_import_reload(self):
        # test fimport provides ModuleProxy
        # assumes SmartCache
        files = {
            'x.py': '''if 1:
    import fakemod; local = fakemod.install(globals())
    fimport('./y.py')
    from . import y as _y
    from .y import *
    ''',
            'y.py': '''Y=1''',
            }
        self.kf.update(files)
        lib = self.lib

        self.assertEqual(lib.x.y.Y, 1)
        self.assertEqual(lib.x._y.Y, 1)

        self.assertIsInstance(lib.x, fakemod.fmods.FakeModuleType)
        self.assertIsInstance(lib.x._y, fakemod.fmods.FakeModuleType)
        self.assertIsInstance(lib.x.y, fakemod.proxy.ModuleProxy)

        self.kf['y.py'] = 'Y=2'

        # force invalidate due to fs timestamp resolution
        # too great for execution speed
        self.reg.cache.invalidate(
            self.kf.path('y.py')
            )

        self.assertEqual(lib.x.Y, 2)
        self.assertEqual(lib.x._y.Y, 2)

        self.assertIs(
            fakemod.unwrap(lib.x.y),
            fakemod.unwrap(lib.x._y)
            )

def run():
    unittest.main(__name__, verbosity=2)


if __name__ == '__main__':
    run()
