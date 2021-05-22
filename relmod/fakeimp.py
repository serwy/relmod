import os

from . import utils
from . import proxy


def count_dots(p):
    x0 = len(p)
    p = p.lstrip('.')
    x1 = len(p)
    return (x0-x1), p


class FakeImport:

    def __init__(self, globalsdict):
        self._g = globalsdict

    def __call__(self, path, as_=None):
        return self._fimport(self._g, path, as_)

    def _fimport(self, g, path, as_):
        g = self._g
        orig_path = path
        if '/' in path or '\\' in path:
            # convert filesystem string to python name string
            path = os.path.normpath(path)
            if '\\' in path:
                path = path.replace('\\', '/')
            if path.endswith('.py'):
                path = path[:-3]
            path = path.replace('../', '.')
            path = path.replace('/', '.')
            path = '.' + path
            # path has been converted from filesystem to python name

        # convert to import
        d, path = count_dots(path)
        if d == 0:
            d = 1

        if path == '':
            # need to go up one more level, and get me
            d = d + 1
            #f = g.get('__file__', None)
            #if f is None:
            #    f = g['__path__'][0]
            f = g['__fullpath__']
            parts = utils.path_to_parts(f)
            path = parts[-d]

        if '.' not in path:
            name = ''
            fromlist = (path,)
            as_ = as_ or path
        else:
            name, sep, rest = path.rpartition('.')
            fromlist = (rest,)
            as_ = as_ or rest

        if '__fakeregistry__' in g:
            imp = g['__fakeregistry__']._import
        else:
            imp = g['__builtins__']['__import__']

        w = imp(name, g, None, fromlist, d)
        w = getattr(w, fromlist[0])  # get the item
        if as_ == '*':
            return self._star(g, w)
        else:
            w = proxy.wrap(w, g['__fullpath__'])
            if as_:
                check = utils.fs_name_to_attr(as_)
                if not check:
                    raise ImportError('use as_ to rename %r' % as_)
                g[as_] = w
            return w

    def _ffrom(self, g, path, import_, as_):
        if import_ == '*':
            return self._fimport(g, path, '*')

        mod = self._fimport(g, path, None)
        what = [i.strip() for i in import_.split(',')]

        if len(what) == 1:
            as_ = as_ or what[0]
            d = {as_: getattr(mod, what[0])}
        else:
            assert(as_ is None)
            d = {}
            for n in what:
                d[n] = getattr(mod, n)

        g.update(d)
        return d

    @staticmethod
    def _star(g, mod):
        _all = getattr(mod, '__all__', None)
        if _all is None:
            _all = [i for i in dir(mod) if i[0] != '_']

        SKIP = ['fimport', 'ffrom']

        for s in SKIP:
            while s in _all:
                _all.remove(s)

        d = {}
        for name in _all:
            d[name] = getattr(mod, name)

        g.update(d)

        return d


class FakeFrom(FakeImport):

    def __call__(self, path, import_, as_=None):
        return self._ffrom(self._g, path, import_, as_)
