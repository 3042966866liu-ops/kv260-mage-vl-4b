"""Validate immutable no-forward capacity evidence and synchronize recovery."""
import argparse
import base64
import hashlib
import json
import re
from pathlib import Path
import m351_workflow as w
from ps_slot_capacity import never_submitted_release

PRIOR='ca35750d1b7043b76a16c75b97341616823137a58d91545576de0361a6ba3bde'
MANIFEST='9069628e668a98ec0965f0638a85c369ea80587b844075e72e25a710efdd4eb3'

def validate(r):
    assert r['build_id']=='0x4D333537' and r['gate_level']=='load-only-memory-diagnostic'
    assert r['prior_board_sha256']==PRIOR and r['manifest_sha256']==MANIFEST
    code=r['gate_return_code'];assert type(code) is int and code in (0,1)
    for key in ('numerical_pass','performance_pass','formal_promotion_allowed','worker_started','model_forward_calls','fpga_transactions','serving_after_vision_capacity_proven'):
        assert not r[key],key
    assert r['host_calls']==r['logical_calls']==0 and not r['blocked_inference_attempts']
    assert r['ps_slot']=={},'No PS slot permitted'
    if code==0:
        assert r['status']=='PASS_M357_COMPLETE_RUNTIME_CAPACITY' and not r['errors']
        assert r['memory_capacity_proven'] and r['load_only_capacity_pass'] and r['overlay_loaded']
        assert not r['unsafe_buffers_retained'] and r['safe_buffers_released']
        assert len(r['allocated_buffers'])==len(r['released_buffers'])==7 and r['extra_pynq_allocations']==0
        assert sorted(r['allocated_buffers'],key=lambda x:x['address'])==sorted(r['released_buffers'],key=lambda x:x['address'])
        assert never_submitted_release(r['final_snapshot'],0,0,[],7)
        assert never_submitted_release(r['stable_restore_snapshot'],0,0,[],7)
        assert r['stable_overlay_reloaded'] and not r['stable_restore_transaction_submitted']
        assert r['stable_bit_sha256']=='1cbf7bbb86cfe64c2349418d5a15890d735bea3fa4c999060c8a9da9ac3206ac'
        for key in ('loaded_capacity','settled_capacity'):
            x=r[key];assert x['required_cma_bytes']==x['required_mem_available_bytes']==64<<20
            assert x['meets_threshold'] and x['cma_free_bytes']>=64<<20 and x['mem_available_bytes']>=64<<20
        assert r['boot_unchanged'] and r['cmdline_unchanged'] and r['elapsed_s_diagnostic_not_performance']<=600
    else:
        assert r['errors'] and not r['memory_capacity_proven']

def decode(text):
    hashes=re.findall(r'(?m)^M358_RESULT_SHA256=([0-9a-f]{64})\s*$',text)
    codes=re.findall(r'(?m)^M358_SAVED_GATE_RC=([01])\s*$',text)
    chunks=re.findall(r'(?m)^M358_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    assert len(hashes)==len(codes)==1 and chunks and len(chunks)==int(chunks[0][1])
    parts=[]
    for i,(index,total,value) in enumerate(chunks):
        assert int(index)==i and int(total)==len(chunks)
        part=base64.b64decode(value,validate=True);assert 0<len(part)<=1800;parts.append(part)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest();assert digest==hashes[0]
    r=json.loads(raw);validate(r);assert int(codes[0])==r['gate_return_code']
    done=re.findall(r'M358_DONE gate_rc=(\d+) export_rc=(\d+)',text)
    if done:assert len(done)==1 and done[0]==(codes[0],'0')
    return digest,raw,r

def selftest():
    snap=dict(ap_ctrl=4,ap_return=0,mm2s_dmasr=0,s2mm_dmasr=0,mm2s_error=False,s2mm_error=False,kernel_read_error='',return_read_error='',dma_read_error='')
    good=dict(build_id='0x4D333537',gate_level='load-only-memory-diagnostic',prior_board_sha256=PRIOR,manifest_sha256=MANIFEST,gate_return_code=0,status='PASS_M357_COMPLETE_RUNTIME_CAPACITY',errors=[],host_calls=0,logical_calls=0,blocked_inference_attempts=[],ps_slot={},memory_capacity_proven=True,load_only_capacity_pass=True,overlay_loaded=True,unsafe_buffers_retained=False,safe_buffers_released=True,allocated_buffers=[dict(address=i) for i in range(7)],released_buffers=[dict(address=i) for i in range(7)],extra_pynq_allocations=0,final_snapshot=snap,stable_restore_snapshot=snap,stable_overlay_reloaded=True,stable_restore_transaction_submitted=False,stable_bit_sha256='1cbf7bbb86cfe64c2349418d5a15890d735bea3fa4c999060c8a9da9ac3206ac',boot_unchanged=True,cmdline_unchanged=True,elapsed_s_diagnostic_not_performance=1)
    for k in ('numerical_pass','performance_pass','formal_promotion_allowed','worker_started','model_forward_calls','fpga_transactions','serving_after_vision_capacity_proven'):good[k]=False
    for k in ('loaded_capacity','settled_capacity'):good[k]=dict(required_cma_bytes=64<<20,required_mem_available_bytes=64<<20,meets_threshold=True,cma_free_bytes=64<<20,mem_available_bytes=64<<20)
    def exported(r):
        raw=w.encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M358_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM358_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M358_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode()+'\n' for i,p in enumerate(parts))+f'M358_DONE gate_rc={r["gate_return_code"]} export_rc=0\n'
    assert decode(exported(good))[2]==good
    fail=dict(good,status='FAIL_M357_COMPLETE_RUNTIME_CAPACITY',gate_return_code=1,errors=['Insufficient runtime reserve'],memory_capacity_proven=False)
    assert decode(exported(fail))[2]==fail
    bads=[exported(good).replace('M358_RESULT_CHUNK=1/','M358_RESULT_CHUNK=0/'),exported(good).replace('export_rc=0','export_rc=1'),exported(good)+'M358_RESULT_SHA256='+'0'*64+'\n']
    for k,v in [('fpga_transactions',1),('blocked_inference_attempts',['forward']),('extra_pynq_allocations',1),('host_calls',1),('ps_slot',{'bytes':1}),('safe_buffers_released',False),('stable_overlay_reloaded',False),('released_buffers',[]),('elapsed_s_diagnostic_not_performance',601),('stable_restore_snapshot',dict(snap,mm2s_dmasr=4098)),('loaded_capacity',dict(good['loaded_capacity'],cma_free_bytes=(64<<20)-1)),('settled_capacity',dict(good['settled_capacity'],required_cma_bytes=1))]:bads.append(exported(dict(good,**{k:v})))
    for bad in bads:
        try:decode(bad)
        except (AssertionError,ValueError):pass
        else:raise AssertionError('Invalid capacity result accepted')
    return len(bads)

def collect(log):
    digest,raw,r=decode(log.read_text(encoding='utf-8-sig'))
    out=w.BASE/'runs/M358-candidate-capacity-board-01/BOARD_RESULT.json'
    w.atomic(out,raw,immutable=True)
    w.atomic(out.parent/'COLLECTION.json',w.encoded(dict(raw_sha256=digest,log_sha256=w.sha(log),original_bytes=True,reexecuted=False)),immutable=True)
    w.sync('latest_m358_candidate_capacity_board',dict(status=r['status'],sha256=digest,result=out.relative_to(w.ROOT).as_posix()),f'## M358 新电路完整runtime容量裁决\n\nBuild0x4D333537，原始rc{r["gate_return_code"]}，{r["status"]}。0模型forward/FPGA事务；无额外bank/PSslot；运行时余量门槛各64MiB保持。原字节SHA `{digest}`；仅容量级，不解锁完整请求性能。')
    print(r['status'],digest)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--selftest',action='store_true');p.add_argument('log',nargs='?',type=Path);a=p.parse_args()
    if a.selftest:print('M358_COLLECTION_SELFTEST_PASS',selftest())
    else:collect(a.log)
