"""Bounded greedy Decode continuation; no Prefill or checkpoint reload in loop.

Per-step timing ends before comparison/hash/log output. Those costs and the
whole sequence wall time are reported separately, not called pure throughput.
"""
import hashlib
import time
import numpy as np


def run_sequence(token, cache, diagnostic_factory, *, reference=None,
                 steps=3, evidence=None, progress=lambda text: None,
                 clock=time.monotonic):
    if steps != 3:
        raise ValueError('This experiment is bounded to exactly three steps')
    if reference is not None and len(reference) != steps:
        raise ValueError('Three complete reference steps required')
    records = evidence if evidence is not None else []
    if records:
        raise ValueError('Evidence must be empty')
    cache_id = id(cache)
    if len(cache.keys) != 36 or len(cache.values) != 36:
        raise ValueError('Expected 36-layer cache')
    start_lengths = [a.shape[0] for a in cache.keys + cache.values]
    if start_lengths != [852] * 72 or int(token) != 1291:
        raise ValueError('Expected locked KV852/token1291 checkpoint')
    sequence_start = clock()
    for index in range(steps):
        row = dict(index=index, input_token=int(token), status='RUNNING')
        records.append(row)
        diagnostic = diagnostic_factory()  # existing one-step guard stays intact
        begin = clock()
        output_token, logits = diagnostic.decode(int(token), cache)
        ready = clock()
        row['decode_seconds'] = ready - begin
        row['output_token'] = int(output_token)
        post_begin = clock()
        if id(cache) != cache_id:
            raise RuntimeError('Cache identity changed')
        row['kv_lengths'] = [a.shape[0] for a in cache.keys + cache.values]
        if row['kv_lengths'] != [853 + index] * 72:
            raise RuntimeError('KV did not increment exactly once in every layer')
        if logits.shape != (151936,) or not np.isfinite(logits).all():
            raise RuntimeError('Invalid full logits')
        if any(not np.isfinite(a).all() for a in cache.keys + cache.values):
            raise RuntimeError('Non-finite KV')
        row['kv_sha256'] = [hashlib.sha256(a.tobytes()).hexdigest()
                            for a in cache.keys + cache.values]
        # Copy only logits, not another full KV. Retained outputs are serialized
        # by the board runner after the sequence and compared bit-for-bit here.
        row['logits'] = logits.copy()
        row['diagnostic'] = diagnostic.finalize()
        if reference is not None:
            expected = reference[index]
            other = expected['logits']
            row['bit_exact'] = (
                row['input_token'] == expected['input_token'] and
                row['output_token'] == expected['output_token'] and
                row['kv_lengths'] == expected['kv_lengths'] and
                row['kv_sha256'] == expected['kv_sha256'] and
                logits.dtype == other.dtype and logits.shape == other.shape and
                logits.tobytes() == other.tobytes())
            if not row['bit_exact']:
                row['status'] = 'FAIL_NUMERICAL'
                raise RuntimeError('Sequence mismatch at step ' + str(index))
        row['status'] = 'PASS_EXACT' if reference is not None else 'REFERENCE_RECORDED'
        row['postcheck_seconds'] = clock() - post_begin
        token = int(output_token)
        progress('DECODE_SEQUENCE_STEP %d token=%d decode_s=%.6f kv=%d' %
                 (index, token, row['decode_seconds'], 853 + index))
    return dict(steps=records, sequence_wall_seconds=clock()-sequence_start,
                decode_seconds_sum=sum(x['decode_seconds'] for x in records),
                timing_scope='Instrumented three-step diagnostic; postchecks interrupt delivery cadence',
                formal_throughput_pass=False)
