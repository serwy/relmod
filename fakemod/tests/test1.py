# Unit test

# $ python -m unittest -v fakemod.tests.test1

import unittest
import types
import os

import fakemod


class TestFileStat(unittest.TestCase):

    def test_first(self):
        _fs = fakemod._fm2._fs
        _fs._forget(__file__)
        for x in [False, True, None]:
            s = _fs.is_same(__file__, first=x, update=False)
            self.assertTrue(s == x)

    def test_change(self):
        _fs = fakemod._fm2._fs
        _fs._forget(__file__)

        s = _fs.is_same(__file__, first=None, update=True)
        self.assertTrue(s is None)

        _fs._blank(__file__)

        s = _fs.is_same(__file__, first=None, update=True)
        self.assertFalse(s)


class TestNamespace(unittest.TestCase):
    def setUp(self):
        head, tail = os.path.split(__file__)
        _mod_ns = os.path.join(head, 'mod_ns')
        _mod_reg = os.path.join(head, 'mod_reg')

        self.mod_ns = fakemod.at(_mod_ns)
        self.mod_reg = fakemod.at(_mod_reg)

    def test_mod_ns(self):
        self.assertTrue(hasattr(self.mod_ns, 'func'))
        self.assertFalse(hasattr(self.mod_ns, 'missing'))

    def test_nested_ns(self):

        t = type(self.mod_ns)
        s = self.mod_ns.sub_ns
        self.assertTrue(isinstance(s, t))

    def test_nested_ns_func(self):
        self.assertTrue(hasattr(self.mod_ns.sub_ns, 'func'))
        self.assertFalse(hasattr(self.mod_ns.sub_ns, 'missing'))


    def test_reload(self):
        _fs = fakemod._fm2._fs
        self.assertTrue(isinstance(self.mod_ns.func.x, types.FunctionType))

        self.mod_ns.func.x = None
        self.assertTrue(self.mod_ns.func.x is None)

        _fs._blank(self.mod_ns.func.__file__)
        self.assertTrue(isinstance(self.mod_ns.func.x, types.FunctionType))


class TestCircular(unittest.TestCase):
    def setUp(self):
        head, tail = os.path.split(__file__)
        _mod_circ = os.path.join(head, 'mod_circ')
        self.mod_circ = fakemod.at(_mod_circ)

    def test_circ(self):
        with self.assertRaises(ImportError):
            self.mod_circ.a


    def test_circ2(self):
        with self.assertRaises(ImportError):
            self.mod_circ.self


if __name__ == '__main__':
    unittest.main()

