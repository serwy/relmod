from __future__ import print_function
import sys
PY27 = sys.version < '3'

import os
import weakref
import types
from collections import defaultdict

if not PY27:
    import builtins

from . import cache
from . import fmods
from . import utils
from . import finder
from . import fakeimp
from . import proxy

_print = print


def _wdict(mod):
    wd = {}
    d = mod.__dict__
    name = mod.__name__
    for k, v in d.items():
        try:
            if v.__module__ == name:
                wv = weakref.ref(v)
                wd[k] = wv
        except:
            pass
    return wd



class FakeModuleRegistry:
    def __init__(self):
        self.cache = cache.SmartCache(self)
        self.mods = {}
        self._deps = defaultdict(lambda: defaultdict(int))
        self._revdeps = defaultdict(lambda: defaultdict(int))
        self.finder = finder.FakeFinder(self)
        self.log = None
        self._hard_reset = set()
        self._hard_reset_always = set()
        self._active = set()

        b = fmods.FakeBuiltins('fake_builtins')
        @b.override('__import__')
        def factory(orig):
            self._orig_import = orig
            def _imp(name, globals=None, locals=None, fromlist=(), level=0):
                if level == 0:
                    return orig(name, globals, locals, fromlist, level)
                else:
                    return self._import(name, globals, locals, fromlist, level)
            return _imp
        self._builtins = b
        if PY27:
            # avoid restricted mode
            __builtins__['__import__'] = b.__import__

    @property
    def builtins(self):
        return self._builtins

    def _add_dep(self, file, inside):
        if inside:
            self._deps[inside][file] += 1
            self._revdeps[file][inside] += 1
        else:
            raise ValueError(repr((file, inside)))

    def _remove_dep(self, file, inside):
        d = self._deps[inside].pop(file, None)
        r = self._revdeps[file].pop(inside, None)
        return d, r

    def _dep_reset(self, filename):
        """removes filename from dependency tracking"""
        x = self._deps.pop(filename, None)
        if x:
            for name in x:
                q = self._revdeps[name].pop(filename, None)
        # TODO: undo function


    def _create_module(self, filename):
        # only call from ._factory
        # always creates a module
        ap = os.path.abspath(filename)
        f = filename
        if f != ap:
            print('WARNING: edge case for ', repr((f, ap)))
            filename = os.path.sep + filename
            #assert(f == ap)
        mod = fmods.FakeModuleType('fake')
        self._populate_module(mod, filename)
        return mod

    def _populate_module(self, mod, filename):

        d = mod.__dict__

        browse = False
        if os.path.isfile(filename):
            file = filename
            path = [os.path.split(filename)[0]]
            if os.path.split(file)[1] == '__init__.py':
                browse = True
        else:
            file = None
            if filename.endswith('__init__.py'):
                filename = os.path.split(filename)[0]
            path = [filename]
            browse = True


        d['__name__'] = 'fakemod.at(%r)' % filename
        d['__file__'] = file
        if not PY27:
            d['__builtins__'] = self.builtins
        d['__path__'] = path

        d['__fullpath__'] = filename

        d['__fakebrowse__'] = browse
        d['__fakeregistry__'] = self

        # TODO: __spec__ and __loader__ for importlib.reload support

        return mod

    def _exec_module(self, filename, mod):
        # only call from _factory
        with open(filename, 'r') as fid:
            src = fid.read()

        code = compile(src, filename, 'exec', dont_inherit=True)
        d = mod.__dict__

        # opt-in tracking of objects that have been redefined
        stale = d.get('__stale__', None)
        if callable(stale):
            wd = _wdict(mod)  # save the current objects
        else:
            wd = None

        if filename in self._hard_reset:
            d.clear()
            self._populate_module(mod, filename)
            if filename not in self._hard_reset_always:
                self._hard_reset.discard(filename)

        d['__fakeload__'] = None
        exec(code, d)
        d['__fakeload__'] = utils.now()

        stale = d.get('__stale__', None)
        if callable(stale):
            if wd:
                s = {}
                for k, v in wd.items():
                    if v():
                        s[k] = v
                # pass in the mod and weak dict, so
                # __stale__ = fakemod.stalehandler could work
                stale(mod, s)

        return mod

    def _factory(self, fp):
        if fp not in self.mods:
            self.mods[fp] = self._create_module(fp)

        mod = self.mods[fp]

        if os.path.isfile(fp):
            if mod.__file__ is None:
                self._populate_module(mod, fp)

            self._dep_reset(fp)
            self._exec_module(fp, mod)
        else:
            if mod.__file__ is not None:
                fp = os.path.split(fp)[0]
                self._populate_module(mod, fp)

        return mod

    def _import(self, name, gb, lc, fromlist, level=0):
        if '__fakeregistry__' not in gb:
            return self._orig_import(name, gb, lc, fromlist, level)

        if self.log is not None:
            log.append(('_import', repr((name, fromlist, level))))

        inside = file = gb['__fullpath__']
        assert(file is not None)

        p = utils.path_to_parts(file)
        file = utils.parts_to_path(p[:-level])
        mod = self._load_file(file)

        name = name.lstrip('.')

        while name:
            g, sep, name = name.partition('.')
            mod = getattr(mod, g)
            fullpath = mod.__file__
            if fullpath:
                self._add_dep(fullpath, inside)

        if fromlist:
            # add dependencies

            if '*' in fromlist:
                _all = getattr(mod, '__all__', None)
                if _all is None:
                    _all = [i for i in dir(mod) if i[0] != '_']
                fromlist = _all

            for f in fromlist:
                m = getattr(mod, f)
                if isinstance(m, fmods.FakeModuleType):
                    fullpath = m.__file__
                    if fullpath:
                        self._add_dep(fullpath, inside)

        return mod

    def _get_mod(self, d, name):

        fullpath = d['__path__'][0]

        base = os.path.join(fullpath, name)
        base = os.path.abspath(base)

        base_py = base + '.py'

        if os.path.isfile(base_py):
            mod = self._load_file(base_py)

        elif os.path.isdir(base):
            base_init = os.path.join(base, '__init__.py')
            if os.path.isfile(base_init):
                mod = self._load_file(base_init)
            else:
                mod = self._load_file(base)
        elif os.path.isfile(base):
            mod = self._load_file(base)
        else:
            mod = None

        if mod:
            inside = d['__file__']
            target = mod.__file__
            if target:
                if inside:
                    self._add_dep(target, inside)

        return mod

    def _dir_mod(self, d):
        fp = d['__file__']
        if fp:
            if os.path.isfile(fp):
                fp = os.path.split(fp)[0]
        else:
            fp = d['__path__'][0]

        r = set(d.keys())
        for n in os.listdir(fp):
            n = utils.fs_name_to_attr(n)
            if n:
                r.add(n)

        mdir = d.get('__dir__', None)
        if callable(mdir):
            r.update(mdir())

        return sorted(r)

    def _load_file(self, file):
        # file is abspath at this point
        if not file.endswith('.py'):
            # assuming directory
            file = os.path.join(file, '__init__.py')

        if self.log is not None:
            self.log.append(('start', file))

        def factory(filename):  # called by cache in case of reload
            return self._factory(filename)

        self._active.add(file)
        try:
            mod, from_cache = self.cache.load(factory, file)
        finally:
            self._active.discard(file)

        if self.log is not None:
            self.log.append(('stop', file, from_cache))
        return mod

    #------
    # API
    #------

    def at(self, fp, inside='__file__'):
        fp = os.path.abspath(fp)
        if os.path.exists(fp):
            s = self._load_file(fp)
        else:
            raise ValueError('not found %r' % fp)

        fp = s.__file__
        if fp:
            self._add_dep(fp, inside)

        s = proxy.wrap(s, inside)
        return s

    def up(self, __file__):
        f = os.path.abspath(__file__)
        head, tail = os.path.split(f)
        return self.at(head, f)

    def install(self, globalsdict):
        g = globalsdict
        g['__fakeregistry__'] = self
        g['fimport'] = fakeimp.FakeImport(g)
        g['ffrom'] = fakeimp.FakeFrom(g)

        file = g.get('__file__')
        if file is None:
            file = os.path.join(os.getcwd(), '<unknown>')
        file = os.path.abspath(file)
        g['__fullpath__'] = file
        return self.up(file)

    def reload(self, filename_or_mod, inside='<reload>'):
        if isinstance(filename_or_mod,
                      (fmods.FakeModuleType, proxy.ModuleProxy)):
            mod = filename_or_mod
            filename = mod.__fullpath__
            filename = utils.split_init(filename)
        else:
            mod = None
            filename = filename_or_mod

        fp = os.path.abspath(filename)
        if not fp.endswith('.py'):
            fp = os.path.join(fp, '__init__.py')
        if fp not in self.mods:
            raise ValueError('file not loaded: %r' % filename_or_mod)

        self.cache.invalidate(fp)
        s = self._load_file(fp)  # force load of the file
        if mod is None:
            mod = proxy.wrap(s, inside)

        return mod
