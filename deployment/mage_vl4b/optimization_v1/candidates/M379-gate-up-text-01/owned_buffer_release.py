"""Future diagnostic release hook; no PYNQ imports or automatic retries.

Not installed in the frozen M352 package. Safety proof belongs to the caller.
"""
from threading import RLock


class OwnedBufferRelease:
    def __init__(self, release, safe, record):
        self._release, self._safe, self._record = release, safe, record
        self._lock = RLock()
        self.state = 'owned'

    def __call__(self):
        with self._lock:
            # PynqBuffer.__del__ may call freebuffer after explicit close.
            # No device reads or second backend call after proven release.
            if self.state == 'released':
                return
            if self.state != 'owned':
                raise RuntimeError('Release unresolved; retain owner, no backend retry')
            if self._safe() is not True:
                raise RuntimeError('Release safety not proven; retain owner')
            self.state = 'releasing'
            try:
                self._release()
            except BaseException:
                self.state = 'unresolved'
                raise
            self.state = 'released'
            self._record()
