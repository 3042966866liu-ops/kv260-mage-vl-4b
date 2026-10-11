"""Default-disabled observation of pinned M238/M236 result waits.

No new executor, tensor ownership, parser or hardware action. Condition.wait
wall time includes wake-up/scheduling; it is not a pure CPU stall-cycle count.
"""
import ast
from concurrent.futures import Future
from contextlib import contextmanager
import copy
import hashlib
import inspect
import threading
import textwrap
import time

PINNED = {
    'language_family_many': '6bcb23fb211b1d411802380799d0a1998d081579811cc8a72635ad01053407f7',
    '_resolve_pending': '7798fae8ad951d777d6d1a46cf89650517f4a7a35d01b7c2d1376f401ff00e55',
}


class FutureWaitObserver:
    def __init__(self, trace, *, max_results=4096):
        if type(max_results) is not int or not 0 < max_results <= 4096:
            raise ValueError('Invalid result-record bound')
        future_source = textwrap.dedent(inspect.getsource(Future.result)).strip().replace('\r\n', '\n')
        waits = [n for n in ast.walk(ast.parse(future_source)) if isinstance(n, ast.Call)
                 and ast.unparse(n.func) == 'self._condition.wait']
        if Future.result.__module__ != 'concurrent.futures._base' or len(waits) != 1:
            raise RuntimeError('Future.result condition-wait path cannot be observed')
        self.future_result_source_sha256 = hashlib.sha256(future_source.encode()).hexdigest()
        self.trace, self.max_results = trace, max_results
        self.owner_thread = threading.get_ident()
        self.records = []
        self.active = set()

    def wait(self, future, *, kind, chain, token_start):
        if threading.get_ident() != self.owner_thread:
            raise RuntimeError('Result observation requires one foreground owner')
        if type(future) is not Future or future.result.__func__ is not Future.result:
            raise RuntimeError('Unreviewed Future.result implementation')
        if kind not in ('pack', 'parse') or len(self.records) >= self.max_results:
            raise RuntimeError('Unknown wait or record bound exceeded')
        condition = future._condition
        if not isinstance(condition, threading.Condition):
            raise RuntimeError('Unsupported Future condition')
        if id(condition) in self.active:
            raise RuntimeError('Concurrent/reentrant observation of one Future')
        caller = threading.get_ident()
        original = condition.wait
        owned = 'wait' in vars(condition)
        prior = vars(condition).get('wait')
        row = dict(kind=kind, layer=chain.get('layer'), family=chain.get('family', 'lm_head'),
                   chain_index=chain['chain_index'], token_start=int(token_start),
                   ready_before=future.done(), condition_wait_calls=0,
                   condition_wait_ns=0, result_wall_ns=None, exception=None)
        self.records.append(row)

        def measured_condition(*args, **kwargs):
            if threading.get_ident() != caller:
                return original(*args, **kwargs)
            with self.trace.span('future_condition_wait', kind=kind,
                                 chain_index=chain['chain_index'], token_start=int(token_start)):
                started = time.perf_counter_ns()
                row['condition_wait_calls'] += 1
                try:
                    return original(*args, **kwargs)
                finally:
                    row['condition_wait_ns'] += time.perf_counter_ns() - started

        self.active.add(id(condition))
        try:
            condition.wait = measured_condition
            with self.trace.span(kind + '_future_result', **{k:row[k] for k in
                    ('layer', 'family', 'chain_index', 'token_start', 'ready_before')}):
                started = time.perf_counter_ns()
                try:
                    # Keep the original timeout=None and exception semantics.
                    return future.result()
                except BaseException as exc:
                    row['exception'] = type(exc).__name__
                    raise
                finally:
                    row['result_wall_ns'] = time.perf_counter_ns() - started
        finally:
            if owned:
                condition.wait = prior
            elif 'wait' in vars(condition):
                del condition.wait
            self.active.remove(id(condition))

    def summary(self):
        if self.active or any(x['result_wall_ns'] is None for x in self.records):
            raise RuntimeError('Cannot serialize active result observation')
        return {kind: dict(calls=len(rows), ready_before=sum(x['ready_before'] for x in rows),
                    calls_with_condition_wait=sum(x['condition_wait_calls'] > 0 for x in rows),
                    condition_wait_calls=sum(x['condition_wait_calls'] for x in rows),
                    result_wall_s=sum(x['result_wall_ns'] for x in rows)/1e9,
                    condition_wait_s=sum(x['condition_wait_ns'] for x in rows)/1e9,
                    exceptions=sum(x['exception'] is not None for x in rows))
                for kind in ('pack', 'parse')
                for rows in [[x for x in self.records if x['kind'] == kind]]}


def instrument(original, name, observer, *, source=None):
    function = getattr(original, '__func__', original)
    source = textwrap.dedent(source or inspect.getsource(function)).strip().replace('\r\n', '\n')
    if name not in PINNED or hashlib.sha256(source.encode()).hexdigest() != PINNED[name]:
        raise RuntimeError('Frozen result-call source identity differs')
    tree = ast.parse(source)
    before = ast.dump(tree, include_attributes=False)
    target = 'pack_future.result' if name == 'language_family_many' else 'pending.future.result'
    kind = 'pack' if name == 'language_family_many' else 'parse'

    class ReplaceResult(ast.NodeTransformer):
        count = 0
        def visit_Call(self, node):
            self.generic_visit(node)
            if ast.unparse(node.func) != target:
                return node
            if node.args or node.keywords:
                raise RuntimeError('Unexpected timeout/arguments in pinned call')
            self.count += 1
            token = 'token_start' if kind == 'pack' else 'pending.token_start'
            future = 'pack_future' if kind == 'pack' else 'pending.future'
            replacement = ast.parse(f'_m372_wait_observer.wait({future}, kind={kind!r}, chain=chain, token_start={token})').body[0].value
            return ast.copy_location(replacement, node)

    rewrite = ReplaceResult()
    tree = rewrite.visit(tree)
    if rewrite.count != 1:
        raise RuntimeError('Expected exactly one original result call')
    # Same-interpreter AST check only; cross-version identity is normalized SHA.
    restored = copy.deepcopy(tree)
    class Undo(ast.NodeTransformer):
        def visit_Call(self, node):
            if ast.unparse(node.func) == '_m372_wait_observer.wait':
                return ast.copy_location(ast.parse(target + '()').body[0].value, node)
            return self.generic_visit(node)
    if ast.dump(Undo().visit(restored), include_attributes=False) != before:
        raise RuntimeError('Observation changed other original statements')
    ast.fix_missing_locations(tree)
    namespace = dict(function.__globals__)
    namespace['_m372_wait_observer'] = observer
    exec(compile(tree, '<m372-pinned-result-observation>', 'exec'), namespace)
    return namespace[name]


@contextmanager
def observe_runtime(runtime, trace, *, enabled=False):
    if not enabled:
        raise ValueError('Future wait observation disabled by default')
    observer = FutureWaitObserver(trace)
    names = ('language_family_many', '_resolve_pending')
    # Validate both methods before changing any instance binding.
    replacements = {name:instrument(getattr(runtime, name), name, observer) for name in names}
    saved = [(name, name in vars(runtime), vars(runtime).get(name)) for name in names]
    try:
        for name, replacement in replacements.items():
            setattr(runtime, name, replacement.__get__(runtime, type(runtime)))
        yield observer
    finally:
        for name, owned, prior in reversed(saved):
            if owned:
                setattr(runtime, name, prior)
            elif name in vars(runtime):
                delattr(runtime, name)
