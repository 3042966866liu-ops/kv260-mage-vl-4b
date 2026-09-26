"""Validate and attribute diagnostic host spans without summing worker overlap."""
from collections import defaultdict


def summarize(record):
    if record['status']!='RECORDED':
        raise ValueError('Cannot attribute incomplete/failed Decode as success')
    rows=record['trace']['events']
    by_id={r['id']:r for r in rows}
    if len(by_id)!=len(rows):raise ValueError('Duplicate span identity')
    roots=[r for r in rows if r['name']=='decode_call' and r['parent'] is None]
    if len(roots)!=1:raise ValueError('Expected one Decode root')
    root=roots[0];main=root['thread'];children=defaultdict(list)
    for row in rows:
        if row['failed'] or row['end_ns'] is None or row['end_ns']<row['start_ns']:
            raise ValueError('Failed/incomplete/nonmonotonic span')
        if row['parent'] is not None:
            parent=by_id.get(row['parent'])
            if parent is None or parent['thread']!=row['thread']:
                raise ValueError('Missing or cross-thread parent')
            if not parent['start_ns']<=row['start_ns']<=row['end_ns']<=parent['end_ns']:
                raise ValueError('Child outside parent')
            children[parent['id']].append(row)
        if row['thread']==main and row['id']!=root['id']:
            seen={row['id']};cursor=row
            while cursor['parent'] is not None:
                if cursor['parent'] in seen:raise ValueError('Cyclic spans')
                seen.add(cursor['parent']);cursor=by_id[cursor['parent']]
            if cursor['id']!=root['id']:raise ValueError('Unaccounted main-thread root')
    exclusive=defaultdict(int);workers=defaultdict(int);families=[]
    for row in rows:
        child_ns=0;cursor=row['start_ns']
        for child in sorted(children[row['id']],key=lambda x:x['start_ns']):
            if child['start_ns']<cursor:raise ValueError('Overlapping synchronous spans')
            child_ns+=child['end_ns']-child['start_ns'];cursor=child['end_ns']
        inclusive=row['end_ns']-row['start_ns'];own=inclusive-child_ns
        if own<0 or own!=row['exclusive_ns'] or inclusive!=row['inclusive_ns']:
            raise ValueError('Stored span accounting differs')
        if row['thread']==main:exclusive[row['name']]+=own
        else:workers[row['name']]+=own
        if row['name']=='language_family':
            families.append(dict(**row['metadata'],inclusive_s=inclusive/1e9,
                                 exclusive_s=own/1e9))
    duration=root['end_ns']-root['start_ns']
    if sum(exclusive.values())!=duration:raise ValueError('Decode timeline does not close')
    delta=record['counter_delta']
    if delta['host_calls']!=delta['logical_calls']+delta['scale_retry_count']:
        raise ValueError('Call/retry accounting differs')
    before,after=record['cache_before'],record['cache_after']
    if before['cache_identity']!=after['cache_identity'] or len(before['layers'])!=len(after['layers']):
        raise ValueError('Changed cache identity/layers')
    for old,new in zip(before['layers'],after['layers']):
        for key in ('key_shape','value_shape'):
            if old[key][1:]!=new[key][1:] or old[key][0]+1!=new[key][0]:
                raise ValueError('Not one-token KV growth')
    if any(f['input_shape'][0]!=1 for f in families):raise ValueError('Multi-token Decode family')
    return dict(status='ATTRIBUTED_DIAGNOSTIC',decode_call_s=duration/1e9,
                main_thread_exclusive_s={k:v/1e9 for k,v in exclusive.items()},
                worker_exclusive_s_not_additive={k:v/1e9 for k,v in workers.items()},
                families=sorted(families,key=lambda f:f['inclusive_s'],reverse=True),
                counters=delta,closure_error_ns=0,numerical_acceptance=False,
                note='Host intervals, not pure PL cycles; no baseline speedup inferred')
