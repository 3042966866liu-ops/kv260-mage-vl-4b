"""Bounded request controller for the existing synchronous M120 language API.

No arithmetic/kernel change. One prefill per request, then genuine one-token
decode. A failed request discards its local cache; it never restarts prefill.
Backend exceptions propagate after trace finalization; DMA recovery is owned by
the verified board runner, not by this controller.
"""
import math
import numpy as np
from measurement import TokenTrace


class GenerationFailure(RuntimeError):
    def __init__(self, message, result):
        super().__init__(message)
        self.result = result


def validate_cache(cache, expected_length, *, layers=36, kv_heads=8, head_dim=128):
    if len(cache.keys) != layers or len(cache.values) != layers:
        raise ValueError('KV cache layer count mismatch')
    expected = (expected_length, kv_heads, head_dim)
    for layer, (key, value) in enumerate(zip(cache.keys, cache.values)):
        if key.shape != expected or value.shape != expected:
            raise ValueError(f'KV length/geometry mismatch at layer {layer}: {key.shape}/{value.shape}')
        if key.dtype != np.float32 or value.dtype != np.float32:
            raise ValueError(f'KV dtype mismatch at layer {layer}')


def generate(model, hidden, *, max_new_tokens, trace=None, eos_ids=(151645,), pad_ids=(),
             max_context=1024, layers=36, kv_heads=8, head_dim=128, vocab=151936,
             logical_calls_before=None, logical_calls_after=None,
             cpu_linear_fallback=None,
             first_token_timeout_s=3600, request_timeout_s=7200, on_token=None):
    """model.prefill/decode must return ONLY after output sync; runner audits this.

    Optional call-counter callbacks must both be provided. Timestamp collection
    starts before this function if raw decoding/preprocessing needs inclusion.
    This host controller cannot preempt a stuck DMA; underlying wait_transaction
    keeps its existing hard timeout and safe failure/diagnostic policy.
    """
    if (not isinstance(max_new_tokens, int) or isinstance(max_new_tokens, bool)
            or not 1 <= max_new_tokens <= 128):
        raise ValueError('max_new_tokens must be integer 1..128')
    if hidden.ndim != 2 or not 1 <= hidden.shape[0] <= max_context:
        raise ValueError('invalid prefill shape/context')
    if not np.isfinite(hidden).all():
        raise ValueError('non-finite prefill input')
    if (logical_calls_before is None) != (logical_calls_after is None):
        raise ValueError('both counter callbacks required')
    if any(not math.isfinite(x) or x <= 0 for x in (first_token_timeout_s, request_timeout_s)):
        raise ValueError('invalid watchdog configuration')
    if trace is None:
        trace = TokenTrace(eos_ids, pad_ids)
    elif trace.eos_ids != set(eos_ids) or trace.pad_ids != set(pad_ids):
        raise ValueError('trace special-token contract mismatch')
    count_before = logical_calls_before() if logical_calls_before else None
    cache = None
    valid_ids, kv_lengths = [], []
    prefill_count, decode_count = 0, 0
    reason, failure = 'length', None
    calls_after = None
    try:
        prefill_count = 1
        stage_start = trace.clock()
        try:
            token, logits, cache = model.prefill(hidden)
        finally:
            trace.stage('language_prefill', stage_start, trace.clock())
        validate_cache(cache, hidden.shape[0], layers=layers, kv_heads=kv_heads, head_dim=head_dim)
        kv_lengths.append(hidden.shape[0])
        for index in range(max_new_tokens):
            if index:
                previous_length = hidden.shape[0] + index - 1
                if previous_length >= max_context:
                    raise ValueError('context limit before next decode')
                validate_cache(cache, previous_length, layers=layers, kv_heads=kv_heads, head_dim=head_dim)
                decode_count += 1
                stage_start = trace.clock()
                try:
                    token, logits = model.decode(valid_ids[-1], cache)
                finally:
                    trace.stage(f'decode_{index}', stage_start, trace.clock())
                validate_cache(cache, previous_length + 1, layers=layers, kv_heads=kv_heads, head_dim=head_dim)
                kv_lengths.append(previous_length + 1)
            if (np.asarray(logits).shape != (vocab,) or not np.isfinite(logits).all()
                    or not isinstance(token, (int, np.integer)) or not 0 <= int(token) < vocab):
                raise ValueError('invalid token/logits')
            if int(np.argmax(logits)) != int(token):
                raise ValueError('reported token is not greedy argmax')
            trace.token_ready(int(token), synchronized=True)
            elapsed = (trace.last_ns - trace.start_ns) / 1e9
            if elapsed > request_timeout_s or (not valid_ids and elapsed > first_token_timeout_s):
                reason = 'timeout'
                raise TimeoutError('frozen request watchdog exceeded')
            if int(token) in eos_ids:
                reason = 'eos'
                break
            if int(token) in pad_ids:
                raise ValueError('unexpected generated padding token')
            valid_ids.append(int(token))
            if on_token:
                on_token(int(token))
        if logical_calls_after:
            calls_after = logical_calls_after()
            expected = math.ceil(hidden.shape[0] / 32) * 154 + 8 + decode_count * 162
            if calls_after - count_before != expected:
                raise ValueError('logical PL call count mismatch including EOS forward')
    except Exception as exc:
        failure = f'{type(exc).__name__}: {exc}'
        if reason != 'timeout':
            reason = 'error'
    # Account for small synchronous control/sampling gaps explicitly, not by
    # adding overlapping worker phase timers to the top-level total.
    end_ns = trace.clock()
    cursor = trace.start_ns
    for stage in sorted(list(trace.stages), key=lambda s: s['start_ns']):
        if stage['start_ns'] > cursor:
            trace.stage('control_sampling_or_gap', cursor, stage['start_ns'])
        cursor = max(cursor, stage['end_ns'])
    if end_ns > cursor:
        trace.stage('control_sampling_or_gap', cursor, end_ns)
    measured = trace.finish(reason, error=failure, cpu_linear_fallback=cpu_linear_fallback)
    result = {**measured, 'valid_token_ids': valid_ids, 'kv_lengths': kv_lengths,
              'prefill_count': prefill_count, 'decode_count': decode_count,
              'logical_calls_observed': None if calls_after is None else calls_after - count_before,
              'logical_calls_expected': math.ceil(hidden.shape[0] / 32) * 154 + 8 + decode_count * 162,
              'hardware_proof_verified': False,
              'hardware_proof_note': 'Counters alone are not proof; runner must bind Build, identity, physical calls and fallback evidence'}
    cache = None
    if measured['status'] != 'PASS':
        raise GenerationFailure(failure or '; '.join(measured['errors']), result)
    return result
