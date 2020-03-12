# FakeMod

A utility to automatically reload a module if modified,
or emulate a namespace package.


## Example

    import os
    os.makedirs('./utilities', exist_ok=True)
    with open('./utilities/tool.py', 'w') as f:
       f.write(r'''if 1:

        def func(a):
            print('func', a)

        ''')

    import fakemod
    mod = fakemod.at('./utilities')
    mod.tool.func(123)


## Usage

Place into `__init__.py`:

    import fakemod; fakemod.local(vars())

Also place into `local.py` to allow for 
`from . import local` to access other files in the 
same directory.

