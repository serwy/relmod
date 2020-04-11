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
import types
import importlib

__all__ = ['at', 'auto', 'local', 'FakeMod']


_cache = {}
_fake = {}
_real_cache = {}


class _FileMod:
    def __init__(self, fullpath, fm):
        self.fullpath = fullpath

        pkg = 'fake:' + self.fullpath
        mod = types.ModuleType(pkg)
        mod.__file__ = fullpath
        mod.__spec__ = None
        mod.__package__ = pkg
        mod.__dict__['__fakemod__'] = fm

        self.mod =mod
        self.load()

    def load(self, stat=None):
        if stat is None:
            self.stat = os.stat(self.fullpath)
        else:
            self.stat = stat

        with open(self.fullpath, 'r') as fid:
            src = fid.read()

        code = compile(src, self.fullpath, 'exec',
                       dont_inherit=True)

        exec(code, self.mod.__dict__)

    def get(self):
        new_stat = os.stat(self.fullpath)
        if new_stat.st_mtime != self.stat.st_mtime:
            self.load(new_stat)
        return self.mod


def _fake_get(self, name):
    absroot, root = _fake[self]
    full = os.path.join(absroot, name)
    if os.path.isfile(full + '.py'):
        full = full + '.py'
        if full not in _cache:
            _cache[full] = _FileMod(full, self)
        return _cache[full].get()
    elif os.path.isdir(full):
        if full not in _cache:
            _cache[full] = FakeMod(full, self)
        return _cache[full]
    else:
        raise AttributeError(
            'fake module has no attribute %r' % name
            )


def _pkg_dir(absroot):
    files = os.listdir(absroot)
    a = []
    for f in files:
        if f[0] == '.':
            continue
        full = os.path.join(absroot, f)
        if os.path.isdir(full):
            if not f.endswith('__'):
                a.append(f)
        if full.endswith('.py'):
            if os.path.isfile(full):
                a.append(f[:-3])
    return sorted(a)


def _fake_dir(self):
    absroot, root = _fake[self]
    return _pkg_dir(absroot)


class FakeMod:
    def __init__(self, root):
        _fake[self] = (os.path.abspath(root), root)

    def __getattr__(self, name):
        return _fake_get(self, name)

    def __setattr__(self, name, value):
        raise AttributeError('Read-only')

    def __delattr__(self, name):
        raise AttributeError('Read-only')

    def __dir__(self):
        return _fake_dir(self)


class _AutoReload:

    def __init__(self, g, head=None, name=None):
        if '__fakemod__' in g:
            return

        self.g = g
        self._last = {}
        self._loaded = {}

        if head is None:
            f = g['__file__']
            if f:
                head, tail = os.path.split(f)
            else:
                head = next(iter(g['__path__']))

        if name is None:
            name = self.g['__name__']

        self._name = name
        self._head = head

        g['__getattr__'] = self.get
        g['__dir__'] = self.dir
        g['__fakemod__'] = self

    def get(self, name):
        if self.g.get('__fakemod_static__'):
            # only do a single lazy import
            _name = self._name
            m = importlib.import_module("." + name, _name)
            self._loaded[name] = m
            return m
        _name = self._name
        m = self._loaded.get(name)
        if m is None:
            m = importlib.import_module("." + name, _name)
            self._loaded[name] = m
            # make sure __getattr__ is called by
            # removing name from the namespace
            self.g.pop(name, None)

            if (_name+'.'+name) not in sys.modules:
                if m.__file__:
                    self._last[m.__file__] = os.stat(m.__file__)

        file = m.__file__

        if file:
            last = self._last.get(file)
            s = os.stat(file)
            if (last is None) or (last.st_mtime != s.st_mtime):
                importlib.reload(m)

            # if an import error occurs during reload,
            # the timestamp is not updated
            self._last[file] = s
        else:
            if '__fakemod__' not in m.__dict__:
                _AutoReload(m.__dict__)

        return m

    def dir(self):
        s1 = set(self.g.keys())
        s2 = set(_pkg_dir(self._head))

        s1.update(s2)
        return sorted(s1)


# Using Python 3.7+ module machinery

def local(vars):
    "For accessing a module's peers in the same directory"
    g = vars
    name = g['__name__']
    if name.endswith('.local'):
        name = name[:-6]

    f = g['__file__']
    if f:
        head, tail = os.path.split(f)
    else:
        head = None

    _AutoReload(g, head, name)

    return g['__fakemod__']


def auto(mod):
    "Given a module, return auto-reloading parent"
    a = local(mod.__dict__)
    check = _pkg_dir(a._head)
    g = a.g
    for i in check:
        g.pop(i, None)


def at(path):
    "Given a file path, install autoreload into parent and return module"
    path = os.path.abspath(path)
    if os.path.isfile(path):
        path, tail = os.path.split(path)

    if path not in _real_cache:
        head, tail = os.path.split(path)
        sys.path.insert(0, head)
        m = importlib.import_module(tail)
        sys.path.remove(head)
        auto(m)
        _real_cache[path] = m

    return _real_cache[path]

