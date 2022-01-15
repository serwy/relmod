"""
AutoImport

Attributes are top-level module names, lazy import-on-demand.

"""

##
## Author:    Roger D. Serwy
## Copyright: 2020-2022, Roger D. Serwy
##            All rights reserved.
## License:   BSD 2-Clause, see LICENSE file from project
##

import importlib
import sys

__all__ = ['AutoImport']

class AutoImport:
    def __init__(self):
        self._cache = {}
        self._from_sysmodules()

    def _from_sysmodules(self):
        for name in sys.modules:
            base, sep, rest = name.partition('.')
            if sep == '':
                self._cache.setdefault(
                    name, sys.modules[name])

    def __getattr__(self, name):
        if name not in self._cache:
            mod = importlib.import_module(name)
            self._cache[name] = mod
        return self._cache[name]

    def __dir__(self):
        self._from_sysmodules()
        return sorted(self._cache)
