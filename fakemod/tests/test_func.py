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

    def tearDown(self):
        shutil.rmtree(self.base)
        self.reg.finder._remove_meta_path()

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


def run():
    unittest.main(__name__, verbosity=2)


if __name__ == '__main__':
    run()
