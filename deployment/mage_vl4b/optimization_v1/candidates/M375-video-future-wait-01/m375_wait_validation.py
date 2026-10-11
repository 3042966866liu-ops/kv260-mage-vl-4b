"""Independently validate narrow main-thread waits and exact frozen coverage."""
from collections import defaultdict

FUTURE_SHA = '205acdb5fd87bc95cb20e986bccff404c1d558617bd54849d9e9947cd039d70f'


def validate(report, contract):
    if (report['status'] != 'OBSERVED_FIXED_VIDEO_WAIT_ONLY' or report['input_shape'] != [159,2560]
            or not report['bindings_restored'] or report['performance_eligible'] or report['new_workers']
            or report['extra_cma_allocations'] or report['future_result_source_sha256'] != FUTURE_SHA):
        raise ValueError('Wait observation scope/implementation/restoration differs')
    if len(contract) != 154 or len(report['families']) != 154:
        raise ValueError('Family coverage differs')
    for row, expected in zip(report['families'], contract):
        if any(row[k] != expected[k] for k in ('layer','family','chain_index')) or len(row['input_shape']) != 2 or row['input_shape'][0] != 159:
            raise ValueError('Family input/identity/order differs')
    events = report['trace']['events']
    byid = {r['id']:r for r in events}
    children = defaultdict(list)
    if not 0 < len(events) <= 4096 or len(byid) != len(events):
        raise ValueError('Trace identity/bound differs')
    for row in events:
        if row['end_ns'] is None or row['failed']:
            raise ValueError('Live/failed trace')
        if row['parent'] is not None:
            if row['parent'] not in byid:
                raise ValueError('Missing parent')
            children[row['parent']].append(row)
    roots = [r for r in events if r['parent'] is None]
    if len(roots) != 1 or roots[0]['name'] != 'prefill_call':
        raise ValueError('Prefill root differs')
    root = roots[0]
    for row in events:
        if row['thread'] != root['thread']:
            raise ValueError('Unexpected worker trace')
        used = 0; cursor = row['start_ns']
        for child in sorted(children[row['id']], key=lambda r:r['start_ns']):
            if child['start_ns'] < cursor or child['end_ns'] > row['end_ns']:
                raise ValueError('Overlapping/escaped nested trace')
            used += child['end_ns']-child['start_ns']; cursor = child['end_ns']
        inclusive = row['end_ns']-row['start_ns']
        if inclusive < 0 or row['inclusive_ns'] != inclusive or row['exclusive_ns'] != inclusive-used or row['exclusive_ns'] < 0:
            raise ValueError('Trace attribution differs')
        parent = byid.get(row['parent'])
        if row['name'] == 'prefill_call':
            if row is not root: raise ValueError('Duplicate Prefill root')
        elif row['name'] == 'family_call':
            if parent is not root: raise ValueError('Family ancestry differs')
        elif row['name'] in ('pack_future_result','parse_future_result'):
            if parent is None or parent['name'] != 'family_call': raise ValueError('Result ancestry differs')
            if any(row['metadata'][k] != parent['metadata'][k] for k in ('layer','family','chain_index')):
                raise ValueError('Result escaped family identity')
        elif row['name'] == 'future_condition_wait':
            if parent is None or parent['name'] != row['metadata']['kind']+'_future_result': raise ValueError('Wait ancestry differs')
            if any(row['metadata'][k] != parent['metadata'][k] for k in ('chain_index','token_start')): raise ValueError('Wait identity differs')
        else: raise ValueError('Unknown trace event')
    if sum(r['exclusive_ns'] for r in events) != root['inclusive_ns']:
        raise ValueError('Main-thread attribution does not close')
    families = [r for r in events if r['name']=='family_call']
    if len(families) != 154 or [r['metadata'] for r in families] != report['families']:
        raise ValueError('Family trace coverage differs')
    records = report['records']; totals = {}
    if len(records) != 1540 or any(r['kind'] not in ('pack','parse') for r in records):
        raise ValueError('Result record coverage differs')
    for kind in ('pack','parse'):
        rows = [r for r in records if r['kind'] == kind]
        spans = [r for r in events if r['name'] == kind+'_future_result']
        if len(rows) != 770 or len(spans) != len(rows): raise ValueError('Result span coverage differs')
        expected_order = [(c['layer'],c['family'],c['chain_index'],t)
                          for c in contract for t in c[kind+'_token_order']]
        if [(r['layer'],r['family'],r['chain_index'],r['token_start']) for r in rows] != expected_order:
            raise ValueError('Frozen T32/chain order differs')
        for row, span in zip(rows,spans):
            if type(row['ready_before']) is not bool or type(row['condition_wait_calls']) is not int or row['condition_wait_calls'] not in (0,1):
                raise ValueError('Future ready/wait count differs')
            if row['exception'] is not None or not 0 <= row['condition_wait_ns'] <= row['result_wall_ns']:
                raise ValueError('Result exception/duration differs')
            if (row['condition_wait_calls']==0 and row['condition_wait_ns']!=0) or (row['ready_before'] and row['condition_wait_calls']):
                raise ValueError('Wait contradicts Future state')
            if any(span['metadata'][k]!=row[k] for k in ('layer','family','chain_index','token_start','ready_before')):
                raise ValueError('Record/trace identity differs')
            waits = children[span['id']]
            if any(w['name']!='future_condition_wait' for w in waits) or len(waits)!=row['condition_wait_calls'] or row['result_wall_ns']>span['inclusive_ns']:
                raise ValueError('Result duration containment differs')
            if sum(w['inclusive_ns'] for w in waits)<row['condition_wait_ns']:
                raise ValueError('Wait duration containment differs')
        value = dict(calls=len(rows), ready_before=sum(r['ready_before'] for r in rows),
            calls_with_condition_wait=sum(r['condition_wait_calls']>0 for r in rows),
            condition_wait_calls=sum(r['condition_wait_calls'] for r in rows),
            result_wall_s=sum(r['result_wall_ns'] for r in rows)/1e9,
            condition_wait_s=sum(r['condition_wait_ns'] for r in rows)/1e9, exceptions=0)
        if report['summary'][kind]!=value: raise ValueError('Wait summary differs')
        totals[kind]=value
    parse = [r for r in records if r['kind']=='parse']
    def grouped(keys):
        values={}
        for key in keys:
            rows=[r for r in parse if (r['layer'] if isinstance(key,int) else r['family'])==key]
            values[str(key)]=dict(calls=len(rows), actual_wait_s=sum(r['condition_wait_ns'] for r in rows)/1e9,
                reuse_wait_s=sum(r['condition_wait_ns'] for r in rows if r['token_start'] in (0,32,64))/1e9,
                tail_wait_s=sum(r['condition_wait_ns'] for r in rows if r['token_start'] in (96,128))/1e9)
        return values
    return dict(prefill_instrumented_s=root['inclusive_ns']/1e9, main_thread_closure_error_ns=0,
        summary=totals, by_family=grouped(sorted({c['family'] for c in contract})), by_layer=grouped(range(36)),
        parse_reuse_wait_s=sum(r['condition_wait_ns'] for r in parse if r['token_start'] in (0,32,64))/1e9,
        parse_tail_wait_s=sum(r['condition_wait_ns'] for r in parse if r['token_start'] in (96,128))/1e9,
        scope='Observed original language Futures; synchronous retries/head excluded; diagnostic, not new performance benefit')
