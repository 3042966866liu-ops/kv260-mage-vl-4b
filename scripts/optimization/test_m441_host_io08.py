"""Actual Windows sharing-lock checks; no tools, model or FPGA."""
import ctypes
import tempfile
import threading
import time
from pathlib import Path
from m441_host_io08 import atomic, observation


def main():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                                 ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
    kernel.CreateFileW.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.restype = ctypes.c_int
    checks = {}
    with tempfile.TemporaryDirectory(prefix='m44108-') as directory:
        path = Path(directory) / 'progress.json'
        atomic(path, b'old')
        handle = kernel.CreateFileW(str(path), 0x80000000, 1, None, 3, 0, None)
        assert handle != ctypes.c_void_p(-1).value
        try:
            try:
                atomic(path, b'rejected', budget_s=.1)
            except PermissionError:
                checks['real_lock_timeout_preserves_original'] = path.read_bytes() == b'old'
            else:
                raise AssertionError('Locked replace accepted')
        finally:
            assert kernel.CloseHandle(handle)
        handle = kernel.CreateFileW(str(path), 0x80000000, 1, None, 3, 0, None)
        assert handle != ctypes.c_void_p(-1).value
        event = threading.Event()
        def release():
            time.sleep(.15)
            assert kernel.CloseHandle(handle)
            event.set()
        thread = threading.Thread(target=release)
        thread.start()
        atomic(path, b'new', budget_s=2)
        thread.join()
        checks['real_lock_release_retry'] = event.is_set() and path.read_bytes() == b'new'
        atomic(path, b'new', immutable=True)
        checks['same_immutable_accepted'] = True
        try:
            atomic(path, b'changed', immutable=True)
        except RuntimeError:
            checks['different_immutable_rejected'] = path.read_bytes() == b'new'
        else:
            raise AssertionError('Immutable overwrite accepted')
        checks['temporary_cleanup'] = list(Path(directory).iterdir()) == [path]
        attempts = []
        def transient(p):
            attempts.append(1)
            if len(attempts) == 1:
                raise PermissionError(13, 'explicit injected read denial', str(p))
            return {'ok': True}
        checks['read_retry_explicit_injection'] = observation(transient, path) == {'ok': True}
        def wrong(p):
            raise ValueError('real parse error not swallowed')
        try:
            observation(wrong, path)
        except ValueError:
            checks['non_permission_failure_propagates'] = True
        else:
            raise AssertionError('Parse error hidden')
    assert len(checks) == 7 and all(checks.values())
    return dict(status='PASS_M441_HOST_IO_COMPONENT08', checks=checks,
                exact_original_failure_operation_proven=False, native_tools_started=0, board=False)


if __name__ == '__main__':
    import json
    print(json.dumps(main(), indent=2))
