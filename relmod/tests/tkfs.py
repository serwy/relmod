import os


class TinyKeyFS:
    def __init__(self, base):
        self.base = os.path.abspath(base)
        self._ensure_path(self.base, split=False)

    def _ensure_path(self, p, split=True):
        if split:
            head, tail = os.path.split(p)
        else:
            head = p
        if not os.path.exists(head):
            os.makedirs(head)

    def __getitem__(self, key):
        p = os.path.join(self.base, key)
        if key.endswith('/'):
            return TinyKeyFS(p)
        with open(p, 'r') as fid:
            return fid.read()

    def __setitem__(self, key, value):
        p = os.path.join(self.base, key)
        self._ensure_path(p)
        with open(p, 'w') as fid:
            fid.write(value)
            if not value.endswith('\n'):
                fid.write('\n')

    def __delitem__(self, key):
        p = os.path.join(self.base, key)
        os.remove(p)

    def update(self, d):
        for k, v in d.items():
            self[k] = v

    def path(self, key):
        p = os.path.join(self.base, key)
        return p
