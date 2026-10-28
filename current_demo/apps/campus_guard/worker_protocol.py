"""Bounded data-only COM3 job protocol. No process or device operations."""
import base64,hashlib,json,re,secrets,select,sys,time,zlib

def parse_job(line,nonce,cases,seen):
    if not isinstance(line,str) or not 1<=len(line.encode())<=512:raise ValueError('Bounded512-byte job required')
    value=json.loads(line)
    if not isinstance(value,dict) or value.get('nonce')!=nonce:raise ValueError('Fresh exact ready nonce required')
    if value.get('action')=='stop' and set(value)=={'action','nonce'}:return None
    if set(value)!={'action','nonce','id','case_id'} or value['action']!='infer':raise ValueError('Data-only job fields differ')
    if not isinstance(value['id'],str) or re.fullmatch('[0-9a-f]{32}',value['id']) is None or value['id'] in seen:raise ValueError('New UUID job required')
    if value['case_id'] not in cases:raise ValueError('Frozen demo case required')
    return value

def emit(kind,value):
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode();assert len(raw)<=32768
    encoded=base64.b64encode(zlib.compress(raw,9)).decode()
    print('M529_'+kind+' '+hashlib.sha256(raw).hexdigest()+' '+encoded,flush=True)

def jobs(requests,maximum=4,idle_seconds=300):
    cases={r['id']:r for r in requests};seen=set()
    assert len(cases)==4 and maximum==4
    for _ in range(maximum):
        nonce=secrets.token_hex(16);emit('READY',dict(nonce=nonce,remaining=maximum-len(seen),idle_seconds=idle_seconds))
        ready,_,_=select.select([sys.stdin],[],[],idle_seconds)
        if not ready:emit('STOP',dict(reason='idle_timeout'));return
        line=sys.stdin.readline(513)
        if not line:emit('STOP',dict(reason='stdin_EOF'));return
        job=parse_job(line,nonce,cases,seen)
        if job is None:emit('STOP',dict(reason='operator_normal_stop'));return
        seen.add(job['id']);yield 'LIVE_'+job['id'],'B',cases[job['case_id']],job
    emit('STOP',dict(reason='four_job_budget_complete'))

def tests():
    nonce='a'*32;ids={'cal_04_t0':{},'cal_04_t1':{},'cal_00_t0':{},'cal_00_t1':{}};valid=dict(action='infer',nonce=nonce,id='b'*32,case_id='cal_04_t0')
    assert parse_job(json.dumps(valid),nonce,ids,set())==valid
    assert parse_job(json.dumps(dict(action='stop',nonce=nonce)),nonce,ids,set()) is None
    bad=[dict(valid,nonce='c'*32),dict(valid,id='b'*31),dict(valid,case_id='$(reboot)'),dict(valid,extra='unsafe'),dict(valid,action='shell'),['not dict']]
    count=0
    for value in bad:
        try:parse_job(json.dumps(value),nonce,ids,set())
        except ValueError:count+=1
        else:raise AssertionError('Invalid job accepted')
    for line,seen in [('x'*513,set()),(json.dumps(valid),{'b'*32})]:
        try:parse_job(line,nonce,ids,seen)
        except ValueError:count+=1
        else:raise AssertionError('Oversize/duplicate accepted')
    return dict(status='PASS_BOUNDED_COM3_JOB_COMPONENT_NOT_HARDWARE',invalid_cases=count,valid_job=True,normal_stop=True,device_APIs=0)
