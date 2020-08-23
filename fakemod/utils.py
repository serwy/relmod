import os
import datetime


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
