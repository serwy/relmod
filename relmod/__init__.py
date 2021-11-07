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


    update_dict = {}
    if isinstance(modname, str):
        if fromlist:
            insert_module = False
        else:
            insert_module = True

        if ' as ' in modname:
            modname, rename = modname.split(' as ')
            modname = modname.strip()
            rename = rename.strip()
            insert_module = True
        else:
            rename = None

        _file = globals.get('__file__', None)
        if _file is None:
            # rely on os.getcwd()
            mod = at(modname)
        else:
            head, tail = os.path.split(_file)
            modname = os.path.join(head, modname)
            mod = at(modname)

        if insert_module:
            if rename is None:
                # use the filename as the key in globals
                head, tail = os.path.split(modname)
                rename, ext = os.path.splitext(tail)

            rename = utils.fs_name_to_attr(rename)
            if rename:
                update_dict[rename] = mod
            else:
                raise ImportError(modname)

    else:
        mod = modname

    if fromlist:
        names = [i.strip() for i in fromlist.split(',')]

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

            update_dict[dst.strip()] = getattr(mod, src.strip())

    # Do the update atomically, so that we don't have a partial
    # update to globals in case there was an error earlier.
    globals.update(update_dict)


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
