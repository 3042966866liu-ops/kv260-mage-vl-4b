import hashlib
import numpy as np

def tensor(value):
    x = np.ascontiguousarray(value)
    if not np.isfinite(x).all(): raise FloatingPointError('Nonfinite model output')
    return dict(shape=list(x.shape), dtype=str(x.dtype), bytes=x.nbytes,
                sha256=hashlib.sha256(x.tobytes()).hexdigest())

def check_call_contract(row, expected_macros):
    attempts = row['scale_attempts']
    if len(attempts) != 778: raise RuntimeError('Missing accepted per-T32/head scale records')
    if any(not a['attempted_shifts'] or a['selected_shift'] != a['attempted_shifts'][-1] for a in attempts):
        raise RuntimeError('Unconverged or inconsistent adaptive retry')
    language = sum(len(a['attempted_shifts']) - 1 for a in attempts if a['layer'] is not None)
    head = sum(len(a['attempted_shifts']) - 1 for a in attempts if a['layer'] is None)
    if row['logical_calls'] != 778 or row['host_calls'] != 778 + language + head or row['retry_count'] != language + head:
        raise RuntimeError('Video logical/physical/total retry contract differs')
    if not row['retry_launches'] == row['nonfinite_detections'] == language:
        raise RuntimeError('Language pipeline retry accounting differs')
    if row['logical_expected_macros'] != expected_macros: raise RuntimeError('Logical hardware macro count differs')
    row['language_retries'], row['head_retries'] = language, head

def validate_stream(events, decoder,expected_build):
    stages = [p['name'] for n,p in events if n == 'stage']
    groups = {n:[p for k,p in events if k == n] for n in ('complete','token','knife_observation')}
    if stages != ['preprocess','vision','prefill'] or any(len(v) != 1 for v in groups.values()):
        raise RuntimeError('Original stream stages/events incomplete')
    final, token, observation = (groups[n][0] for n in ('complete','token','knife_observation'))
    proof = final.get('proof', {})
    if not (final.get('status') == 'PASS' and final.get('prompt_tokens') == 159 and final.get('generated_tokens') == 1
            and final.get('decode_calls') == 0 and final.get('selected_frame_indices') == [3]
            and token.get('token_id') == 15 and token.get('text') == '0' and token.get('knife_verdict') == 'ABSENT'
            and observation.get('verdict') == 'ABSENT' and observation.get('selected_frame_indices') == [3]
            and str(proof.get('build_id','')).lower() == expected_build.lower()
            and proof.get('pl_logical_chain_calls') == proof.get('expected_pl_logical_chain_calls') == 778
            and proof.get('language_cpu_linear_fallback') is False and proof.get('decode_calls') == 0
            and proof.get('pl_expected_macros', 0) > 0):
        raise RuntimeError('Frozen M277 functional contract failed')
    if not (decoder.get('cache_entries') == 26 and decoder.get('cache_bytes') == 66699264
            and decoder.get('cache_misses') == 26 and decoder.get('cache_within_budget') is True):
        raise RuntimeError('Original bounded vision cache contract differs')
    # Timing is diagnostic only. Original constrained decision fields are exact.
    semantic = dict(token=token, observation=observation, proof=proof, prompt_tokens=159,
                    selected_frame_indices=[3], generated_tokens=1, decode_calls=0)
    if not token['knife_score'] == observation['knife_score'] == final['knife_score']:
        raise RuntimeError('Inconsistent constrained decision score')
    return semantic
