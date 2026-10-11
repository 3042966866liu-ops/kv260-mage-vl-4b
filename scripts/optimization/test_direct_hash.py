"""Portable algorithm/error tests; never proves Linux/fs direct-I/O support."""
import errno
from contextlib import ExitStack
import hashlib
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from direct_hash import Alignment, AlignedBuffer, DirectHashRejected, direct_sha256, hash_stream


class DirectHashTests(unittest.TestCase):
    def run_case(self, data, fault=None, **kwargs):
        requests = []
        with AlignedBuffer(8192, 4096) as b:
            def read(view, offset):
                requests.append((offset, len(view), b.address))
                if fault:
                    return fault(view, offset)
                chunk = data[offset:offset + len(view)]
                view[:] = b'\xa5' * len(view)  # Padding must not enter SHA.
                view[:len(chunk)] = chunk
                return len(chunk)
            r = hash_stream(len(data), b.view, read, 512, block=8192, **kwargs)
            self.assertEqual(r['sha256'], hashlib.sha256(data).hexdigest())
            self.assertEqual(r['bytes_hashed'], len(data))
            self.assertFalse(r['buffered_fallback'])
            self.assertTrue(all(off % 512 == count % 512 == addr % 4096 == 0 for off, count, addr in requests))
        self.assertTrue(b.closed)
        return r, requests

    def test_zero(self):
        r, requests = self.run_case(b'')
        self.assertEqual(requests, [])
        self.assertEqual(r['successful_reads'], 0)

    def test_alignment_boundaries_and_multiple_chunks(self):
        for size in (1, 511, 512, 513, 4095, 4096, 4097, 8191, 8192, 8193, 24579):
            with self.subTest(size=size):
                self.run_case(bytes((i * 73 + 19) % 256 for i in range(size)))

    def test_default_disabled_before_path_access(self):
        with self.assertRaisesRegex(DirectHashRejected, 'disabled'):
            direct_sha256('must-not-exist')

    def test_short_nonfinal(self):
        with self.assertRaisesRegex(DirectHashRejected, 'Short read'):
            self.run_case(b'x' * 16384, lambda v, off: len(v) - 512)

    def test_short_final(self):
        with self.assertRaisesRegex(DirectHashRejected, 'Short read'):
            self.run_case(b'x' * 4097, lambda v, off: 4096)

    def test_early_eof(self):
        with self.assertRaises(DirectHashRejected):
            self.run_case(b'x' * 4096, lambda v, off: 0)

    def test_count_larger_than_file_or_request(self):
        for count in (512, 9000):
            with self.subTest(count=count), self.assertRaises(DirectHashRejected):
                self.run_case(b'x', lambda v, off: count)

    def test_invalid_count(self):
        for count in (-1, True, 1.0, None):
            with self.subTest(count=count), self.assertRaises(DirectHashRejected):
                self.run_case(b'x', lambda v, off: count)

    def test_io_error_is_not_swallowed(self):
        def error(view, offset):
            raise OSError(errno.EIO, 'injected')
        with self.assertRaises(OSError) as raised:
            self.run_case(b'x', error)
        self.assertEqual(raised.exception.errno, errno.EIO)

    def test_eintr_recovers_same_offset(self):
        calls = []
        def read(view, offset):
            calls.append(offset)
            if len(calls) < 3:
                raise InterruptedError()
            view[:1] = b'x'
            return 1
        r, unused = self.run_case(b'x', read)
        self.assertEqual(calls, [0, 0, 0])
        self.assertEqual(r['interrupted_reads'], 2)

    def test_eintr_bounded(self):
        def error(view, offset):
            raise InterruptedError()
        with self.assertRaisesRegex(DirectHashRejected, 'retry bound'):
            self.run_case(b'x', error)

    def test_deadline_before_and_after_read(self):
        with self.assertRaises(TimeoutError):
            self.run_case(b'x', deadline=1, clock=lambda: 1)
        times = iter((0, 0, 2))
        with self.assertRaises(TimeoutError):
            self.run_case(b'x', deadline=1, clock=lambda: next(times))

    def test_geometry_rejected(self):
        for a in (0, 3, -1, 2 << 20):
            with self.subTest(a=a), self.assertRaises(DirectHashRejected):
                Alignment(a, a, 1).validate()
        with AlignedBuffer(8192, 4096) as b:
            for size, align, block in ((-1, 512, 8192), (1, 0, 8192), (1, 512, 8000), (1, 512, 16384)):
                with self.subTest(size=size, align=align, block=block), self.assertRaises(DirectHashRejected):
                    hash_stream(size, b.view, lambda v, o: 1, align, block=block)

    def test_buffer_close_on_failure(self):
        b = AlignedBuffer(8192, 4096)
        with self.assertRaises(ValueError):
            with b:
                raise ValueError('injected')
        self.assertTrue(b.closed)
        b.close()

    def wrapper_case(self, change=None, expected=None, error=None, mode=0o100600):
        # Explicit fake API test, not a simulated Linux capability PASS.
        original = SimpleNamespace(st_dev=1, st_ino=2, st_size=1, st_mtime_ns=3,
            st_ctime_ns=4, st_mode=mode, st_uid=0, st_gid=0, st_nlink=1)
        changed = SimpleNamespace(**vars(original))
        if change:
            setattr(changed, change, getattr(changed, change) + 1)
        closed = []
        with ExitStack() as stack:
            stack.enter_context(patch('direct_hash.require_linux'))
            stack.enter_context(patch('direct_hash.alignment_for_fd', return_value=Alignment(4096, 512, 1)))
            for name, value in (('O_DIRECT', 0x4000), ('O_CLOEXEC', 0x80000), ('O_NOFOLLOW', 0x20000)):
                stack.enter_context(patch('direct_hash.os.' + name, value, create=True))
            stack.enter_context(patch('direct_hash.os.stat', side_effect=[original, original]))
            stack.enter_context(patch('direct_hash.os.fstat', side_effect=[original, changed]))
            opened = stack.enter_context(patch('direct_hash.os.open', return_value=123))
            stack.enter_context(patch('direct_hash.os.close', side_effect=closed.append))
            def read(fd, vectors, offset):
                if error:
                    raise error
                vectors[0][:1] = b'x'
                return 1
            stack.enter_context(patch('direct_hash.os.preadv', side_effect=read, create=True))
            try:
                return direct_sha256('fake-fixture', enabled=True, expected_sha256=expected)
            finally:
                self.assertEqual(closed, [123] if opened.called else [])

    def test_fake_wrapper_full_sha_and_scope(self):
        r = self.wrapper_case(expected=hashlib.sha256(b'x').hexdigest())
        self.assertFalse(r['direct_mode_proven'])

    def test_fake_wrapper_file_identity_change(self):
        for field in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_mode', 'st_nlink'):
            with self.subTest(field=field), self.assertRaisesRegex(DirectHashRejected, 'identity changed'):
                self.wrapper_case(change=field)

    def test_fake_wrapper_bad_sha_and_io_error_close_fd(self):
        with self.assertRaisesRegex(DirectHashRejected, 'SHA differs'):
            self.wrapper_case(expected='0' * 64)
        with self.assertRaises(OSError):
            self.wrapper_case(error=OSError(errno.EIO, 'injected'))

    def test_fake_wrapper_symlink_rejected(self):
        with self.assertRaisesRegex(DirectHashRejected, 'non-symlink'):
            self.wrapper_case(mode=0o120777)


if __name__ == '__main__':
    unittest.main(verbosity=2)
