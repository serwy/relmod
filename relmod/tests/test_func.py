import relmod
from relmod.tests import tkfs

import unittest
import tempfile
import shutil
from pprint import pprint
import sys
import json
import os

from relmod import proxy
from relmod import fakesite

class TestFunc(unittest.TestCase):

    def setUp(self):
        self._prior_cwd = os.getcwd()
        self.base = tempfile.mkdtemp()
        os.chdir(self.base)
        self.kf = tkfs.TinyKeyFS(self.base)
        self.reg = relmod.registry.FakeModuleRegistry()
        self.lib = self.reg._load_file(self.base)

        # override registry
        self._old = relmod._default
        relmod._default = self.reg

    def tearDown(self):
        os.chdir(self._prior_cwd)
        shutil.rmtree(self.base)
        self.reg.finder._remove_meta_path()
        self.reg.finder._remove_sys_modules()

        # restore registry
        relmod._default = self._old

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


    def test_imp_star(self):
        files = {'main/__init__.py': '',
                  'main/x.py':'X=1; Y=2; Z=3 ',
                  'main/y.py':'X=4; Y=5; Z=6 ',
                  'main/a.py':'''if 1:
                    import relmod
                    local=relmod.install(globals())
                    ''',
                  }
        self.kf.update(files)
        lib = self.lib

        mod = lib.main.a
        relmod.imp(lib.main.x, '*', mod.__dict__)

        self.assertEqual(mod.X, 1)
        self.assertEqual(mod.Y, 2)
        self.assertEqual(mod.Z, 3)

        relmod.imp(lib.main.y, '*', mod.__dict__)
        self.assertEqual(mod.X, 4)
        self.assertEqual(mod.Y, 5)
        self.assertEqual(mod.Z, 6)

    def test_init_api(self):
        files = {'main/__init__.py': '',
                  'main/x.py':'X=1; Y=2; Z=3 ',
                  'main/y.py':'X=4; Y=5; Z=6 ',
                  'main/a.py':'''if 1:
                    import relmod
                    local=relmod.install(globals())
                    ''',
                  }
        self.kf.update(files)

        p = self.kf.path('main/x.py')
        x = relmod.at(p)
        self.assertEqual(x.X, 1)

        lib = relmod.up(p)
        self.assertEqual(lib.x.X, 1)
        self.assertEqual(lib.y.X, 4)

        lib.y.X = 10
        self.assertEqual(lib.y.X, 10)
        relmod.reload(lib.y.__file__)
        self.assertEqual(lib.y.X, 4)

        g = {'__name__':'__main__',
             '__file__':self.kf.path('main/__init__.py')}

        local = relmod.install(g)

        relmod.toplevel('fm_main_x', lib.x.__file__)
        try:
            import fm_main_x
            self.assertEqual(fm_main_x.X, 1)
        finally:
            sys.modules.pop('fm_main_x')

    def test_imp(self):
        files = {'main/sub/sub/a.py': '''if 1:
    import relmod; local = relmod.install(globals())
    relmod.imp('../x.py', 'X')
    relmod.imp('../../y.py', 'Y')
    ''',
                 'main/sub/sub/b.py': '''if 1:
    import relmod; local = relmod.install(globals())
    relmod.imp('../x.py as x')
    relmod.imp('../../y.py as y')
    ''',
                 'main/sub/x.py': 'X=1',
                 'main/y.py': 'Y=2',
                 }
        self.kf.update(files)
        lib = self.lib

        self.assertEqual(lib.main.sub.sub.a.X, 1)
        self.assertEqual(lib.main.sub.sub.a.Y, 2)

        self.assertEqual(lib.main.sub.sub.b.x.X, 1)
        self.assertEqual(lib.main.sub.sub.b.y.Y, 2)

    def test_use(self):
        files = {
            'main/sub/sub/a.py': '''if 1:
    import relmod
    x = relmod.use('../x.py')
    y = relmod.use('../../y.py')
    ''',
            'main/sub/x.py': 'X=1',
            'main/y.py': 'Y=2',
                 }

        self.kf.update(files)
        lib = self.lib

        self.assertEqual(lib.main.sub.sub.a.x.X, 1)
        self.assertEqual(lib.main.sub.sub.a.y.Y, 2)


    def test_import_reload(self):
        # test fimport provides ModuleProxy
        # assumes SmartCache
        files = {
            'x.py': '''if 1:
    import relmod; local = relmod.install(globals())
    relmod.imp('./y.py')
    from . import y as _y
    from .y import *
    ''',
            'y.py': '''Y=1''',
            }
        self.kf.update(files)
        lib = self.lib

        self.assertEqual(lib.x.y.Y, 1)
        self.assertEqual(lib.x._y.Y, 1)

        self.assertIsInstance(lib.x, relmod.fmods.FakeModuleType)
        self.assertIsInstance(lib.x._y, relmod.proxy.ModuleProxy)
        self.assertIsInstance(lib.x.y, relmod.proxy.ModuleProxy)

        self.kf['y.py'] = 'Y=2'

        # force invalidate due to fs timestamp resolution
        # too great for execution speed
        self.reg.cache.invalidate(
            self.kf.path('y.py')
            )

        self.assertEqual(lib.x.Y, 2)
        self.assertEqual(lib.x._y.Y, 2)

        self.assertIs(
            relmod.unwrap(lib.x.y),
            relmod.unwrap(lib.x._y)
            )


    def test_import_proxy(self):  # for later
        # test fimport provides ModuleProxy
        # assumes SmartCache
        BASE = self.base
        files = {
            'x.py': '''if 1:
    import relmod; relmod.install(globals())
    relmod.toplevel('yyy2', '{BASE}/y2.py')
    import yyy2
    from . import z
    __fakeproxy__ = False
    from . import z2
    '''.format(BASE=BASE),
            'y.py': '''if 1:
    from . import z
    from .z import Z''',
            'y2.py': '''if 1:
    from . import z2
    from .z2 import Z''',
            'z.py': '''from .zcache import Z''',
            'z2.py': '''from .zcache import Z''',
            'zcache.py':'''Z=3''',
            }
        self.kf.update(files)
        lib = self.lib

        self.assertIsInstance(lib.x.yyy2, relmod.proxy.ModuleProxy)

        self.assertIsInstance(lib.x.z, relmod.proxy.ModuleProxy)
        self.assertIsInstance(lib.x.z2, relmod.fmods.FakeModuleType)

        self.assertIsInstance(proxy.unwrap(lib.x.yyy2).z2, relmod.proxy.ModuleProxy)

        self.assertEqual(proxy.unwrap(lib.x.yyy2).Z, 3)

        self.kf['zcache.py'] = 'Z=0'

        # force invalidate due to fs timestamp resolution
        # too great for execution speed
        self.reg.cache.invalidate(
            self.kf.path('zcache.py')
            )

        self.assertEqual(lib.x.yyy2.Z, 0)


    def test_site(self):
        site = fakesite.FakeSite(self.reg)
        self.assertFalse(dir(site))  # empty

        kf = self.kf

        kf['a1.py'] = 'value = 123'
        kf['a.site'] = json.dumps([('abc', kf.path('a1.py'))])

        # user-set item
        site['AAA'] = kf.path('a1.py')
        self.assertEqual(site.AAA.value, 123)

        # user-set use
        (~site).use(kf.path('a.site'))
        self.assertEqual(site.abc.value, 123)

        # clear it
        (~site).reset()
        self.assertFalse(dir(site))  # empty
        (~site).set_site_files('', [kf.path('a.site')])
        self.assertEqual(site.abc.value, 123)

        # test site break
        (~site).set_site_files('break', [kf.path('a.site')])
        self.assertFalse(dir(site))  # empty

        # test site empty
        (~site).set_site_files('', [])
        self.assertFalse(dir(site))  # empty


        # test site from env variable
        (~site).set_site_files(kf.path('a.site'), [])
        self.assertEqual(site.abc.value, 123)


    def test_expand_user(self):
        try:
            kf = self.kf
            kf['home/a1.py'] = 'value = 123'
            home = os.environ.get('HOME', None)
            os.environ['HOME'] = kf.path('home')
            a1 = self.reg.at('~/a1.py')
            self.assertEqual(a1.value, 123)
        finally:
            if home is not None:
                os.environ['HOME'] = home


def run():
    unittest.main(__name__, verbosity=2)


if __name__ == '__main__':
    run()
