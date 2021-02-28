from collections import defaultdict
import os

_missing = object()

_blank_stat = os.stat_result([0] * len(os.stat(__file__)))

def _stat_changed(old_stat, new_stat):
    return old_stat.st_mtime != new_stat.st_mtime


class FileStat:
    def __init__(self):
        self.stats = {}
        self.inhibit = False

    def blank(self):
        return _blank_stat

    def stat(self, filename):
        filename = os.path.abspath(filename)

        if self.inhibit:
            return self.stats.get(
                filename,
                _blank_stat
            )
        try:
            stat = os.stat(filename)
        except IOError:
            #return None
            stat = _blank_stat
        self.stats[filename] = stat
        return stat

    def changed(self, s1, s2):
        res = _stat_changed(s1, s2)
        return res


def deep_check_list(filename, deps):
    seen = set()
    def walk(filename):
        d = deps.get(filename, None)
        if d:
            for k, v in d.items():
                if k in seen:
                    continue
                seen.add(k)
                walk(k)
    walk(filename)
    return seen


class CacheSystem:
    def __init__(self, reg):
        self.reg = reg
        self.filestat = FileStat()
        self.modstat = {}
        self.check_invalid = True

    def load(self, factory, filename):
        raise NotImplementedError

    def invalidate(self, filename):
        raise NotImplementedError


class CacheTracer(CacheSystem):
    def __init__(self, cache):
        self.__dict__['_CacheTracer__cache'] = cache

    def __getattr__(self, name):
        return getattr(self.__cache, name)

    def __setattr__(self, name, value):
        setattr(self.__cache, name, value)

    def __pfactory(self, factory):
        def printer_factory(filename):
            print('build factory', filename)
            return factory(filename)
        return printer_factory

    def load(self, factory, mods, filename, inside):
        print('load', filename, inside)
        mod, load = self.__cache.load(
            self.__pfactory(factory),
            mods, filename, inside)
        print('load return:', load)
        return (mod, load)

    def invalidate(self, filename):
        print('invalidate', filename)
        res = self.__cache.invalidate(filename)
        print('invalidate return: ', res)
        return res

    def __dir__(self):
        return dir(self.__cache)


class NoCache(CacheSystem):

    def load(self, factory, filename):
        m = self.reg.mods[filename] = factory(filename)
        return m, False

    def invalidate(self, filename):
        return [filename]


class FirstLoadCache(CacheSystem):
    def __init__(self, filestat):
        CacheSystem.__init__(self, filestat)
        self._invalid = set()

    def load(self, factory, filename):
        reg = self.reg

        load = False
        if filename not in reg.mods:
            load = True
        elif (self.check_invalid and
              (filename in self._invalid)):
            load = True

        if load:
            stat = self.filestat.stat(filename)
            reg.mods[filename] = factory(filename)
            self.modstat[filename] = stat
            self._invalid.discard(filename)

        from_cache = not load
        return reg.mods[filename], from_cache

    def invalidate(self, filename):
        self._invalid.add(filename)
        return [filename]


class ShallowCache(CacheSystem):
    def __init__(self, filestat):
        CacheSystem.__init__(self, filestat)


    def _do_load(self, factory, filename, stat):
        m = self.reg.mods[filename] = factory(filename)
        self.modstat[filename] = stat
        return m

    def load(self, factory, filename):
        reg = self.reg
        load = False
        stat = self.filestat.stat(filename)
        if filename not in reg.mods:
            load = True
        elif self.check_invalid:
            last_stat = self.modstat.get(filename, None)
            if last_stat is None:
                last_stat = self.filestat.blank()
            if self.filestat.changed(stat, last_stat):
                load = True

        if load:
            self._do_load(factory, filename, stat)

        m = reg.mods[filename]
        from_cache = not load
        return m, from_cache


    def invalidate(self,  filename):

        if filename in self.modstat:
            self.modstat[filename] = self.filestat.blank()
        return [filename]


class SmartCache(CacheSystem):
    def __init__(self, filestat):
        CacheSystem.__init__(self, filestat)
        self.cache_invalid = defaultdict(set)
        self.deep = True


    def _would_also_invalidate(self, filename):
        # return files that depend on filename
        if self.deep:
            inv = deep_check_list(filename, self.reg._revdeps)
        else:
            inv = set()
        return inv

    def _invalidate(self, filename, dry=False):
        reg = self.reg
        inv = self._would_also_invalidate(filename)
        inv.add(filename)
        if not dry:
            inv = [i for i in inv if i in reg.mods]
            for i in inv:
                self.cache_invalid[i].add('inv:' + filename)
        return list(inv)

    def _fs_check(self, filename):
        reg = self.reg
        if self.deep:
            d = deep_check_list(filename, reg._deps)
        else:
            d = set()

        d.add(filename)
        file_changed = set()
        for file in d:
            new_stat = self.filestat.stat(file)
            if new_stat is None:
                if file != filename:
                    continue

            last_stat = self.modstat.get(file, _missing)
            if last_stat is _missing:
                changed = True
            elif self.filestat.changed(new_stat, last_stat):
                changed = True
            else:
                changed = False

            if changed:
                file_changed.add(filename)

        return file_changed

    def _cache_load(self, factory, filename):
        reg = self.reg
        if filename not in reg.mods:
            needs_load = True
        elif (self.check_invalid and
              (filename in self.cache_invalid)):
            needs_load = True
        else:
            needs_load = False

        if needs_load:
            if self.deep:
                inv = self._would_also_invalidate(filename)
                for i in inv:
                    if i == filename:
                        continue
                    self.cache_invalid[i].add('load:'+filename)

            stat = self.filestat.stat(filename)
            try:
                last_stat = self.modstat.get(filename)
                ci = self.cache_invalid.pop(filename, None)
                self.modstat[filename] = stat
                reg.mods[filename] = factory(filename)
            except:
                if ci:
                    self.cache_invalid[filename] = ci
                if last_stat:
                    self.modstat[filename] = last_stat
                raise

        m = reg.mods[filename]

        from_cache = not needs_load
        return m, from_cache

    def load(self, factory, filename):
        reg = self.reg
        if ((self.check_invalid) and
            (filename not in self.cache_invalid) and
            (filename in reg.mods)):

            # is the cache still valid?
            # did the filesystem change ?
            inv = self._fs_check(filename)
            if inv:
                for i in inv:
                    self.cache_invalid[i].add('fs:'+filename)
                # a deeper file was changed, need to do
                # a reload of this file
                self.cache_invalid[filename].add('fs:'+repr(inv))

        m, from_cache = (
            self._cache_load(factory, filename)
        )
        return m, from_cache

    def invalidate(self, filename):
        reg = self.reg
        inv = self._invalidate(filename)
        return list(inv)
