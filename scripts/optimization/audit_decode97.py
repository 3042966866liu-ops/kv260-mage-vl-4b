"""Read-only derivation from frozen SYS02; never invent absent phase timings."""
import json
from collections import defaultdict
from pathlib import Path
from measurement import sha256, write_json

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'


def derive(board):
    g = board['request']['generation']
    assert g['prefill_count'] == g['decode_count'] == 1
    assert g['kv_lengths'] == [852, 853]
    stages = [x for x in g['top_level_stages'] if x['name'] == 'decode_1']
    assert len(stages) == 1
    stage = stages[0]
    events = g['raw_token_events']
    assert len(events) == 2
    elapsed = (stage['end_ns'] - stage['start_ns']) / 1e9
    gap = (events[1]['ready_ns'] - events[0]['ready_ns']) / 1e9
    attempts = board['board_evidence']['scale_attempts']
    assert len(attempts) == 4328
    physical = sum(len(x['attempted_shifts']) for x in attempts)
    assert physical == len(board['transactions']) == 4333
    # Sequential logical attempt stream expanded to physical transactions.
    cursor = 0
    for item in attempts:
        for _ in item['attempted_shifts']:
            tx = board['transactions'][cursor]
            for key in ('chain_index', 'layer', 'family'):
                assert tx['current'][key] == item[key]
            assert tx['ap_return'] == 0x4D395832
            cursor += 1
    tail = attempts[-162:]
    assert [x['chain_index'] for x in tail[:154]] == list(range(154))
    assert [x['chain_index'] for x in tail[154:]] == list(range(8))
    count = sum(len(x['attempted_shifts']) for x in tail)
    waits = defaultdict(float)
    for tx in board['transactions'][-count:]:
        waits[tx['current']['family']] += tx['elapsed_ns'] / 1e9
    return dict(status='PARTIAL_ATTRIBUTION', decode_call_s=elapsed,
        token_ready_interval_s=gap, outside_decode_call_s=gap-elapsed,
        kv_lengths=g['kv_lengths'], logical_calls=162, physical_calls=count,
        retries=count-162, observed_wait_s=sum(waits.values()),
        observed_wait_by_family_s=dict(waits),
        non_wait_unattributed_s=elapsed-sum(waits.values()),
        wait_scope='Host wait_transaction duration, not a hardware cycle counter; overlaps possible with worker preparation',
        missing=['decode-only read/copy/sync/pack/parse/PS timings',
                 'real decode input tensors and same-quant comparison',
                 'saved prefill checkpoint for isolated reproducibility'],
        numerical_acceptance=False, optimization_speedup_proven=False)


if __name__ == '__main__':
    source = BASE/'gates/G01-SYS-development/attempt_02/board_result.json'
    result = derive(json.loads(source.read_text()))
    result['source_sha256'] = sha256(source)
    out = BASE/'runs/OP01-decode97-audit-v1/result.json'
    if out.exists():
        raise RuntimeError('Immutable audit exists')
    write_json(out, result)
    print(json.dumps(result))
