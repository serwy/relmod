# `relmod` - auto-reloading module development library

Place your Python code in a directory and start using it immediately.

* Import file names as auto-deep-reloading modules.
* Import directories as auto-loading namespaces.
* Run `unittest` cases easily.

Running the following:

    import relmod

    # create a file with a function
    with open('./myfunc.py', 'w') as f:
        f.write("""
    def add(x, y):
        return x + y
    """)

    myfunc = relmod.at('./myfunc.py')  # load as a module

    print(myfunc.add(3, 4))  # call the function

    import unittest
    class TestMyFunc(unittest.TestCase):
        def test_add(self):
            self.assertEqual(myfunc.add(3, 4), 7)  # create a test

    relmod.runtest(TestMyFunc)  # run the test

produces this output:

    7
    test_add (__main__.TestMyFunc) ... ok

    ----------------------------------------------------------------------
    Ran 1 test in 0.003s

    OK


## Motivation

The `relmod` library allows for placing helper modules and functions
in a directory and making them quickly available, with reloading if needed.
This helps with converting existing notebook cells into re-usable
library code.

Tests for these library functions can be developed easily along the way.

When you're finished, you no longer need `relmod`. You have a readily usable
Python library. Packaging is up to you.


## Examples

Use the current working directory as a namespace module:

    lib = relmod.at('.')

Entering folders that are not valid Python identifiers is supported:

    py = lib['./Documents and Settings'].sub.folders

Relative directories can be given:

    parent = lib['../']  # go up a directory, using []

which is the same as

    parent = relmod.up('.')


### Importing

Import an object from a module into the global namespace:

    relmod.imp('./myfunc.py', 'add')

Rename references in the import using `as`

    relmod.imp('./myfunc.py', 'add as add2')
    print(add2(3, 4))

Names can be comma-separated, e.g. `'add, sub, mult, div'`.


Import a filename as another name:

    relmod.imp('./myfunc.py as mfunc')
    mfunc.add(1, 2)

__Note:__ Non-module objects imported using `relmod.imp` are not automatically
reloaded if changes occur to the file. You will need to reimport them.

The prior importing functions `fimport` and `ffrom` have been
deprecated and will be removed in a later version.




### Cell Mode

The `.install` function will use the current working directory
if `__file__` is not defined. This is useful in a cell-mode
environment.

    here = relmod.install(globals())

Using `.install` allows for relative imports within `__main__`:

    from . import myfunc
    print(myfunc.add(3, 4))

Use the parent directory of `__file__` as a namespace:

    here = relmod.up(__file__)


### Top-level Modules

You can register a directory or file as a top-level module and then import it.

    relmod.toplevel('myfunc', './myfunc.py')
    import myfunc
    myfunc.add(3, 4)


### Testing

Run a single test case method:

    relmod.runtest(TestMyFunc, 'test_add')

Find and run all `unittest.TestCase` classes in a module:

    relmod.testmod(mod)

Only run a single class in a test file and exit:

    @relmod.testonly()
    class Test(unittest.TestCase):
        ...


## How it works

The `.use`, `.imp`, `.at`, `.up`, and `.install` functions return `FakeModuleType`
objects wrapped in a `ModuleProxy` object that trigger reloading when
accessing its attributes, if needed. Namespace and `__init__.py` fake
modules perform auto-reloading on attribute access as well.

The files and directories accessed via `relmod` are not found in
`sys.modules`. These "fake modules" are handled separately and
behave as regular Python modules, with enhancements. Relative
imports within a fake module perform dependency tracking,
allowing for lazy deep-reloading of modules.

The auto-reloading of a module's source __will not hot-patch__ existing
objects like the `%autoreload` magic from IPython. Hot-patching makes
certain assumptions about your code, and if violated, will introduce
subtle bugs.

### Relative Path Resolution

The `relmod.at` and `relmod.up` functions use `os.getcwd()` when resolving relative paths.

The `relmod.use` and `relmod.imp` functions use `__file__` from the calling frame's
globals dictionary, and uses `os.getcwd()` as a fallback if `__file__` is not defined.

It is recommended to use `.use` and `.imp` in library scripts where relative paths must
resolve relative to the script's file path rather than the current working directory.


## Install

    pip3 install relmod


## Zen
* Beautiful is better than ugly.
    - `relmod` is a useful alternative to `importlib.reload`
       and `sys.path` hacking.

* Explicit is better than implicit.
    - If you want a file, request it.

* Namespaces are one honking great idea -- let's do more of those!
    - `relmod` turns the filesystem into a namespace

* There should be one-- and preferably only one --obvious way to do it.
    - `relmod` is the way ;-)
