import os
import types

try:
    import builtins
except:
    # python 2.7, because why not
    builtins = lambda: None
    builtins.__dict__ = __builtins__


class FakeBuiltins(types.ModuleType):

    def __init__(self, name, b=None):
        if b is None:
            b = builtins.__dict__

        types.ModuleType.__init__(self, name)
        self.__dict__.update(b)
        self.__dict__['__name__'] = name
        self._orig = {}

    def _factory(self, name, factory):
        # the func is called with the original function
        # as its argument
        d = self.__dict__
        orig = d[name]
        self._orig[name] = orig

        new_func = factory(orig)
        d[name] = new_func

        return orig

    def override(self, name):
        def wrapper(func):
            return self._factory(name, func)
        return wrapper



class FakeModuleType(types.ModuleType):

    def __repr__(self):
        if self.__name__.startswith('fakemod.at'):
            return '<fakemodule %r>' % (
            self.__name__,)
        else:
            # importlib reload changed the name
            return '<fakemodule %r from %r>' % (
            self.__name__, self.__fullpath__)

    def __getitem__(self, name):
        return self.__getattr__(name)

    def __getattr__(self, name):
        d = self.__dict__
        if d['__fakebrowse__']:
            m = d['__fakeregistry__']._get_mod(d, name)
            if m is not None:
                return m

        if name in d:
            return d[name]

        msg = '%s for %r' % (name, self)
        raise AttributeError(msg)

    def __setattr__(self, name, value):
        self.__dict__[name] = value

    def __delattr__(self, name):
        if name in self.__dict__:
            del self.__dict__[name]
        else:
            raise AttributeError(name)

    def __dir__(self):
        d = self.__dict__

        if d['__fakebrowse__']:
            return d['__fakeregistry__']._dir_mod(d)

        mdir = d.get('__dir__', None)
        if callable(mdir):
            return mdir()

        return sorted(d.keys())
