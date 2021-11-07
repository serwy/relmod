import sys
import os
import json
from collections import defaultdict

from .cache import FileStat


def _dep_warn(filename):
    head, tail = os.path.split(filename)

    rename = None
    for pre in ('', '.'):
        if tail.lower() == pre + 'fakemod.site':
            rename = os.path.join(head, pre +'relmod.site')

    if rename is not None:
        import warnings
        warnings.warn(
            ('"fakemod.site" deprecated.\n' +
            ('    rename %r\n' % filename) +
            ('    to:    %r' % rename)),
            FutureWarning
        )


def load_site(filename):

    if os.path.isfile(filename):
        _dep_warn(filename)
        with open(filename, 'r') as fid:
            try:
                d = json.load(fid)
            except Exception:
                print('Unable to load  %r' % filename, file=sys.stderr)
                d = []

    elif os.path.isdir(filename):
        # treat a directory as load everything
        d = [['*', filename]]
    else:
        d = []

    # TYPE CHECK:
    try:
        for k, v in d:
            assert(isinstance(k, str))
            assert(isinstance(v, str))
    except:
        print('Invalid structure  %r' % filename, file=sys.stderr)
        d = []

    # convert to dict
    dd = {}
    for k, v in d:
        if k != '*':
            dd[k] = v
        else:
            if '*' not in dd:
                dd['*'] = []
            dd['*'].append(v)
    return dd


def _expand_star(path):
    dd = {}
    if os.path.isdir(path):
        for f in os.listdir(path):
            name = utils.fs_name_to_attr(f)
            if name == '':
                continue
            p = os.path.join(path, f)
            dd.setdefault(name, p)
    return dd


def _expand_path(path):
    return os.path.abspath(os.path.expanduser(path))


class _FakeSiteConfig:

    def __init__(self, registry):
        self.registry = registry
        self.user_d = {}
        self._envlist = ''
        self._defaults = []
        self.filestat = FileStat()
        self.user_files = [(self.user_d, '', '')]
        self.site_files = []

    @property
    def d_paths(self):
        x = []
        x.extend(self.user_files)
        x.extend(self.site_files)
        return x

    def reset(self):
        self.user_d.clear()
        self.user_files = [(self.user_d, '', '')]
        self.filestat.stats.clear()  # reset cache

    def use(self, filename):
        self.user_files.append(({}, filename, _expand_path(filename)))

    def set_site_files(self, envlist, defaults):
        self._envlist = envlist  # semicolon separated values
        self._defaults = defaults

        _site_files = []

        # specifying `break` in the environment variable FAKEMOD_SITE
        # ignores using the default files
        for file in envlist.split(';'):
            file = file.strip()
            if file.lower() != 'break':
                if file:
                    _site_files.append(file)
            else:
                break
        else:
            if self._defaults:
                _site_files.extend(self._defaults)

        _site_files_abs = [
            os.path.abspath(os.path.expanduser(f))
            for f in _site_files]

        site_files = []
        for fp in _site_files:
            fp_abs = _expand_path(fp)
            site_files.append(({}, fp, fp_abs))

        self.site_files = site_files
        self.filestat.stats.clear()  # reset cache

    def _setitem(self, name, value):
        self.user_d[name] = value

    def _needs_load(self, fp):
        return self.filestat.file_changed(fp)

    @property
    def d_list(self):
        for d, fp_str, fp_abs in self.d_paths:
            if fp_abs:
                if self._needs_load(fp_abs):
                    try:
                        d2 = load_site(fp_abs)
                    except Exception:
                        d2 = {}

                    d.clear()  # hard reset
                    d.update(d2)

            if '*' in d:
                for p in d['*']:
                    dd = _expand_star(p)
                    for k, v in dd:
                        d.setfault(k, v)
            yield d

    def _getitem(self, name):
        for d in self.d_list:
            if name in d:
                return d[name]
        raise KeyError(name)

    def _dir(self):
        n = set()
        for d in self.d_list:
            n.update(d)
        n.discard('*')
        return sorted(n)

    def at(self, p):
        return self.registry.at(p)

    def _destroy(self):
        pass


_fakesites = {}  # indirection to the implementation


class FakeSite:

    def __init__(self, registry):
        _fakesites[self] = _FakeSiteConfig(registry)

    def __del__(self):
        if _fakesites:
            x = _fakesites.pop(self, None)
            if x:
                x._destroy()

    def __getattr__(self, name):
        try:
            p = self[name]
        except KeyError:
            raise AttributeError(name) from None

        return _fakesites[self].at(p)

    def __setattr__(self, name, value):
        raise ValueError('read-only attributes')

    def __delattr__(self, name):
        raise ValueError('read-only attributes')

    def __setitem__(self, name, value):
        _fakesites[self]._setitem(name, value)

    def __delitem__(self, name):
        _fakesites[self]._delitem(name)

    def __getitem__(self, name):
        return _fakesites[self]._getitem(name)

    def __dir__(self):
        return _fakesites[self]._dir()

    def __invert__(self):
        # Avoid namespace polution/collisions
        # with user-defined names. Access the
        # shadow namespace by inverting the object
        return _fakesites[self]


_site_files_default = [
    './relmod.site',
    './fakemod.site',
    '~/.relmod.site',
    '~/.fakemod.site',
    '~/.config/relmod.site',
    '~/.config/fakemod.site',
    ]


def create_default_site(registry):
    site = FakeSite(registry)

    fsite = os.environ.get('FAKEMOD_SITE', '')
    if fsite:
        import warning
        warning.warn(
            'FAKEMOD_SITE environment variable deprecated.\n'
            'Use RELMOD_SITE instead.')

    rsite = os.environ.get('RELMOD_SITE', fsite)
    (~site).set_site_files(
        rsite,
        _site_files_default)
    return site
