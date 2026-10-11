"""Strict raw-byte collection. A completed capacity rejection is not a PASS."""
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import m351_workflow as w
from ps_slot_capacity import never_submitted_release

PKG=w.BASE/'candidates/M362-common-load-observer-01'
CASES=('A1','B1','B2','A2')
SIZES=[6963200]*4+[389152,2621440,2621440]
PRIOR='ca35750d1b7043b76a16c75b97341616823137a58d91545576de0361a6ba3bde'

def completed(r):
    if not r.get('diagnostic_completed'):return False
    assert r['status'] in ('PASS_COMPLETE_RUNTIME_CAPACITY','FAIL_COMPLETE_RUNTIME_CAPACITY')
    assert r['host_calls']==r['logical_calls']==0 and not r['blocked_inference_attempts']
    assert r['safe_buffers_released'] and not r['unsafe_buffers_retained']
    assert [x['bytes'] for x in r['allocated_buffers']]==SIZES
    assert r['released_buffers']==list(reversed(r['allocated_buffers']))
    assert never_submitted_release(r['final_snapshot'],0,0,[],7)
    assert never_submitted_release(r['stable_restore_snapshot'],0,0,[],7)
    assert r['stable_overlay_reloaded'] and not r['stable_restore_transaction_submitted']
    assert r['stable_bit_sha256']=='1cbf7bbb86cfe64c2349418d5a15890d735bea3fa4c999060c8a9da9ac3206ac'
    assert r['boot_unchanged'] and r['cmdline_unchanged'] and r['elapsed_s_diagnostic_not_performance']<=600
    rows=[x for x in r['io_events'] if x['name']=='release_preflight.digest']
    assert len(rows)==35 and all('returned_sha256' in x and 'exception' not in x for x in rows)
    assert len([x for x in r['io_events'] if x['name']=='tokenizer.from_file'])==2
    assert len([x for x in r['io_events'] if x['name']=='pynq.Overlay'])==1
    assert len(r['retained_inventory']['buffers'])==7
    for key in ('loaded_capacity','settled_capacity'):
        x=r[key];assert x['required_cma_bytes']==x['required_mem_available_bytes']==64<<20
        assert x['meets_threshold']==(x['cma_free_bytes']>=64<<20 and x['mem_available_bytes']>=64<<20)
    fits=all(r[x]['meets_threshold'] for x in ('loaded_capacity','settled_capacity'))
    assert r['memory_capacity_proven']==fits and r['gate_return_code']==(0 if fits else 1)
    if fits:assert not r['errors']
    else:assert len(r['errors'])==1 and r['errors'][0].startswith('CapacityRejected:')
    return True

def validate(r):
    assert r['case'] in CASES and r['build_id']==('0x4D333537' if r['case'].startswith('B') else '0x4D395832')
    assert r['gate_level']=='load-only-memory-diagnostic' and r['prior_board_sha256']==PRIOR
    assert r['manifest_sha256']==w.sha(PKG/'PACKAGE_MANIFEST.json')
    assert r['common_runner_sha256']==w.sha(PKG/'m362_load_only_probe.py')
    assert type(r['gate_return_code']) is int and r['gate_return_code'] in (0,1)
    for k in ('numerical_pass','performance_pass','formal_promotion_allowed','worker_started','model_forward_calls','fpga_transactions','serving_after_vision_capacity_proven'):assert not r[k],k
    assert r['ps_slot']=={}
    done=completed(r)
    if r['gate_return_code']==0:assert done
    elif not done:assert r['errors'] and not r['memory_capacity_proven']
    return done

def decode(text):
    hashes=re.findall(r'(?m)^M362_RESULT_SHA256=([0-9a-f]{64})\s*$',text)
    codes=re.findall(r'(?m)^M362_SAVED_GATE_RC=([01])\s*$',text)
    chunks=re.findall(r'(?m)^M362_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    assert len(hashes)==len(codes)==1 and chunks and len(chunks)==int(chunks[0][1])
    parts=[]
    for i,(index,total,value) in enumerate(chunks):
        assert int(index)==i and int(total)==len(chunks)
        part=base64.b64decode(value,validate=True);assert 0<len(part)<=1800;parts.append(part)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest();assert digest==hashes[0]
    r=json.loads(raw);validate(r);assert int(codes[0])==r['gate_return_code']
    done=re.findall(r'M362_DONE case=(A1|B1|B2|A2) gate_rc=(\d+) export_rc=(\d+)',text)
    if done:assert len(done)==1 and done[0]==(r['case'],codes[0],'0')
    return digest,raw,r

def selftest():
    snap=dict(ap_ctrl=4,ap_return=0,mm2s_dmasr=0,s2mm_dmasr=0,mm2s_error=False,s2mm_error=False,kernel_read_error='',return_read_error='',dma_read_error='')
    buffers=[dict(address=i,bytes=s) for i,s in enumerate(SIZES)]
    r=dict(case='A1',build_id='0x4D395832',gate_level='load-only-memory-diagnostic',prior_board_sha256=PRIOR,manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),common_runner_sha256=w.sha(PKG/'m362_load_only_probe.py'),gate_return_code=1,status='FAIL_COMPLETE_RUNTIME_CAPACITY',errors=['CapacityRejected: below reserve'],diagnostic_completed=True,host_calls=0,logical_calls=0,blocked_inference_attempts=[],safe_buffers_released=True,unsafe_buffers_retained=False,allocated_buffers=buffers,released_buffers=list(reversed(buffers)),final_snapshot=snap,stable_restore_snapshot=snap,stable_overlay_reloaded=True,stable_restore_transaction_submitted=False,stable_bit_sha256='1cbf7bbb86cfe64c2349418d5a15890d735bea3fa4c999060c8a9da9ac3206ac',boot_unchanged=True,cmdline_unchanged=True,elapsed_s_diagnostic_not_performance=1,memory_capacity_proven=False,ps_slot={},retained_inventory=dict(buffers=buffers),io_events=[dict(name='release_preflight.digest',returned_sha256='0'*64)]*35+[dict(name='tokenizer.from_file')]*2+[dict(name='pynq.Overlay')])
    for k in ('numerical_pass','performance_pass','formal_promotion_allowed','worker_started','model_forward_calls','fpga_transactions','serving_after_vision_capacity_proven'):r[k]=False
    for k in ('loaded_capacity','settled_capacity'):r[k]=dict(required_cma_bytes=64<<20,required_mem_available_bytes=64<<20,cma_free_bytes=(64<<20)-1,mem_available_bytes=64<<20,meets_threshold=False)
    def exported(obj):
        raw=w.encoded(obj);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M362_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM362_SAVED_GATE_RC='+str(obj['gate_return_code'])+'\n'+''.join(f'M362_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode()+'\n' for i,p in enumerate(parts))+f'M362_DONE case={obj["case"]} gate_rc={obj["gate_return_code"]} export_rc=0\n'
    assert completed(decode(exported(r))[2])
    b=copy.deepcopy(r);b.update(case='B1',build_id='0x4D333537');assert decode(exported(b))[2]==b
    good=copy.deepcopy(r);good.update(status='PASS_COMPLETE_RUNTIME_CAPACITY',gate_return_code=0,errors=[],memory_capacity_proven=True)
    for k in ('loaded_capacity','settled_capacity'):good[k].update(cma_free_bytes=64<<20,meets_threshold=True)
    assert completed(decode(exported(good))[2])
    bads=[exported(r).replace('M362_RESULT_CHUNK=1/','M362_RESULT_CHUNK=0/'),exported(r).replace('export_rc=0','export_rc=1'),exported(r)+'M362_RESULT_SHA256='+'0'*64+'\n']
    for k,v in [('fpga_transactions',1),('safe_buffers_released',False),('released_buffers',buffers),('manifest_sha256','0'*64),('common_runner_sha256','0'*64),('boot_unchanged',False),('memory_capacity_proven',True),('io_events',[]),('host_calls',1),('blocked_inference_attempts',['forward']),('gate_return_code',0),('elapsed_s_diagnostic_not_performance',601),('stable_restore_transaction_submitted',True)]:bads.append(exported(dict(r,**{k:v})))
    for bad in bads:
        try:decode(bad)
        except (AssertionError,ValueError):pass
        else:raise AssertionError('Invalid load comparison result accepted')
    return len(bads)

def collect(log,case):
    digest,raw,r=decode(log.read_text(encoding='utf-8-sig'));assert r['case']==case
    out=w.BASE/f'runs/M362-load-{case}-board-01/BOARD_RESULT.json'
    w.atomic(out,raw,immutable=True)
    w.atomic(out.parent/'COLLECTION.json',w.encoded(dict(raw_sha256=digest,log_sha256=w.sha(log),original_bytes=True,reexecuted=False)),immutable=True)
    w.sync('latest_m362_load_'+case,dict(status=r['status'],sha256=digest,result=out.relative_to(w.ROOT).as_posix(),diagnostic_completed=completed(r)),f'## M362 共用只加载对照 {case}\n\nBuild{r["build_id"]}，原rc{r["gate_return_code"]}，{r["status"]}。仅逐文件SHA/逐DMA分配/对象保留诊断，0模型forward/FPGA事务；64MiB余量保持，非输出/性能PASS。证据SHA `{digest}`。自然缓存条件独立记录，不声称缓存完全一致。')
    print(r['status'],digest,'diagnostic_completed='+str(completed(r)))
    if not completed(r):raise RuntimeError('Incomplete load diagnostic; stop series and recover only')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--selftest',action='store_true');p.add_argument('log',nargs='?',type=Path);p.add_argument('case',nargs='?',choices=CASES);a=p.parse_args()
    if a.selftest:print('M362_COLLECTOR_SELFTEST_PASS',selftest())
    else:collect(a.log,a.case)
