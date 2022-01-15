##
## Author:    Roger D. Serwy
## Copyright: 2020-2022, Roger D. Serwy
##            All rights reserved.
## License:   BSD 2-Clause, see LICENSE file from project
##

import sys
import unittest
import types
import io

__all__ = ['runtest', 'testmod', 'testonly', 'testfocus']


def _runtest(tc, test_names='', verbosity=2, **kw):
    # test names, a comma-separated list of methods in the class

    testonly = []
    testfunc = []
    for name in dir(tc):
        if name.startswith('test_'):
            func = getattr(tc, name)
            if hasattr(func, '_relmod_testfocus'):
                testonly.append(name)
                testfunc.append(func)

    if testfunc and verbosity > 0:

        stream = kw.get('stream', None)
        if stream is None:
            stream = sys.stderr

        def sprint(*args):
            print(*args, file=stream)

        sprint('-' * 70)
        sprint(' Note: @relmod.testfocus present on: ')
        for func in testfunc:
            sprint('    line % 4i - %r' % (func.__code__.co_firstlineno, func))
        sprint('', func)
        sprint()
        if test_names:
            sprint('Ignoring provided test_names=%r' % (test_names, ))
        sprint('-' * 70)


    if testonly:
        test_names = ','.join(testonly)


    if test_names == '':
        s = unittest.makeSuite(tc)
    else:
        testonly = []
        tests = []
        names = [i.strip() for i in test_names.split(',')]
        for test_method in names:
            tests.append(tc(test_method))

        s = unittest.TestSuite(tests)
    kw['verbosity'] = verbosity
    rn = unittest.runner.TextTestRunner(**kw)
    return rn.run(s)


def runtest(tc, test_names='', verbosity=2, **kw):
    """Run unittest on a given TestCase class.
       May be used as a decorator if tc=None.
    """
    if tc is None:
        def wrapper(cls):
            _runtest(cls, test_names, verbosity, **kw)
            return cls
        return wrapper
    else:
        return _runtest(tc, test_names, verbosity, **kw)


def testfocus(func):
    """Decorator to focus on this test when using `runtest`"""
    func._relmod_testfocus = True
    return func

def testonly(test_names='', **kw):
    import __main__
    g = __main__.__dict__

    def wrapper(obj, test_names=test_names):
        name = g['__name__']
        if name in ('__main__'):
            print('-' * 72)
            print(' Note: @relmod.testonly present on', obj)
            r = runtest(obj, test_names, **kw)
            sys.exit(int(not r.wasSuccessful()))
        return obj

    if callable(test_names):
        return wrapper(test_names, '')

    return wrapper


def testmod(mod, **kw):
    """Find all TestCase classes and send to `runtest`"""
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
