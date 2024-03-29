##
## Author:    Roger D. Serwy
## Copyright: 2020-2022, Roger D. Serwy
##            All rights reserved.
## License:   BSD 2-Clause, see LICENSE file from project
##

import os
import datetime
import sys


def now():
    return datetime.datetime.now().isoformat()

def fproperty(func):
    return property(*func())


def strip_file(b):
    if os.path.isfile(b):
        return os.path.split(b)[0]
    return b


def path_to_parts(path):
    p = os.path.abspath(path)
    return p.split(os.path.sep)


def parts_to_path(parts):
    s = os.path.sep
    return s.join(parts)


def fs_name_to_attr(n):
    # filesystem name to python attribute
    if not n:
        return ''
    if n.endswith('.py'):
        n = n[:-3]

    # Python 3.4 compatibility - no .isnumeric()
    if n[0] in '0123456789': #.isnumeric():
        return ''

    for bad in ' .:-=\\#@()[]^$%"\';,?~{}!/|':
        if bad in n:
            return ''
    if n == '__pycache__':
        return ''

    return n


def expand_path(path):
    p = os.path.expanduser(path)
    return os.path.abspath(p)

def grab_init(fp):
    if os.path.isdir(fp):
        fpy = os.path.join(fp, '__init__.py')
        if os.path.isfile(fpy):
            fp = fpy
    return fp

def split_init(fp):
    head, tail = os.path.split(fp)
    if tail == '__init__.py':
        fp = head
    return fp


def execfile(filename, globals=None, locals=None,
             flags=0, dont_inherit=False):
    """execute a filename in the given dictionary, using
       provided compile flags."""
    if globals is None:
        import __main__
        globals = __main__.__dict__

    fullpath = os.path.abspath(filename)
    with open(fullpath, 'r') as f:
        src = f.read()

    code = compile(src, fullpath, 'exec',
                   flags=flags,
                   dont_inherit=dont_inherit)

    exec(code, globals, locals)


def get_globals(depth):
    """ Return globals from the caller, depth=0 is caller frame."""
    frame = sys._getframe()
    for d in range(depth+1):
        frame = frame.f_back
    return frame.f_globals
