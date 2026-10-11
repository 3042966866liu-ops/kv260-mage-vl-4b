"""Thread-exclusive attribution; full bounded trace remains independently recoverable."""
import base64
from collections import defaultdict
import hashlib
import json
import zlib

MAX_RAW = 20 << 20


def summarize(report):
    if report['status'] != 'RECORDED' or report['input_shape'] != [159,2560]:
        raise RuntimeError('Incomplete/wrong candidate Prefill trace')
    rows = report['trace']['events']
    if not 0 < len(rows) <= 20000:
        raise RuntimeError('Trace bound differs')
    byid = {r['id']:r for r in rows}
    if len(byid) != len(rows):raise RuntimeError('Duplicate interval')
    # Independently reconstruct exclusive intervals; do not trust exported sums.
    children=defaultdict(list)
    for row in rows:
        if row['failed'] or row['end_ns'] is None:raise RuntimeError('Failed/open span')
        if row['parent'] is not None:
            if row['parent'] not in byid:raise RuntimeError('Missing parent')
            children[row['parent']].append(row)
    for row in rows:
        cursor=row['start_ns'];used=0
        for child in sorted(children[row['id']],key=lambda x:x['start_ns']):
            if child['thread']!=row['thread'] or child['start_ns']<cursor or child['end_ns']>row['end_ns']:raise RuntimeError('Invalid nested span')
            used+=child['end_ns']-child['start_ns'];cursor=child['end_ns']
        inclusive=row['end_ns']-row['start_ns']
        if inclusive<0 or row['inclusive_ns']!=inclusive or row['exclusive_ns']!=inclusive-used or inclusive-used<0:raise RuntimeError('Invalid attribution')
    roots=[r for r in rows if r['name']=='prefill_call']
    if len(roots)!=1 or roots[0]['parent'] is not None:raise RuntimeError('Prefill root differs')
    root=roots[0];main=[r for r in rows if r['thread']==root['thread']]
    if sum(r['exclusive_ns'] for r in main)!=root['inclusive_ns']:raise RuntimeError('Main wall tree does not close')
    exclusive=defaultdict(int);worker=defaultdict(int);calls=defaultdict(int);io=defaultdict(int)
    for r in rows:
        (exclusive if r['thread']==root['thread'] else worker)[r['name']]+=r['exclusive_ns']
        calls[r['name']]+=1
        if r['name']=='weight_file_read':
            for k,v in r['metadata'].get('process_io_delta',{}).items():io[k]+=v
    families=[dict(**r['metadata'],inclusive_ms=r['inclusive_ns']/1e6,self_ms=r['exclusive_ns']/1e6) for r in rows if r['name']=='language_family']
    return dict(status='MEASURED_CANDIDATE_INSTRUMENTED_PREFILL_NOT_PERFORMANCE',
        prefill_s=root['inclusive_ns']/1e9,main_thread_closure_error_ns=0,
        main_exclusive_s={k:v/1e9 for k,v in sorted(exclusive.items(),key=lambda x:-x[1])},
        background_exclusive_s_do_not_add={k:v/1e9 for k,v in sorted(worker.items(),key=lambda x:-x[1])},
        all_thread_call_counts=dict(calls),process_read_boundary_io_delta=dict(io),
        counter_delta=report['counter_delta'],original_phase_ms_delta=report['phase_ms_delta'],
        language_families=families,trace_event_count=len(rows),
        device_wait_is_pure_compute=False,cross_thread_addition_allowed=False,
        cache_policy='natural files; original PS visual cache warm; process I/O is not per-file disk sectors',
        interpretation='Main exclusive costs identify exposed work. Workers overlap wall time; device completion includes DMA/DDR/compute/backpressure. This diagnostic is not a new speed result.')


def pack(report):
    raw=json.dumps(report,sort_keys=True,separators=(',',':')).encode('utf-8')
    if len(raw)>MAX_RAW:raise RuntimeError('Trace serialization bound')
    return dict(raw_bytes=len(raw),raw_sha256=hashlib.sha256(raw).hexdigest(),
                encoding='zlib-base64-v1',data=base64.b64encode(zlib.compress(raw)).decode('ascii'))


def unpack(value):
    if value['encoding']!='zlib-base64-v1' or type(value['raw_bytes']) is not int or not 0<value['raw_bytes']<=MAX_RAW:raise RuntimeError('Invalid packed trace header')
    compressed=base64.b64decode(value['data'],validate=True)
    if len(compressed)>MAX_RAW:raise RuntimeError('Compressed trace bound')
    decoder=zlib.decompressobj();raw=decoder.decompress(compressed,MAX_RAW+1)
    if len(raw)>MAX_RAW or not decoder.eof or decoder.unconsumed_tail or decoder.unused_data:raise RuntimeError('Invalid/bounded compressed stream')
    if len(raw)!=value['raw_bytes'] or hashlib.sha256(raw).hexdigest()!=value['raw_sha256']:raise RuntimeError('Trace raw SHA differs')
    return json.loads(raw),raw
