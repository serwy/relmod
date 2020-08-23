import importlib


"""
AutoImport

Attributes are top-level module names,
lazy import on demand.

"""


class AutoImport:
    def __init__(self):
        self._cache = {}

    def __getattr__(self, name):
        if name not in self._cache:
            mod = importlib.import_module(name)
            self._cache[name] = mod
        return self._cache[name]

    def __dir__(self):
        return sorted(self._cache)
