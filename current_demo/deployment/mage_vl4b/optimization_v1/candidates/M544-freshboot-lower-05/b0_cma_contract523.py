"""Independent complete CMA trace validation; never discard busy-retry events.

Only exact M455/M462 configuration allocations, not resident buffer allocations.
Linux v5.15 cma_alloc clears the unsuccessful bitmap before busy_retry and
accounts successful pages only after a non-null finish. Actual finish/release,
same PID/PFN, counters, provenance, trace loss and budgets remain mandatory.
"""
import hashlib
import math
import re

BITS = {'1cbf7bbb86cfe64c2349418d5a15890d735bea3fa4c999060c8a9da9ac3206ac'}


def validate(record):
    assert record['kernel'] == '5.15.0-1027-xilinx-zynqmp'
    assert record['page_size'] == 4096 and record['pages'] == 1904
    assert record['bit_bytes'] == 7797914 and record['bit_sha256'] in BITS
    before, after = record['before'], record['after']
    assert set(before) == set(after)
    assert {k: after[k] - before[k] for k in before} == {
        'reserved:alloc_pages_success': 1904, 'reserved:alloc_pages_fail': 0}
    trace = record['trace']; text = trace['trace_text']
    assert len(text.encode()) <= 1 << 20
    assert hashlib.sha256(text.encode()).hexdigest() == trace['trace_sha256']
    assert trace['pid'] == record['pid'] and record['pid'] > 0
    assert math.isfinite(trace['elapsed_trace_s']) and 0 <= trace['elapsed_trace_s'] <= 30
    assert not trace['observer_errors'] and trace['own_instance_removed']
    assert trace['owned_instance_only'] and not trace['shared_root_configuration_changed']
    assert set(trace['stats']) == {'cpu0', 'cpu1', 'cpu2', 'cpu3'}
    for stats in trace['stats'].values():
        for field in ('overrun', 'commit overrun', 'dropped events'):
            match = re.search(r'^' + re.escape(field) + r':\s*(\d+)', stats, re.M)
            assert match and int(match[1]) == 0
    events = []
    # Include unknown CMA events too, so an unrecognized event fails closed.
    matches = list(re.finditer(r'(?m)^.*?\b(cma_\w+):\s*([^\n]*)\n', text))
    for index, match in enumerate(matches):
        name, fields = match[1], match[2]
        assert name in ('cma_alloc_start', 'cma_alloc_busy_retry', 'cma_alloc_finish', 'cma_release')
        assert re.search(r'-' + str(record['pid']) + r'\s', match[0])
        assert re.search(r'\bname=reserved\b', fields) and re.search(r'\bcount=1904\b', fields)
        tail = text[match.end():matches[index+1].start() if index+1 < len(matches) else len(text)]
        stack = tail.split('tracing_mark_write:', 1)[0]
        assert '=> zynqmp_fpga_ops_write' in stack
        assert (' => dma_free_attrs' if name == 'cma_release' else ' => dma_alloc_attrs') in stack
        events.append((name, fields))
    names = [event[0] for event in events]
    assert len(names) >= 3
    assert names[0] == 'cma_alloc_start' and names[-2:] == ['cma_alloc_finish', 'cma_release']
    assert all(name == 'cma_alloc_busy_retry' for name in names[1:-2])
    assert re.search(r'\balign=8\b', events[0][1])
    candidates = []
    pages = []
    for name, fields in events[1:]:
        pfn = re.search(r'\bpfn=(0x[0-9a-f]+)\b', fields)
        page = re.search(r'\bpage=([0-9a-f]+)\b', fields)
        assert pfn and page and int(pfn[1], 16) > 0 and int(page[1], 16) > 0
        if name != 'cma_release':
            assert re.search(r'\balign=8\b', fields)
            assert int(pfn[1], 16) % 256 == 0
            candidates.append(int(pfn[1], 16))
        pages.append((int(pfn[1], 16), page[1]))
    assert all(a < b for a, b in zip(candidates, candidates[1:]))
    assert pages[-2] == pages[-1], 'Successful PFN/page must be fully released by original PID'
    return {'reserved:alloc_pages_success': 1904}

