"""Bounded in-memory diagnostic intervals; no tensor copies or I/O in spans.

Exclusive attribution is per thread. Worker intervals must never be added to
the main-thread wall time. This tracer does not imply device completion.
"""
from contextlib import contextmanager
import threading
import time


class DecodeTrace:
    def __init__(self, clock=time.perf_counter_ns, max_events=20000):
        self.clock = clock
        self.max_events = max_events
        self.events = []
        self.lock = threading.Lock()
        self.local = threading.local()

    @contextmanager
    def span(self, name, **metadata):
        stack = getattr(self.local, 'stack', None)
        if stack is None:
            stack = self.local.stack = []
        with self.lock:
            if len(self.events) >= self.max_events:
                raise RuntimeError('Diagnostic event bound exceeded')
            event = dict(id=len(self.events), name=name,
                         thread=threading.get_ident(),
                         parent=stack[-1] if stack else None,
                         metadata=metadata, start_ns=self.clock(), end_ns=None,
                         failed=False)
            self.events.append(event)
        stack.append(event['id'])
        try:
            yield event
        except BaseException:
            event['failed'] = True
            raise
        finally:
            event['end_ns'] = self.clock()
            assert stack.pop() == event['id']

    def wrap(self, target, attribute, name=None):
        """Explicit context manager: restore even on failure; preserve returns."""
        @contextmanager
        def installed():
            original = getattr(target, attribute)
            # Restore the original instance dictionary, not a bound-method copy.
            owned = attribute in vars(target)
            prior = vars(target).get(attribute)
            def measured(*args, **kwargs):
                with self.span(name or attribute):
                    return original(*args, **kwargs)
            setattr(target, attribute, measured)
            try:
                yield
            finally:
                if owned:
                    setattr(target, attribute, prior)
                else:
                    delattr(target, attribute)
        return installed()

    def report(self):
        rows = [dict(x) for x in self.events]
        for row in rows:
            if row['end_ns'] is None:
                raise RuntimeError('Cannot report a live span')
            children = [x for x in rows if x['parent'] == row['id']]
            cursor = row['start_ns']
            child_ns = 0
            for child in sorted(children, key=lambda x: x['start_ns']):
                if (child['thread'] != row['thread'] or child['start_ns'] < cursor
                        or child['end_ns'] > row['end_ns']):
                    raise ValueError('Invalid nested interval')
                child_ns += child['end_ns'] - child['start_ns']
                cursor = child['end_ns']
            row['inclusive_ns'] = row['end_ns'] - row['start_ns']
            if row['inclusive_ns'] < 0:
                raise ValueError('Clock moved backwards')
            row['exclusive_ns'] = row['inclusive_ns'] - child_ns
        return dict(status='RECORDED', events=rows,
                    scope='Diagnostic host intervals; no device-cycle or numerical acceptance',
                    cross_thread_addition_allowed=False)


def cache_geometry(cache):
    """Shapes/identities only: do not scan/hash growing cache during timing."""
    if not cache.keys or len(cache.keys) != len(cache.values):
        raise ValueError('Invalid cache layer count')
    rows = []
    for key, value in zip(cache.keys, cache.values):
        if key.ndim != 3 or key.shape != value.shape:
            raise ValueError('Invalid cache geometry')
        rows.append(dict(key_shape=list(key.shape), value_shape=list(value.shape),
                         key_identity=id(key), value_identity=id(value)))
    if len({r['key_shape'][0] for r in rows}) != 1:
        raise ValueError('Inconsistent layer lengths')
    return dict(cache_identity=id(cache), layers=rows)
