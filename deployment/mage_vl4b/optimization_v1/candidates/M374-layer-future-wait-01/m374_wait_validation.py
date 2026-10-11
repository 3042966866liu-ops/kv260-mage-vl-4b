"""Reconstruct nested intervals and expected frozen single-layer result calls."""
from collections import defaultdict

FAMILIES=('q','kv','attention_out','gate_up','mlp_down')
FUTURE_SHA='205acdb5fd87bc95cb20e986bccff404c1d558617bd54849d9e9947cd039d70f'

def validate(report, transactions, *, require_complete=True):
    if not report['bindings_restored'] or report['performance_eligible'] or report['new_workers'] or report['extra_cma_allocations']:
        raise ValueError('Observation scope/restoration differs')
    if report['future_result_source_sha256']!=FUTURE_SHA: raise ValueError('Future implementation differs')
    events=report['trace']['events'];byid={r['id']:r for r in events};children=defaultdict(list)
    if len(byid)!=len(events) or not 0<len(events)<=256: raise ValueError('Trace identity/bound differs')
    for row in events:
        if row['parent'] is not None:
            if row['parent'] not in byid:raise ValueError('Missing trace parent')
            children[row['parent']].append(row)
        if row['end_ns'] is None or (require_complete and row['failed']):raise ValueError('Live/failed trace')
    for row in events:
        cursor=row['start_ns'];used=0
        for child in sorted(children[row['id']],key=lambda r:r['start_ns']):
            if child['thread']!=row['thread'] or child['start_ns']<cursor or child['end_ns']>row['end_ns']:raise ValueError('Invalid nesting')
            used+=child['end_ns']-child['start_ns'];cursor=child['end_ns']
        inclusive=row['end_ns']-row['start_ns']
        if inclusive<0 or row['inclusive_ns']!=inclusive or row['exclusive_ns']!=inclusive-used or row['exclusive_ns']<0:raise ValueError('Trace attribution differs')
    roots=[r for r in events if r['name']=='layer_call']
    if len(roots)!=1 or roots[0]['parent'] is not None:raise ValueError('Layer root differs')
    root=roots[0]
    if any(r['thread']!=root['thread'] for r in events) or sum(r['exclusive_ns'] for r in events)!=root['inclusive_ns']:raise ValueError('Main thread closure differs')
    records=report['records'];sums={};by_family={}
    if require_complete and (report['families']!=list(FAMILIES) or len(records)!=50):raise ValueError('Layer result coverage differs')
    for kind in ('pack','parse'):
        rows=[r for r in records if r['kind']==kind]
        for row in rows:
            if row['layer']!=0 or row['family'] not in FAMILIES or type(row['ready_before']) is not bool:raise ValueError('Result identity differs')
            if type(row['condition_wait_calls']) is not int or row['condition_wait_calls'] not in (0,1):raise ValueError('Wait call count differs')
            if not 0<=row['condition_wait_ns']<=row['result_wall_ns'] or (require_complete and row['exception'] is not None):raise ValueError('Wait duration/exception differs')
            if row['condition_wait_calls']==0 and row['condition_wait_ns']!=0:raise ValueError('Unentered wait has duration')
            if row['ready_before'] and row['condition_wait_calls']:raise ValueError('Ready future slept')
        expected=dict(calls=len(rows),ready_before=sum(r['ready_before'] for r in rows),
            calls_with_condition_wait=sum(r['condition_wait_calls']>0 for r in rows),condition_wait_calls=sum(r['condition_wait_calls'] for r in rows),
            result_wall_s=sum(r['result_wall_ns'] for r in rows)/1e9,condition_wait_s=sum(r['condition_wait_ns'] for r in rows)/1e9,
            exceptions=sum(r['exception'] is not None for r in rows))
        if expected!=report['summary'][kind]:raise ValueError('Wait summary differs')
        spans=[r for r in events if r['name']==kind+'_future_result']
        if len(spans)!=len(rows):raise ValueError('Result span coverage differs')
        waits=[r for r in events if r['name']=='future_condition_wait' and r['metadata']['kind']==kind]
        if len(waits)!=expected['condition_wait_calls']:raise ValueError('Wait span coverage differs')
        for record,span in zip(rows,spans):
            if any(span['metadata'][key]!=record[key] for key in ('layer','family','chain_index','token_start','ready_before')):raise ValueError('Result span identity differs')
            actual=[r for r in children[span['id']] if r['name']=='future_condition_wait']
            if len(actual)!=record['condition_wait_calls'] or record['result_wall_ns']>span['inclusive_ns']:raise ValueError('Result timer containment differs')
            if sum(r['inclusive_ns'] for r in actual)<record['condition_wait_ns']:raise ValueError('Wait timer containment differs')
        for family in FAMILIES:
            group=[r for r in rows if r['family']==family]
            chains={t['chain_index'] for t in transactions if t['family']==family}
            # Original two-output-buffer drain follows slot order, not token order.
            order=[0,32,64,96,128] if kind=='pack' else [0,32,64,128,96]
            if require_complete and (len(chains)!=1 or [r['token_start'] for r in group]!=order or {r['chain_index'] for r in group}!=chains):raise ValueError('T32/chain order differs')
        sums[kind]=expected
    for family in FAMILIES:
        group=[r for r in records if r['kind']=='parse' and r['family']==family]
        by_family[family]=dict(parse_result_s=sum(r['result_wall_ns'] for r in group)/1e9,
            parse_wait_s=sum(r['condition_wait_ns'] for r in group)/1e9,
            reuse_wait_s=sum(r['condition_wait_ns'] for r in group if r['token_start'] in (0,32,64))/1e9,
            tail_wait_s=sum(r['condition_wait_ns'] for r in group if r['token_start'] in (96,128))/1e9)
    return dict(layer_instrumented_s=root['inclusive_ns']/1e9,main_thread_closure_error_ns=0,summary=sums,
        by_family=by_family,scope='Single synthetic fixed-text layer; not fixed video or performance benefit')
