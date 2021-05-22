"""
fakemod redirection stub

The `fakemod` package has been renamed to `relmod`.
Using `import fakemod` in existing code will work,
but will issue a warning message to change the code.

Any `fakemod.site` files will need to be renamed to
`relmod.site`. For the moment, both are valid.

"""

import relmod
from relmod import *
__all__ = relmod.__all__[:]

def __warn():
    import sys
    import os
    frm = sys._getframe()
    # walk up the frame, find where fakemod is imported
    frm = frm.f_back
    stacklevel = 3
    for _ in range(10):
        frm = frm.f_back
        if frm is None:
            break
        filename = frm.f_code.co_filename
        if filename.startswith('<frozen'):
            continue
        head, tail = os.path.split(filename.lower())
        if head.endswith('relmod'):
            stacklevel += 1
            continue
        break

    import warnings as _warnings
    _warnings.warn(
        "`fakemod` renamed to `relmod`, "
        "use `import relmod as fakemod`",
        stacklevel=stacklevel,
    )

__warn()
