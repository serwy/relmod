from __future__ import print_function

import sys
import types
import os

from . import proxy
from . import utils


class FakeLoader:
    def __init__(self, fs):
        self.fs = fs

    def __getattr__(self, name):
        #print('fl getattr', name)
        raise AttributeError(name)

    def load_module(self, *args):
        fullname = self.fs.fullname

        base, sep, rest = fullname.partition('.')

        fullpath, use_proxy = self.fs.finder.toplevel[base]
        reg = self.fs.finder.registry

        mod = reg._load_file(fullpath)
        if mod.__file__:
            reg._add_dep(mod.__file__, '<toplevel import>')

        mod.__dict__['__fakeproxy__'] = use_proxy

        # walk the name
        while rest:
            name, sep, rest = rest.partition('.')
            mod = getattr(mod, name)

        self.fs.origin = mod.__dict__['__file__']

        if use_proxy:
            wmod = proxy.wrap(mod)
        else:
            wmod = mod

        sys.modules[fullname] = wmod
        self.fs.finder._sysmods[fullname] = wmod
        return mod


class FakeSpec:
    def __init__(self, finder, fullname, fullpath, use_proxy):

        self.finder = finder
        self.fullname = fullname
        self.use_proxy = use_proxy

        self.name = fullname
        self.submodule_search_locations = []
        self.loader = FakeLoader(self)
        self.origin = fullpath
        self.has_location = True
        self.parent = fullname.rpartition('.')[0]
        self.cached = None
        self._initializing = False

    def __getattr__(self, name):
        print('fs getattr', name)
        raise AttributeError(name)


class FakeFinder:
    def __init__(self, registry):
        self.registry = registry
        sys.meta_path.insert(0, self)
        self.toplevel = {}
        self._sysmods = {}  # cache of what was added

    def _remove_meta_path(self):
        if self in sys.meta_path:
            sys.meta_path.remove(self)

    def _remove_sys_modules(self):
        for k, v in self._sysmods.items():
            if k in sys.modules:
                if sys.modules[k] is v:
                    sys.modules.pop(k)
        self._sysmods.clear()

    def __getattr__(self, name):
        if name not in ('find_spec',):
            print('ff getattr', name)
        raise AttributeError(name)

    def invalidate_caches(self, *args):
        pass

    def register(self, name, fullpath, proxy=True):
        fp = os.path.abspath(fullpath)
        fp = utils.split_init(fp)
        self.toplevel[name] = (fp, proxy)

    def _find_spec(self, fullname, path=None, target=None):
        #print('find_spec', id(self), fullname, path, target)
        for t, (fullpath, use_proxy) in self.toplevel.items():
            if fullname.partition('.')[0] == t:
                #print('--- find_spec', fullname)
                return FakeSpec(self, fullname, fullpath, use_proxy)

    # python 3.3
    def find_module(self, fullname, path=None):
        #print('find module', fullname)
        spec = self._find_spec(fullname)
        if spec is None:
            return
        return spec.loader

    def load_module(self, fullname):
        print('load module', fullname)
        pass

    def __del__(self):
        try:
            self._remove_meta_path()
        except:
            pass
