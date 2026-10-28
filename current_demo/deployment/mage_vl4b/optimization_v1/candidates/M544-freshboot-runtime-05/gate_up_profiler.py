"""Instance-scoped RAM/NumPy vs RAM/C GateUp; no DMA or completion API changes.

Install after owner allocation and before timed requests. Call begin/end only
after the existing request idle/checkpoint checks. Both A and B copy into ordinary RAM and reserve two
ordinary-RAM scratch arrays, outside timing, to keep their memory budgets equal.
The LM head follows _execute(), so this first experiment changes language family
parsing only. Head, vision, weights, retries and DMA ownership remain unchanged.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import textwrap
import threading
import time
import types

import numpy as np
from gate_up_native import GateUpNative


def source_sha(function):
    return hashlib.sha256(textwrap.dedent(inspect.getsource(function)).encode()).hexdigest()


class ParserAB:
    def __init__(self, runtime, expected_parse_sha, expected_resolve_sha, limit=2048, native_library=None):
        self.runtime = runtime
        self.original_parse = runtime._parse_buffer
        self.original_resolve = runtime._resolve_pending
        if source_sha(self.original_parse) != expected_parse_sha:
            raise RuntimeError("Unexpected original parse method")
        if source_sha(self.original_resolve) != expected_resolve_sha:
            raise RuntimeError("Unexpected original pending/retry method")
        self.native_parser = GateUpNative(native_library)
        self.buffers = (runtime.output_buffer, runtime.output_buffer_alt)
        if any(b is None or b.dtype != np.uint8 or not b.flags.c_contiguous for b in self.buffers):
            raise RuntimeError("Two original contiguous uint8 DMA outputs required")
        if np.may_share_memory(*self.buffers):
            raise RuntimeError("DMA outputs must be independent")
        self.scratch = tuple(np.empty(b.nbytes, dtype=np.uint8) for b in self.buffers)
        self.slot_locks = (threading.Lock(), threading.Lock())
        self.state_lock = threading.Lock()
        self.active = False
        self.installed = False
        self.owner_thread = threading.get_ident()
        self.limit = limit
        self.busy = 0
        self.rows, self.wait_rows = [], []
        self.previous = {n: (n in runtime.__dict__, runtime.__dict__.get(n))
                         for n in ("_parse_buffer", "_resolve_pending")}
        # Insert only an observer around the original Future.result(). The retry
        # body, exception propagation, completion, and buffer reuse stay intact.
        original = self.original_resolve.__func__
        tree = ast.parse(textwrap.dedent(inspect.getsource(original)))
        before = copy.deepcopy(tree)
        hits = []
        class Observe(ast.NodeTransformer):
            def visit_Call(self, node):
                self.generic_visit(node)
                if (isinstance(node.func, ast.Attribute) and node.func.attr == "result"
                        and isinstance(node.func.value, ast.Attribute)
                        and node.func.value.attr == "future"
                        and isinstance(node.func.value.value, ast.Name)
                        and node.func.value.value.id == "pending"):
                    if node.args or node.keywords:
                        raise RuntimeError("Unexpected Future.result arguments")
                    hits.append(node)
                    return ast.copy_location(ast.Call(
                        func=ast.Attribute(ast.Name("_parser_ab_observer", ast.Load()),
                                           "future_result", ast.Load()),
                        args=[ast.Name("chain", ast.Load()), node.func.value], keywords=[]), node)
                return node
        observed = Observe().visit(tree)
        if len(hits) != 1:
            raise RuntimeError("Original Future.result observer site differs")
        stripped = copy.deepcopy(observed)
        class Strip(ast.NodeTransformer):
            def visit_Call(self, node):
                if (isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "_parser_ab_observer"):
                    return copy.deepcopy(hits[0])
                return self.generic_visit(node)
        if ast.dump(Strip().visit(stripped)) != ast.dump(before):
            raise RuntimeError("Pending/retry AST changed beyond observer")
        namespace = dict(original.__globals__)
        namespace["_parser_ab_observer"] = self
        exec(compile(ast.fix_missing_locations(observed), "<parser_ab_pending>", "exec"), namespace)
        self.resolve_hook = types.MethodType(namespace[original.__name__], runtime)
        self.parse_hook = types.MethodType(self.parse_buffer, runtime)
        self.proof = dict(original_parse_sha256=expected_parse_sha,
                          original_resolve_sha256=expected_resolve_sha,
                          retry_AST_unchanged_except_future_timer=True,
                          ordinary_RAM_reserved_bytes=sum(b.nbytes for b in self.scratch),
                          DMA_ownership_and_reuse_unchanged=True,
                          scope="both_arms_RAM_copy_GateUp_C_only_head_and_visual_unchanged",
                          both_arms_same_ordinary_RAM_copy=True, C_only_family="gate_up")

    def install(self):
        if self.installed or self.active:
            raise RuntimeError("Already installed/active")
        self.runtime._parse_buffer = self.parse_hook
        self.runtime._resolve_pending = self.resolve_hook
        self.installed = True

    def begin(self, variant):
        if threading.get_ident() != self.owner_thread or variant not in ("A", "B"):
            raise RuntimeError("Main-thread A/B boundary required")
        with self.state_lock:
            if not self.installed or self.active or self.busy:
                raise RuntimeError("Parser not idle at request boundary")
            self.variant = variant
            self.rows, self.wait_rows = [], []
            self.active = True

    def parse_buffer(self, runtime, chain, output_buffer, targets, token_start, token_count, shift):
        with self.state_lock:
            if not self.active:
                return self.original_parse(chain, output_buffer, targets, token_start, token_count, shift)
            if len(self.rows) + self.busy >= self.limit:
                raise RuntimeError("Bounded parser observation budget exhausted")
            self.busy += 1
            variant = self.variant
        slot = next((i for i, b in enumerate(self.buffers) if output_buffer is b), None)
        if slot is None:
            with self.state_lock: self.busy -= 1
            raise RuntimeError("Unknown DMA output owner")
        if not self.slot_locks[slot].acquire(blocking=False):
            with self.state_lock: self.busy -= 1
            raise RuntimeError("Same output still in use; refuse scratch reuse")
        started = time.perf_counter()
        began = time.perf_counter_ns()
        row = dict(variant=variant, slot=slot, family=runtime._family_key(chain),
                   token_start=token_start, token_count=token_count, shift=shift,
                   effective_bytes=int(chain["output_bytes"]), copy_ns=0, parse_ns=0, ok=False)
        try:
            size = row["effective_bytes"]
            raw = memoryview(output_buffer).cast("B")
            if not 0 < size <= len(raw):
                raise RuntimeError("Output exceeds original DMA capacity")
            payload = raw[:size]
            if variant in ("A", "B"):
                tick = time.perf_counter_ns()
                scratch = self.scratch[slot][:size]
                np.copyto(scratch, np.frombuffer(payload, dtype=np.uint8), casting="no")
                payload = memoryview(scratch)
                row["copy_ns"] = time.perf_counter_ns() - tick
            tick = time.perf_counter_ns()
            use_native = variant == "B" and chain.get("family") == "gate_up"
            row["implementation"] = "C_gate_up" if use_native else "original_numpy"
            parser = self.native_parser.parse if use_native else runtime._parse_into_and_check
            finite = parser(chain, payload, targets, token_start, token_count, shift)
            row["parse_ns"] = time.perf_counter_ns() - tick
            row.update(ok=True, finite=bool(finite))
            runtime._record_phase(chain, "parse", started)
            return finite
        finally:
            row["total_ns"] = time.perf_counter_ns() - began
            with self.state_lock:
                self.rows.append(row)
                self.busy -= 1
            self.slot_locks[slot].release()

    def future_result(self, chain, future):
        if not self.active:
            return future.result()
        if threading.get_ident() != self.owner_thread:
            raise RuntimeError("Pending resolver must remain on original main thread")
        tick = time.perf_counter_ns()
        row = dict(family=self.runtime._family_key(chain), ok=False)
        try:
            result = future.result()
            row["ok"] = True
            return result
        finally:
            row["wait_ns"] = time.perf_counter_ns() - tick
            self.wait_rows.append(row)

    def end(self):
        if threading.get_ident() != self.owner_thread:
            raise RuntimeError("Main-thread boundary required")
        with self.state_lock:
            if not self.active or self.busy:
                raise RuntimeError("Parser must finish before request boundary")
            self.active = False
        rows = list(self.rows)
        return dict(variant=self.variant, proof=self.proof, calls=len(rows),
                    effective_bytes=sum(r["effective_bytes"] for r in rows),
                    copy_s=sum(r["copy_ns"] for r in rows)/1e9,
                    parse_s=sum(r["parse_ns"] for r in rows)/1e9,
                    copy_plus_parse_s=sum(r["copy_ns"]+r["parse_ns"] for r in rows)/1e9,
                    parser_total_s=sum(r["total_ns"] for r in rows)/1e9,
                    main_future_wait_s=sum(r["wait_ns"] for r in self.wait_rows)/1e9,
                    successful=all(r["ok"] for r in rows) and all(r["ok"] for r in self.wait_rows),
                    phase_sums_overlap_device_execution=True,
                    rows=rows, waits=list(self.wait_rows))

    def restore(self):
        if self.active or self.busy:
            raise RuntimeError("Do not restore while parser is active")
        if self.installed:
            for name, hook in (("_parse_buffer", self.parse_hook), ("_resolve_pending", self.resolve_hook)):
                if self.runtime.__dict__.get(name) is not hook:
                    raise RuntimeError("Another owner changed parser hooks")
            for name, (owned, value) in self.previous.items():
                if owned: setattr(self.runtime, name, value)
                else: delattr(self.runtime, name)
            self.installed = False
