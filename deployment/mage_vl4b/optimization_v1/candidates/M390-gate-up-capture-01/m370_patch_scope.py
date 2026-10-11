"""Isolated diagnostic patch lifetimes; no service/board installation.

Retain all hooks on unproven completion. Restore inherited attributes by
deleting instance overrides, so restoring a bound method creates no self cycle.
"""


class PatchScope:
    def __init__(self):
        self.entries = []

    def patch(self, owner, name, replacement):
        original = getattr(owner, name)
        namespace = vars(owner)
        self.entries.append((owner, name, name in namespace, namespace.get(name)))
        setattr(owner, name, replacement)
        return original

    def restore_owner(self, owner, *, completion_proven=False, release_proven=False):
        if completion_proven is not True or release_proven is not True:
            raise RuntimeError('Retain patches and owner until completion and release proven')
        selected = [e for e in self.entries if e[0] is owner]
        for obj, name, present, value in reversed(selected):
            if present:
                setattr(obj, name, value)
            else:
                delattr(obj, name)
        self.entries = [e for e in self.entries if e[0] is not owner]
        return len(selected)

    def restore_all(self, *, completion_proven=False, release_proven=False):
        if completion_proven is not True or release_proven is not True:
            raise RuntimeError('Retain patches and owners until safe exit proven')
        for obj, name, present, value in reversed(self.entries):
            if present:
                setattr(obj, name, value)
            else:
                delattr(obj, name)
        self.entries.clear()
