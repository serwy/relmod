import os

from . import proxy
from . import registry
from . import autoimport

from .runner import runtest, testonly, testmod
from .proxy import wrap, unwrap

_default = registry.FakeModuleRegistry()

__all__ = ['at', 'up', 'install', 'reload', 'toplevel',
           'auto', 'runtest', 'testonly', 'testmod']

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
    _default.finder.register(toplevel, filename)

auto = autoimport.AutoImport()


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
