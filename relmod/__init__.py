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
from . import utils

from .runner import runtest, testmod, testfocus, testonly
from .proxy import wrap, unwrap
from ._version import __version__
from . import fakesite
from .utils import execfile



_default = registry.FakeModuleRegistry()

__all__ = ['at', 'up', 'install', 'reload', 'toplevel',
           'auto', 'runtest', 'testonly', 'testmod', 'testfocus',
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


def if_main(globals=None):
    """Install relmod only if run in __main__"""
    # use case: relative imports and testing in same file
    if globals is None:
        frame = sys._getframe()
        globals = frame.f_back.f_globals

    g = globals
    if g['__name__'] == '__main__':
        __builtins__['__import__'] = _default.builtins.__import__
        mod = _default.install(g)
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

def _toplevel_site(name):
    toplevel(name, getattr(site, name))

toplevel.site = _toplevel_site

auto = autoimport.AutoImport()
site = fakesite.create_default_site(_default)


def imp(modname, fromlist=None, globals=None, abswarn=True):
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

    if isinstance(modname, str):
        _file = globals.get('__file__', None)
        if _file is not None:
            if (abswarn) and (not modname.startswith('.')):
                head, tail = os.path.split(_file)
                m = os.path.expanduser(modname)
                m = os.path.join(head, m)

                import warnings
                # do a warning for relative path
                rp = os.path.relpath(m, head)
                if not rp.startswith('.'):
                    rp = '.' + os.sep + rp

                s = '%r -> %r' % (modname, rp)
                warnings.warn(fmods.AbsolutePathWarning(s), 'once',
                              stacklevel=2)

    return _default.imp(modname, fromlist, globals)


def _imp_site(name, fromlist=None, globals=None):
    """Import using `relmod.site`"""
    if globals is None:
        globals = utils.get_globals(1)

    if fromlist is None:
        return imp(site, name, globals)
    else:
        obj = getattr(site, name)
        return imp(obj, fromlist, globals)


def _imp_develop(name, globals=None):
    """Import a toplevel name for development"""
    import importlib
    mod = importlib.import_module(name)
    file = mod.__file__
    head, tail = os.path.split(file)
    if tail == '__init__.py':
        target = head
    else:
        target = file

    if globals is None:
        f = sys._getframe()
        g = f.f_back.f_globals
    else:
        g = globals

    imp(target, globals=g)
    if name not in sys.modules:
        sys.modules[name] = g[name]


imp.site = _imp_site
imp.develop = _imp_develop



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
