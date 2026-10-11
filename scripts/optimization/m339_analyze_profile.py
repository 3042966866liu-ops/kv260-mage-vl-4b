"""Exclusive host attribution for one instrumented159-token request, never a speed claim."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'deployment/mage_vl4b/optimization_v1/runs/M339-profile-04-results'


def main():
    path = RUN / 'prefill_trace.json'
    trace = json.loads(path.read_text(encoding='utf-8'))
    result = json.loads((RUN / 'result.json').read_text(encoding='utf-8'))
    if not result['status'].startswith('PASS') or trace['status'] != 'RECORDED':
        raise RuntimeError('Cannot summarize incomplete profile as passing measurement')
    rows = trace['trace']['events']
    roots = [row for row in rows if row['name'] == 'prefill_call']
    if len(roots) != 1: raise RuntimeError('Expected one Prefill root')
    root = roots[0]
    thread = root['thread']
    main_rows = [row for row in rows if row['thread'] == thread]
    if any(row['exclusive_ns'] < 0 for row in rows): raise RuntimeError('Negative attribution')
    closure = sum(row['exclusive_ns'] for row in main_rows) - root['inclusive_ns']
    if closure: raise RuntimeError('Main-thread tree does not close')
    exclusive, count, workers = defaultdict(int), defaultdict(int), defaultdict(int)
    for row in rows:
        if row['thread'] == thread:
            exclusive[row['name']] += row['exclusive_ns']
            count[row['name']] += 1
        else:
            workers[row['name']] += row['exclusive_ns']
    io = defaultdict(int)
    for row in rows:
        if row['name'] == 'weight_file_read':
            for key, value in row['metadata'].get('process_io_delta', {}).items(): io[key] += value
    families = [dict(**row['metadata'], inclusive_ms=row['inclusive_ns']/1e6,
                     self_ms=row['exclusive_ns']/1e6) for row in rows if row['name']=='language_family']
    summary = dict(status='MEASURED_INSTRUMENTED_PREFILL_ONLY', trace_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        build_id='0x4D395832', prompt_tokens=159, numerical_scope='M277 constrained decision and FPGA proof; no full-logits A/B',
        prefill_seconds=root['inclusive_ns']/1e9, main_thread_closure_error_ns=closure,
        main_thread_exclusive_seconds={k:v/1e9 for k,v in sorted(exclusive.items(),key=lambda x:-x[1])},
        main_thread_call_counts=dict(count),
        background_exclusive_seconds_do_not_add={k:v/1e9 for k,v in workers.items()},
        process_read_boundary_io_delta=dict(io),
        io_caveat='Process counters include possible concurrent activity; not per-file physical sectors',
        counters=trace['counter_delta'],
        fpga_proof=result['fpga_proof'], first_token_ms=result['first_token_ms'],
        top_language_families=sorted(families,key=lambda x:-x['inclusive_ms'])[:12],
        performance_pass=False, device_wait_is_pure_pl_compute=False,
        preload_cache_conditions='Release asset hashes were scanned in same process before runtime; no controlled cold/warm A/B',
        next_step='Select one candidate using exposed cost, preserve numerical/protocol rules, and validate separately')
    destination = RUN / 'PROFILE_SUMMARY.json'
    if destination.exists(): raise RuntimeError('Immutable summary exists')
    destination.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:summary[k] for k in ('status','prefill_seconds','main_thread_exclusive_seconds','background_exclusive_seconds_do_not_add','counters')},indent=2))


if __name__ == '__main__': main()
