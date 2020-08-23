# `fakemod` - auto-reloading module development library

Place your Python cell code in a directory and start using it immediately.

* Use directories as auto-loading namespaces.
* Use file names as auto-deep-reloading modules.
* Run `unittest` cases easily.

Running the following:

    import fakemod

    with open('./myfunc.py', 'w') as f:
        f.write("""
    def add(x, y):
        return x + y
    """)  # create a file with a function

    lib = fakemod.at('.')  # create a local namespace module

    print(lib.myfunc.add(3, 4))  # call the function from myfunc.py

    import unittest
    class TestMyFunc(unittest.TestCase):
        def test_add(self):
            self.assertEqual(lib.myfunc.add(3, 4), 7)  # create a test

    fakemod.runtest(TestMyFunc)  # run the test

produces this output:

    7
    test_add (__main__.TestMyFunc) ... ok

    ----------------------------------------------------------------------
    Ran 1 test in 0.003s

    OK


## Motivation

The `fakemod` library allows for placing helper modules and functions
in a directory and making them quickly available, with reloading if needed.
This helps with converting existing notebook cells into re-usable
library code.

Tests for these library functions can be developed easily along the way.

When you're finished, you no longer need `fakemod`. You have a readily usable
Python library. Packaging is up to you.


## Examples


Use a file directly:

    myfunc = fakemod.at('./myfunc.py')

Relative directories can be given:

    lib = fakemod.at('.')
    parent = lib['../']  # go up a directory, using []

which is the same as

    parent = fakemod.up('.')


### Top-level Modules

You can register a directory or file as a top-level module and then import it.

    fakemod.toplevel('myfunc', './myfunc.py')
    import myfunc
    myfunc.add(3, 4)


### Testing

Run a single test case method:

    fakemod.runtest(TestMyFunc, 'test_add')

Find and run all `unittest.TestCase` classes in a module:

    fakemod.testmod(mod)

Only run a single class in a test file and exit:

    @fakemod.testonly()
    class Test(unittest.TestCase):
        ...

### Cell Mode

The `.install` function will use the current working directory
if `__file__` is not defined. This is useful in a cell-mode
environment.

    here = fakemod.install(globals())

Use parent directory of `__file__`:

    here = fakemod.up(__file__)


### Fake `fimport`, Fake `ffrom`

The `fimport` and `ffrom` objects can accept filesystem paths or
a Python-like relative import with leading dots.

To use fake import, fake from:

    fakemod.install(globals())  # injects fimport, ffrom

    fimport('./myfunc.py', as_='myfunc')
    myfunc.add(3, 4)

Import a nested name directly:

    fimport('.myfunc.add')
    print(add(3,4))

which is the same as

    ffrom('.myfunc', import_='add')


## How it works

The `.at`, `.up`, `.install` functions return `FakeModuleType` objects
wrapped in a `ModuleProxy` object that triggers reloading when
accessing its attributes, if needed. Namespace and `__init__.py` fake
modules perform auto-reloading on attribute access as well.

The files and directories accessed via `fakemod` are not found in
`sys.modules`. These "fake modules" are handled separately and
behave as regular Python modules, with enhancements. Relative
imports within a fake module perform dependency tracking,
allowing for lazy deep-reloading of modules.


## Install

    pip install fakemod


## Zen
* Beautiful is better than ugly.
    - `fakemod` is a useful alternative to `importlib.reload`
       and `sys.path` hacking.

* Explicit is better than implicit.
    - If you want a file, request it.

* Namespaces are one honking great idea -- let's do more of those!
    - `fakemod` turns the filesystem into a namespace

* There should be one-- and preferably only one --obvious way to do it.
    - `fakemod` is the way ;-)
