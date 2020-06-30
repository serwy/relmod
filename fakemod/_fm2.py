"""

# FakeMod

A utility to automatically reload a module if modified,
or emulate a namespace package.


## Example

    import os
    os.makedirs('./utilities', exist_ok=True)
    with open('./utilities/tool.py', 'w') as f:
       f.write(r'''if 1:

        def func(a):
            print('func', a)

        ''')

    import fakemod
    mod = fakemod.at('./utilities')
    mod.tool.func(123)


## Usage

Place into `__init__.py`:

    import fakemod; fakemod.local(vars())

Also place into `local.py` to allow
for `from . import local` to access other files
in the same directory.


"""
import os
import sys
import importlib
import types
import traceback
from pprint import pprint


__all__ = ['at', 'local', 'ModuleProxy', 'import_at', 'wrap']

def __fakemod_pre():
    return {'_fs':_fs, '_fm':_fm, '_sm':_sm}

def __fakemod_post(obj):
    if obj:
        globals().update(obj)


_blank_stat = os.stat_result([0] * len(os.stat(__file__)))


class FakeModule(types.ModuleType):
    def __repr__(self):
        return '<fakemodule %r at %r>' % (
            self.__name__, self.__file__)

class FileStat:
    def __init__(self):
        self.stats = {}  # fullpath : stat
        self._check = True

    def _blank(self, fullpath):
        self.stats[fullpath] = _blank_stat

    def _forget(self, fullpath):
        if fullpath in self.stats:
            return self.stats.pop(fullpath)

    def is_same(self, fullpath, first=None, update=False,
                _check=None):
        """Returns True if not modified since last call.
            If not seen, return `first`"""
        if _check is None:
            _check = self._check

        if _check:
            assert(os.path.isfile(fullpath))
            stat = os.stat(fullpath)
            if fullpath in self.stats:
                prior = self.stats[fullpath]
                if prior.st_mtime == stat.st_mtime:
                    same = True
                else:
                    same = False
            else:
                same = first

            if update:
                self.stats[fullpath] = stat

            return same
        else:
            stat = self.stats.get(fullpath)
            if stat:
                return True
            else:
                return first

    def not_same(self, keys=None):
        r = []
        if keys is None:
            keys = self.stats.keys()
        for fullpath in keys:
            if not self.is_same(fullpath, first=False,
                                _check=True):
                r.append(fullpath)
        return r


_fs = FileStat()

class FakeModules:
    # fake module registry
    def __init__(self):
        self.mods = {}   # fullpath: fakemodule
        self._active = set()

    def __load_file(self, fullpath):
        # this will always load/exec the file
        assert(os.path.isfile(fullpath))

        stat = os.stat(fullpath)
        with open(fullpath, 'r') as fid:
            src = fid.read()

        try:
            code = compile(
                src,
                fullpath,
                'exec',
                dont_inherit=True,
                )
        except BaseException:
            code = None
            # maybe return error?
            raise

        if code:
            # reuse module if already loaded
            mod = self.mods.get(fullpath)
            if mod is None:
                mod = FakeModule(':fakemod:' + fullpath)

            d = mod.__dict__

            pre = None
            if '__fakemod_pre' in d:
                try:
                    pre = d['__fakemod_pre']()
                except BaseException:
                    traceback.print_exc()

            d['__fakemod__'] = self
            d['__name__'] = ':fakemod:' + fullpath
            d['__file__'] = fullpath
            exec(code, d)

            if '__fakemod_post' in d:
                try:
                    d['__fakemod_post'](pre)
                except BaseException:
                    traceback.print_exc()

            self.mods[fullpath] = mod
            _fs.stats[fullpath] = stat
            return mod

        else:
            return None

    def load_file(self, fullpath):
        if fullpath in self._active:
             raise ImportError('circular %s' % repr(self._active))
        try:
            self._active.add(fullpath)
            return self.__load_file(fullpath)
        finally:
            self._active.remove(fullpath)

    def get_module(self, fullpath):
        # grabs a module based on fullpath, reloading if needed
        if not _fs.is_same(fullpath, first=False):
            # lazy loading here
            m = self.load_file(fullpath)
        return self.mods[fullpath]

    def changed(self):
        return _fs.not_same(self.mods.keys())

    def _reload_all(self):
        for fp in self.mods:
            self.load_file(fp)

    def _reset(self, mod):
        # clear module dict and reload
        filename = mod.__file__
        fhead, ftail = os.path.split(filename)

        self.mods[filename].__dict__.clear()
        self.load_file(filename)

    def _reload_related(self, mod):
        # reload modules with same parent dir as mod
        filename = mod.__file__
        fhead, ftail = os.path.split(filename)
        for name in self.mods:
            head, tail = os.path.split(name)
            if head == fhead:
                print('reloading:', name)
                self.load_file(name)



_fm = FakeModules()


class SysModules:
    def __init__(self):
        self.mods = {}
        self._fsmod = FileStat()
        self._first_load(update=True)

    def _first_load(self, update=False):
        nup = []
        for k,v in sys.modules.items():
            if hasattr(v, '__file__'):
                if v.__file__:
                    self.mods[v.__file__] = v
                    s = self._fsmod.is_same(v.__file__,
                                   update=update,
                                   first=True)
                    if not s:
                        nup.append(k)
        return nup

    def needs_reload(self):
        return self._first_load(update=False)

    def register(self, mod):
        self._fsmod.is_same(mod.__file__, first=False,
                            update=True)
        self.mods[mod.__file__] = mod

    def get_module(self, fullpath):
        if not self._fsmod.is_same(fullpath, first=True,
                                   update=False):
            importlib.reload(self.mods[fullpath])
        return self.mods[fullpath]

    def _check(self, mod, reload=True):
        fullpath = mod.__file__
        if fullpath not in self.mods:
            self._fsmod.is_same(fullpath, first=True,
                                update=True)
            self.mods[fullpath] = mod
        elif reload:
            if not self._fsmod.is_same(fullpath, first=False,
                                   update=True):
                importlib.reload(mod)

    def reload(self):
        nup = self._first_load()
        nup.sort(reverse=True)

        r = []  # list of module names reloaded
        for n in nup:
            if n == '__main__':
                continue
            mod = sys.modules[n]
            r.append(n)
            pre = None
            if hasattr(mod, '__fakemod_pre'):
                try:
                    pre = getattr(mod, '__fakemod_pre')()
                except BaseException:
                    traceback.print_exc()

            importlib.reload(mod)

            if hasattr(mod, '__fakemod_post'):
                try:
                    getattr(mod, '__fakemod_post')(pre)
                except BaseException:
                    traceback.print_exc()

            self._fsmod.is_same(mod.__file__, update=True)

        return r


_sm = SysModules()

## Higher-level interfaces

def fs_name_to_attr(n):
    # filesystem name to python attribute
    if not n:
        return ''
    if n.endswith('.py'):
        n = n[:-3]
    #if n[0] in '0123456789': #.isnumeric():
    if n[0].isnumeric():
        n = ''
    if '.' in n:
        n = ''
    # TODO: :-=\\#@%()[]  check for more
    return n

def norm_path(n):
    # directories always end in a path separator
    x = n
    if os.path.isdir(x):
        if x[-1] != os.path.sep:
            x = x + os.path.sep
    return x

def scan_attr(root):
    # look at directory,
    # return dict of python attr : filesystem path
    assert(os.path.isdir(root))
    xr = {}

    for d in os.scandir(root):
        n = fs_name_to_attr(d.name)
        path = norm_path(d.path)
        if n:
            xr[n] = path
    return xr

def attr_to_fs_name(root, a):
    # python attribute to filesystem name
    absroot = os.path.abspath(root)
    base = os.path.join(absroot, a)
    base_py = base + '.py'
    if os.path.isfile(base_py):
        return base_py
    elif os.path.isdir(base):
        return norm_path(base)
    else:
        return ''

def _fns_init(self):
    def wrapper(root=None):
        assert(os.path.isdir(root))
        self.__dict__[':root:'] = norm_path(root)
    return wrapper

def _getattr(root, name):
    path = attr_to_fs_name(root, name)
    if path == '':
        raise AttributeError(name)

    if path.endswith(os.path.sep):
        mod = FakeNamespace(path)
    else:
        mod = _fm.get_module(path)
    return mod

def _dir(root):
    x = scan_attr(root)
    return sorted(x.keys())


class FakeNamespace:

    @property
    def __init__(self):
        d = self.__dict__
        d[':proxy:'] = True
        if ':root:' not in d:
            return _fns_init(self)
        else:
            # run the __init__.py for the module
            return _getattr(d[':root:'], '__init__')

    def __getitem__(self, key):
        return self.__dict__[key]

    def __dir__(self):
        return _dir(self.__dict__[':root:'])

    def __getattr__(self, name):
        r = _getattr(self.__dict__[':root:'], name)
        if self.__dict__[':proxy:']:
            if isinstance(r, types.ModuleType):
                if r.__file__:
                    r = ModuleProxy(r)
                else:
                    pass  # what to do here?
        return r

    def __setattr__(self, name, value):
        raise ValueError('read-only')

    def __repr__(self):
        return '<FakeNamespace at %r>' % (
            self.__dict__[':root:'])


    def __call__(self, num):
        # go up a directory, -num times
        assert(isinstance(num, int))
        if num == 0:
            return self

        r = self.__dict__[':root:']
        r = os.path.abspath(r)
        head = r
        for _ in range(-num):
            head, tail = os.path.split(head)

        return FakeNamespace(head)

class missing:
    pass

def _qgetattr(self, name):
    mod = self.__dict__[':mod:']
    rel = self.__dict__[':autoreload:']

    parts = mod.__name__.split('.')
    # when nested, need to break off names
    # TODO: test case
    if len(parts) == 1:
        _name = parts[0]
    else:
        _name  = '.'.join(parts[:-1])

    new_name = _name + '.' + name
    prior = getattr(mod, name, missing)
    new_mod = importlib.import_module(new_name, mod
                                      )
    _sm._check(new_mod, reload=rel)
    if prior is not missing:
        if prior is not new_mod:
            print('Loading %r overwrites a %r in %r' % (
                name, type(prior), mod))

    return new_mod


class QuasiNamespace:
    # Use the import machinery for reloading modules

    def __init__(self, mod, root=None):
        d = self.__dict__
        d[':mod:'] = mod
        d[':autoreload:'] = True
        if root is None:
            # namespace modules have __file__ = None
            head, tail = os.path.split(mod.__file__)
            root = head
        d[':root:'] = root

    def __dir__(self):
        return _dir(self.__dict__[':root:'])

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __getattr__(self, name):
        res = _qgetattr(self, name)

        if isinstance(res, types.ModuleType):
            if res.__file__ is None:
                root = self.__dict__[':root:']
                nr = os.path.join(root, name)
                res = QuasiNamespace(res, root=nr)
            else:
                # proxy ?
                pass
        return res

    def __setattr__(self, name, value):
        raise ValueError('read-only')

    def __repr__(self):
        q  = self.__dict__[':mod:'].__name__
        return '<QuasiNamespace %r at %r>' % (
            q, self.__dict__[':root:'])


def _mp_get(self):
    d = self.__dict__
    fp = d[':fullpath:']
    handler = d[':handler:']
    m = handler.get_module(fp)
    return m

class ModuleProxy:
    # proxy to a particular file
    def __init__(self, fullpath):
        d = self.__dict__
        d[':handler:'] = _fm
        d[':name:'] = ':fakemod:'
        # fullpath - usually a string with a fs path
        if hasattr(fullpath, '__file__'):
            if isinstance(fullpath, FakeModule):
                fullpath = fullpath.__file__
            elif isinstance(fullpath, ModuleProxy):
                # copy constructor
                dd = fullpath.__dict__
                d[':name:'] = dd[':name:']
                d[':handler:'] = dd[':handler:']
                fullpath = dd[':fullpath:']
            else:
                d[':name:'] = fullpath.__name__
                d[':handler:'] = _sm
                _sm.register(fullpath)
                fullpath = fullpath.__file__

        d[':fullpath:'] = fullpath

    @property
    def __doc__(self):
        m = _mp_get(self)
        return getattr(m, '__doc__')

    def __getattr__(self, name):
        m = _mp_get(self)
        return getattr(m, name)

    def __setattr__(self, name, value):
        m = _mp_get(self)
        return setattr(m, name, value)

    def __delattr__(self, name):
        m = _mp_get(self)
        return delattr(m, name)

    def __dir__(self):
        m = _mp_get(self)
        return dir(m)

    def __repr__(self):
        d = self.__dict__
        fp = d[':fullpath:']
        name = d[':name:']
        return "<moduleproxy %r for %r>" % (name, fp)


def wrap(obj):
    return ModuleProxy(obj)


def at(where, allow_real=False):
    if isinstance(where, dict):
        # globals() passed in
        if '__fakemod__' in where or __name__ == '__main__' or not allow_real:
            f = where['__file__']
            f = os.path.abspath(f)
            head, tail = os.path.split(f)
            return FakeNamespace(head)
        else:
            head = sys.modules[where['__name__']]
            return QuasiNamespace(head)

    elif os.path.isdir(where):
        where = os.path.abspath(where)
        return FakeNamespace(where)
    elif os.path.isfile(where):
        where = os.path.abspath(where)
        return ModuleProxy(where)
    else:
        raise ValueError('Not found: %r' % where)


class FakeImport:
    """dirty hack with python syntax.
The getattr can be space-separated.

`fimport .util` is  `getattr(fimport, 'util')`

It is conveniently close to `import .util`
for one-level relative imports when fakemod
is no longer needed.

If `local` was created for importlib, then fimport
functions the same as a relative import
"""

    def __init__(self, vars, local):
        self.__vars = vars
        self.__local = local

    def __getattr__(self, name):
        try:
            error = False
            item = getattr(self.__local, name)
        except AttributeError:
            error = True

        if error:
            n = self.__vars['__name__'] + '.' + name
            raise ModuleNotFoundError(n)

        # inject into namespace, just like import
        self.__vars[name] = item
        return item

# TODO: reference tracking to modules to
# form a dependency graph, maybe use gc to augment

# TODO: import hook for tracking
# importlib machinery will not auto-reload

def local(vars, name='local', allow_real=False):
    assert(isinstance(vars, dict))
    # vars() passed in
    where = vars
    if '__fakemod__' in where or __name__ == '__main__' or not allow_real:
        f = where['__file__']
        f = os.path.abspath(f)
        head, tail = os.path.split(f)
        mod = FakeNamespace(head)
    else:
        head = sys.modules[where['__name__']]
        mod = QuasiNamespace(head)

    if name:
        vars[name] = mod
        vars['fimport'] = FakeImport(vars, mod)

    return mod


# Note: namespace modules in python 3.3+
# what to do before 3.3 ?

def import_at(path):
    path = os.path.abspath(path)
    path2, ext = os.path.splitext(path)
    head, tail = os.path.split(path2)
    if tail == '__init__':
        head, tail = os.path.split(head)

    # head, tail, ext
    sys.path.append(head)
    try:
        if tail in sys.modules:
            m = sys.modules[tail]
            if m.__file__:
                if os.path.abspath(m.__file__) != path:
                    # collision
                    raise Warning('module collision: %r' % m.__file__)
            else:
                # namespace mod?
                # TODO: check for path collision
                pass

        mod = importlib.import_module(tail)
        if mod.__file__:
            _sm.register(mod)
            return mod
        else:
            return QuasiNamespace(mod, root=path)
    except ImportError:
        if os.path.isdir(path):
            # Python < 3.3
            return FakeNamespace(path)
        else:
            print('well')
            raise
            return ModuleProxy(path)
    finally:
        sys.path.pop()
