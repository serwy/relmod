import os
import sys

from . import proxy
from . import registry
from . import autoimport

from .runner import runtest, testonly, testmod
from .proxy import wrap, unwrap
from ._version import __version__
from . import fakesite
from .utils import execfile


_default = registry.FakeModuleRegistry()

__all__ = ['at', 'up', 'install', 'reload', 'toplevel',
           'auto', 'runtest', 'testonly', 'testmod',
           'site', 'execfile', 'imp']

def at(fp, inside='__file__'):
    mod = _default.at(fp, inside)
    return mod

def up(__file__):
    mod = _default.up(__file__)
    return mod

def install(globalsdict):
    g = globalsdict
    mod = _default.install(g)
    if g['__name__'] == '__main__':
        __builtins__['__import__'] = _default.builtins.__import__
    return mod

def reload(filename):
    return _default.reload(filename)

def toplevel(toplevel, filename):
    if isinstance(filename, fmods.FakeModuleType):
        filename = filename.__fullpath__
    _default.finder.register(toplevel, filename, proxy=True)

auto = autoimport.AutoImport()
site = fakesite.create_default_site(_default)


def imp(modname, what, globals=None):
    """import names from module into provided namespace"""
    if globals is None:
        frame = sys._getframe()
        globals = frame.f_back.f_globals

    if isinstance(modname, str):
        mod = at(modname)
    else:
        mod = modname

    names = [i.strip() for i in what.split(',')]

    if '*' in names:
        _all = getattr(mod, '__all__', None)
        if _all is None:
            _all = [i for i in dir(mod) if not i.startswith('_')]
        names.extend(_all)
        while '*' in names:
            names.remove('*')

    for n in names:
        if ':' in n:
            src, dst = n.split(':')
        elif ' as ' in n:
            src, dst = n.split(' as ')
        else:
            src = dst = n

        globals[dst.strip()] = getattr(mod, src.strip())


def deps(dirs=True, files=True):
    __deps(_default._deps, dirs, files)

def revdeps(dirs=True, files=True):
    __deps(_default._revdeps, dirs, files)

def __deps(deps, dirs=True, files=True):

    for k in sorted(deps.keys()):
        v = deps[k]
        if not files:
            if os.path.isfile(k):
                continue
        if not dirs:
            if os.path.isdir(k):
                continue
        print(k)
        for k2 in sorted(v.keys()):
            v2 = v[k2]
            if not files:
                if os.path.isfile(k2):
                    continue
            if not dirs:
                if os.path.isdir(k2):
                    continue
            print('\t %4i %s ' % (v2, k2))
