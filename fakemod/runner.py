import sys
import unittest
import types

__all__ = ['runtest', 'testonly', 'testmod']

def runtest(tc, test_names='', verbosity=2, **kw):
    # test names, a comma-separated list of methods in the class

    if test_names == '':
        s = unittest.makeSuite(tc)
    else:
        tests = []
        names = [i.strip() for i in test_names.split(',')]
        for test_method in names:
            tests.append(tc(test_method))
        s = unittest.TestSuite(tests)
    kw['verbosity'] = verbosity
    rn = unittest.runner.TextTestRunner(**kw)
    return rn.run(s)


def testonly(test_names='', **kw):
    import __main__
    g = __main__.__dict__

    def wrapper(obj, test_names=test_names):
        name = g['__name__']
        if name in ('__main__'):
            print('-' * 72)
            print(' WARNING: @fakemod.testonly present on', obj)
            print('-' * 72)
            r = runtest(obj, test_names, **kw)
            sys.exit(not r.wasSuccessful())
        return obj

    if callable(test_names):
        return wrapper(test_names, '')

    return wrapper


def testmod(mod, **kw):
    todo = []
    d = mod.__dict__
    for k in sorted(mod.__dict__.keys()):
        v = d[k]
        if isinstance(v, type):
            if issubclass(v, unittest.TestCase):
                todo.append((k, v))

    result = {}
    for k, v in todo:
        result[k] = runtest(v, **kw)

    return result
