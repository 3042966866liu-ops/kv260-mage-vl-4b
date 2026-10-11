"""Independent protocol04 saved-evidence checks; no tool invocation."""
import collections
import re
from m441_protocol_evidence import validate_max, validate_timeout
from m441_progress03 import validate_progress


def validate_boundary(prep, receipt, log, data, golden, source):
    result = validate_max(prep, receipt, log, data, golden, source)
    progress = validate_progress(log, prep, 'B')
    result['checks'].update(progress['checks'])
    hold = re.findall(r'^M441_BOUNDARY_LAST_HOLD valid_cycles=(\d+) accepted_before=(\d+)\s*$', log, re.M)
    result['checks']['final_TLAST_hold128'] = hold == [('128', '327679')]
    # Complete byte coverage alone does not demonstrate a split at a boundary.
    ars = re.findall(r'^M441MAX_AR shard=(\d+) address=([0-9a-fA-F]+) len=(\d+) size=(\d+) burst=(\d+)\s*$', log, re.M)
    split = {}
    for i in range(4):
        tuples = collections.Counter((int(a,16),int(n)+1) for j,a,n,_,_ in ars if int(j)==i)
        # W4 record starting at word255 crosses the first 4KiB boundary.
        split[i] = tuples[(255*16,1)] == 10 and tuples[(256*16,16)] == 10
    result['checks']['actual_4KiB_split_four_ports'] = all(split.values())
    samples = re.findall(r'^M441_DELAY channel=(\w+) count=(\d+) sum=(\d+)\s*$', log, re.M)
    expected = {f'axi_latency_w{i}_get_rdata_lat' for i in range(4)} | {'svr_latency_rx_get_transfer_lat'}
    sampled = {ch for ch,count,total in samples if int(count)>=4096 and 0<int(total)<=8*int(count)}
    result['checks']['bounded_random_samples'] = bool(samples) and all(0<=int(total)<=8*int(count) for _,count,total in samples)
    result['checks']['nonzero_random_four_R_and_RX'] = expected <= sampled
    result['details'].update(progress_proof=progress, final_hold=hold, split_at_first_4KiB=split,
                             missing_small_AR_delay_samples='AR calls may remain below4096; no sampled mean is invented')
    result['accepted'] = all(result['checks'].values()) and not result['errors']
    return result


def validate_boundary_timeout(receipt, log, same_snapshot):
    result = validate_timeout(receipt, log, same_snapshot)
    # Actual watchdog must export its counters before the fatal.
    result['checks']['failure_snapshot'] = bool(re.search(r'^M441_BOUNDARY_TIMEOUT_SNAPSHOT ',log,re.M))
    result['accepted'] = all(result['checks'].values())
    return result
