"""Saved-log observation validation; no tools or hardware calls."""
import re


def rows(log, tag):
    return [{k: int(v) for k, v in re.findall(r'(\w+)=(\d+)', line)}
            for line in re.findall(r'^' + tag + r' [^\r\n]*', log, re.M)]


def validate_progress(log, prep, variant):
    totals = rows(log, 'M441_PROGRESS')
    ports = rows(log, 'M441_PORT_PROGRESS')
    delay = re.findall(r'^M441_DELAY channel=(\w+) count=(\d+) sum=(\d+)\s*$', log, re.M)
    required = {'cycle', 'shard', 'AR', 'R', 'pending', 'gap', 'ARSTALL', 'RSTALL', 'MAC', 'iter', 'qwrite', 'qread', 'qcount', 'qhigh', 'qfull', 'live'}
    complete = bool(totals) and all({'cycle', 'output', 'tx', 'rx_stall', 'tx_stall', 'ctrl', 'stagnant', 'terminal'} <= set(t) for t in totals)
    grouped = {}
    for p in ports:
        grouped.setdefault(p.get('cycle'), []).append(p)
    port_complete = complete and len(grouped) == len(totals) and all(
        len(grouped.get(t['cycle'], [])) == 4 and
        sorted(p.get('shard', -1) for p in grouped[t['cycle']]) == [0, 1, 2, 3] and
        all(required <= set(p) for p in grouped[t['cycle']]) for t in totals)
    monotone = port_complete
    if port_complete:
        for a, b in zip(totals, totals[1:]):
            monotone &= b['cycle'] > a['cycle'] and all(b[k] >= a[k] for k in ('output', 'tx', 'rx_stall', 'tx_stall', 'ctrl'))
        for shard in range(4):
            pp = [p for p in ports if p['shard'] == shard]
            for a, b in zip(pp, pp[1:]):
                monotone &= all(b[k] >= a[k] for k in ('AR', 'R', 'gap', 'ARSTALL', 'RSTALL', 'MAC', 'iter', 'qwrite', 'qread', 'qfull'))
    final = totals[-1] if complete else {}
    final_ports = grouped.get(final.get('cycle'), [])
    terminal_ok = complete and sum(t['terminal'] == 1 for t in totals) == 1 and final['terminal'] == 1 and final['output'] == prep['expected']['output_words']
    bounds = port_complete and all(p['qcount'] <= 34 and p['qhigh'] <= 34 and p['qread'] <= p['qwrite'] and p['qwrite'] - p['qread'] <= 34 for p in ports)
    terminal_counts = terminal_ok and port_complete and all(p['R'] == prep['expected']['weight_beats_per_shard'] and p['pending'] == 0 and p['qcount'] == 0 for p in final_ports)
    no_stall = complete and all(t['stagnant'] < 1000000 for t in totals)
    delays = {}
    delay_valid = True
    for channel, count, total in delay:
        count, total = int(count), int(total)
        prior = delays.get(channel)
        delay_valid &= count > 0 and count % 4096 == 0 and 0 <= total <= count * 256
        if prior:
            delay_valid &= count > prior['count'] and total >= prior['sum']
        delays[channel] = dict(count=count, sum=total, generated_mean_cycles=total / count)
    return dict(checks=dict(progress_complete=port_complete, progress_monotone=bool(monotone), progress_terminal=terminal_ok,
                            progress_bounds=bounds, progress_final_counts=terminal_counts, progress_no_global_stall=no_stall, delay_samples_valid=bool(delay_valid)),
                final=final, final_ports=final_ports, generated_delay_samples=delays,
                counters_overlap_and_must_not_be_summed=True,
                periodic_snapshot_count=len(totals), failed_snapshot_present=any(t.get('terminal') == 2 for t in totals),
                interpretation='gap is pending/RREADY/no-RVALID; rx_stall is RX-valid/no-ready. Concurrent counters are exposure observations, not disjoint critical-path attribution.')


def selftest():
    def fixture(final_kind=1):
        lines = []
        for c, v, term in [(50000, 5, 0), (51000, 10, final_kind)]:
            lines.append(f'M441_PROGRESS cycle={c} output={v} tx=10 rx_stall=2 tx_stall=0 ctrl=3 stagnant=0 terminal={term}')
            for j in range(4):
                lines.append(f'M441_PORT_PROGRESS cycle={c} shard={j} AR={v} R={v} pending=0 gap=3 ARSTALL=4 RSTALL=0 MAC={v} iter={v} qwrite=0 qread=0 qcount=0 qhigh=0 qfull=0 live=0')
        return '\n'.join(lines) + '\n'
    prep = dict(expected=dict(output_words=10, weight_beats_per_shard=10))
    good = fixture()
    assert all(validate_progress(good, prep, 'A')['checks'].values())
    bad = [fixture(2), '', good.replace('shard=3', 'shard=2'), good.replace('R=10', 'R=9'),
           good.replace('output=10', 'output=9'), good.replace('qcount=0', 'qcount=35'),
           good.replace('qread=0', 'qread=1'), good.replace('stagnant=0', 'stagnant=1000000'),
           good.replace('cycle=51000', 'cycle=49000'), good + 'M441_DELAY channel=w0 count=4096 sum=1048577\n']
    for log in bad:
        assert not all(validate_progress(log, prep, 'A')['checks'].values())
    return 1 + len(bad)
