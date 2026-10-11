"""Bounded Windows evidence I/O; no native-tool or board entry points."""
import os
import tempfile
import time
from pathlib import Path


def retry(operation, budget_s=5):
    deadline = time.monotonic() + budget_s
    while True:
        try:
            return operation()
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(min(.05, max(0, deadline - time.monotonic())))


def atomic(path, raw, immutable=False, budget_s=5):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if immutable and path.exists():
        if retry(path.read_bytes, budget_s) != raw:
            raise RuntimeError('Immutable result differs: ' + str(path))
        return
    fd, name = tempfile.mkstemp(prefix=path.name + '.m44108-', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        retry(lambda: os.replace(temporary, path), budget_s)
    finally:
        if temporary.exists():
            retry(temporary.unlink, budget_s)


def observation(reader, path):
    try:
        return retry(lambda: reader(path))
    except PermissionError as exc:
        return dict(path=str(path), observation='UNAVAILABLE_PERMISSION',
                    error=repr(exc), filename=exc.filename, winerror=getattr(exc, 'winerror', None))
