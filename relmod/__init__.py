"""
relmod

auto-reloading module development library

"""

##
## Author:    Roger D. Serwy
## Copyright: 2020-2022, Roger D. Serwy
##            All rights reserved.
## License:   BSD 2-Clause, see LICENSE file from project
##

import os
import sys

from . import proxy
from . import registry
from . import autoimport

from .runner import runtest, testmod, testfocus, testonly
from .proxy import wrap, unwrap
from ._version import __version__
from . import fakesite
from .utils import execfile


_default = registry.FakeModuleRegistry()

__all__ = ['at', 'up', 'install', 'reload', 'toplevel',
           'auto', 'runtest', 'testonly', 'testmod',
           'site', 'execfile', 'imp']

def at(pathname, inside='__file__'):
    """Create a module reference to the `pathname` string.

        Relative paths are normalized to `os.getcwd()`.
    """
    mod = _default.at(pathname, inside)
    return mod

def up(__file__):
    """Create a namespace module reference to the parent directory
        of the provided path, e.g. `__file__`.

        Relative paths are normalized to `os.getcwd()`.
    """
    mod = _default.up(__file__)
    return mod

def install(globals=None):
    """Install relmod import machinery into the provided namespace.
    If `globals is None`, uses the caller frame's globals.
    """
    if globals is None:
        frame = sys._getframe()
        globals = frame.f_back.f_globals

    g = globals
    mod = _default.install(g)
    if g['__name__'] == '__main__':
        __builtins__['__import__'] = _default.builtins.__import__
    return mod

def reload(filename):
    """Reload a provided filename or module reference."""
    return _default.reload(filename)

def toplevel(toplevel, filename):
    """Register a toplevel name for import.

        relmod.toplevel('mymodule', '/path/to/file.py')
        import mymodule

    """
    if isinstance(filename, fmods.FakeModuleType):
        filename = filename.__fullpath__
    _default.finder.register(toplevel, filename, proxy=True)

auto = autoimport.AutoImport()
site = fakesite.create_default_site(_default)


def imp(modname, fromlist=None, globals=None):
    """Import names from a module into a provided namespace.

        If `modname` is a relative path string, it is normalized relative
        to `__file__` from the global namespace, not os.getcwd().

        Supports renaming imports using ` as `.

        relmod.imp('. as local')  # import local directory namespace as `local`
        relmod.imp('../file.py', 'funcA, func2 as funcB')
    """
    if globals is None:
        frame = sys._getframe()
        globals = frame.f_back.f_globals

    return _default.imp(modname, fromlist, globals)


def use(path, *, globals=None):
    """Use the provided path. Relative paths resolve using `__file__` from
        calling frame's global namespace.
    """
    if globals is None:
        frame = sys._getframe()
        globals = frame.f_back.f_globals

    _file = globals.get('__file__', None)
    if _file is None:
        # rely on os.getcwd()
        mod = at(path)
    else:
        head, tail = os.path.split(_file)
        path = os.path.expanduser(path)
        modname = os.path.join(head, path)
        mod = at(modname)

    return mod


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
