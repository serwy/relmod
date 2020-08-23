import types
from collections import defaultdict
import os

from . import utils
from . import fmods


_mp_fakedict = {}

def _mp_get(self):
    d = _mp_fakedict[id(self)]
    fp = d[':filename:']
    registry = d[':registry:']
    m = registry._load_file(fp)
    return m


def _by_mod(mod, inside):
    # Could be a classmethod,
    # is not to avoid namespace pollution
    reg = mod.__fakeregistry__
    fp = mod.__file__
    if fp is None:
        fp = mod.__path__[0]
    return ModuleProxy(reg, fp, inside)


class ModuleProxy:
    # allows for lazy loading
    # proxy to a particular file

    def __init__(self, registry, filename, inside):
        _mp_fakedict[id(self)] = fd = {}
        fd[':filename:'] = filename
        fd[':registry:'] = registry
        fd[':inside:'] = inside
        if os.path.isfile(filename):
            if inside:
                registry._add_dep(filename, inside)


    def __eq__(self, other):
        if isinstance(other, self.__class__):
            sd = self.__fakedict__
            od = other.__fakedict__
            care = (':filename:', ':registry:')
            return all([sd[n] == od[n] for n in care])
        else:
            return False

    @property
    def __fakedict__(self):
        return _mp_fakedict[id(self)]

    @property
    def __dict__(self):
        m = _mp_get(self)
        return m.__dict__

    @property
    def __doc__(self):
        m = _mp_get(self)
        a = getattr(m, '__doc__')
        return a

    def __getattr__(self, name):
        m = _mp_get(self)
        a = getattr(m, name)

        if isinstance(a, fmods.FakeModuleType):
            a = _by_mod(a, self.__fakedict__[':inside:'])
        return a

    def __setattr__(self, name, value):
        m = _mp_get(self)
        return setattr(m, name, value)

    def __delattr__(self, name):
        m = _mp_get(self)
        return delattr(m, name)

    def __getitem__(self, relpath):
        m = _mp_get(self)
        return m[relpath]

    def __dir__(self):
        m = _mp_get(self)
        return dir(m)

    def __repr__(self):
        d = self.__fakedict__
        fp = d[':filename:']
        if os.path.exists(fp):
            missing = ''
        else:
            missing = '(MISSING)'

        name = '"%s"' % fp
        return "<moduleproxy %r%s>" % (fp, missing)

    def __del__(self):
        del _mp_fakedict[id(self)]


def wrap(m, inside='__file__'):
    if isinstance(m, fmods.FakeModuleType):
        m = _by_mod(m, inside)
    return m

def unwrap(mp):
    if isinstance(mp, ModuleProxy):
        return _mp_get(mp)
    else:
        return mp
