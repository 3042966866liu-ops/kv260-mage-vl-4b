"""Actual file/hook tests; Windows counters explicit fake, Linux counters/probe real."""
import copy
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import m435_io_observer as obs


class ObserverTests(unittest.TestCase):
    def setUp(self):
        task_temp = Path(__file__).resolve().parents[2] / 'tmp' if os.name != 'posix' else Path('/tmp')
        self.temp = tempfile.TemporaryDirectory(prefix='m435-test-', dir=task_temp)
        self.root = Path(self.temp.name)
        self.weight = self.root / 'weight.bin'
        self.weight.write_bytes(bytes(range(256)) * 32)
        self.store = SimpleNamespace(decode=lambda n: n)
        self.result = {}
        self.open_before, self.decode_before = Path.open, self.store.decode
        self.counter = patch.object(obs, 'counters', lambda: dict(io={'read_bytes': 0, 'rchar': 0}, major=0)) if os.name != 'posix' else None
        if self.counter:
            self.counter.start()
        self.identity_adapter = None
        if os.name != 'posix':
            original_identity = obs.identity
            # Windows path/fd creation-time reporting differs. Linux retains all seven fields.
            self.identity_adapter = patch.object(obs, 'identity', lambda s: original_identity(s)[:4] + original_identity(s)[5:])
            self.identity_adapter.start()

    def tearDown(self):
        self.assertIs(Path.open, self.open_before)
        self.assertIs(self.store.decode, self.decode_before)
        if self.counter:
            self.counter.stop()
        if self.identity_adapter:
            self.identity_adapter.stop()
        self.temp.cleanup()

    def make(self, group='visual'):
        o = obs.IOObserver({self.weight: group}, self.store, self.result)
        o.phase, o.request = ('vision' if group == 'visual' else 'prefill'), 1
        return o

    def test_actual_read_bytes_seek_and_restore(self):
        with self.make() as o:
            with self.weight.open('rb') as f:
                f.seek(13)
                self.assertEqual(f.read(123), (bytes(range(256)) * 32)[13:136])
            self.assertEqual(self.store.decode('qkv'), 'qkv')
        self.assertEqual(o.reads[0]['offset'], 13)
        self.assertEqual(o.reads[0]['returned_bytes'], 123)
        self.assertEqual(len(o.decodes), 1)
        self.assertTrue(self.result['io_observer_hooks_restored'])

    def test_actual_unbuffered_language(self):
        with self.make('language') as o:
            with self.weight.open('rb', buffering=0) as f:
                self.assertEqual(f.read(16), bytes(range(16)))
        self.assertEqual(o.reads[0]['group'], 'language')

    def test_short_read_rejected_restored(self):
        with self.assertRaisesRegex(RuntimeError, 'short/changed'):
            with self.make() as o:
                with self.weight.open('rb') as f:
                    f.read(9000)
        self.assertEqual(o.reads[0]['returned_bytes'], 8192)

    def test_changed_path_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'identity changed'):
            with self.make():
                with self.open_before(self.weight, 'wb') as f:
                    f.write(b'x')
                self.weight.open('rb')

    def test_changed_open_file_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'short/changed'):
            with self.make():
                with self.weight.open('rb', buffering=0) as f:
                    with self.open_before(self.weight, 'r+b', buffering=0) as other:
                        other.write(b'z')
                    f.read(1)

    def test_wrong_phase_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'phase'):
            with self.make() as o:
                o.phase = 'none'
                with self.weight.open('rb') as f:
                    f.read(1)

    def test_wrong_group_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'contract/phase'):
            with self.make() as o:
                o.phase = 'prefill'
                with self.weight.open('rb') as f:
                    f.read(1)

    def test_thread_identity_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'concurrent'):
            with self.make() as o:
                o.thread = -1
                with self.weight.open('rb') as f:
                    f.read(1)

    def test_mutating_mode_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'read-only'):
            with self.make():
                self.weight.open('wb')

    def test_other_file_passthrough(self):
        p = self.root / 'other'
        with self.make() as o:
            p.write_bytes(b'fixture')
            self.assertEqual(p.read_bytes(), b'fixture')
        self.assertEqual(o.reads, [])

    def test_decode_exception_restores(self):
        def fail(n):
            raise ValueError('actual delegate error')
        self.store.decode = fail
        self.decode_before = fail
        with self.assertRaises(ValueError):
            with self.make():
                self.store.decode('q')

    def test_nested_rejected(self):
        with self.make() as o:
            with self.assertRaisesRegex(RuntimeError, 'Nested'):
                o.__enter__()

    def test_residency_diff_exact(self):
        import base64, hashlib
        def row(bits):
            return dict(identity=[1], pages=8, page_bytes=4096, permission_proven=True,
                        bits_b64=base64.b64encode(bits).decode(), bits_sha256=hashlib.sha256(bits).hexdigest(),
                        resident_pages=bin(bits[0]).count('1'))
        a, b = row(b'\x03'), row(b'\x06')
        self.assertEqual(obs.residency_change(a, b)['gained_pages'], 1)
        self.assertEqual(obs.residency_change(a, b)['lost_pages'], 1)
        for k, v in [('identity', [2]), ('permission_proven', False), ('bits_sha256', '0' * 64), ('bits_b64', '')]:
            bad = dict(b, **{k: v})
            with self.assertRaises(RuntimeError):
                obs.residency_change(a, bad)

    @unittest.skipUnless(os.name == 'posix', 'Linux-only real mincore')
    def test_real_linux_probe_fd_lifecycle(self):
        before = len(list(Path('/proc/self/fd').iterdir()))
        proof = obs.linux_probe_fixture(self.root)
        self.assertEqual(len(list(Path('/proc/self/fd').iterdir())), before)
        self.assertTrue(proof['fixture_removed'])
        self.assertTrue(proof['first_page_observed'])

    @unittest.skipUnless(os.name == 'posix', 'Linux-only real mincore')
    def test_real_linux_snapshot_and_hardlink_rejection(self):
        row = obs.residency(self.weight)
        self.assertTrue(row['permission_proven'])
        self.assertEqual(row['pages'], 2)
        os.link(self.weight, self.root / 'hardlink')
        with self.assertRaisesRegex(RuntimeError, 'ownership/type'):
            obs.residency(self.weight)


if __name__ == '__main__':
    unittest.main(verbosity=2)
