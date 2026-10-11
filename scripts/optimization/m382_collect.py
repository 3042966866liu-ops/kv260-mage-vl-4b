"""Strict existing byte collection; no hardware or probe imports/execution."""
import base64,hashlib,json,re,sys
from pathlib import Path
import m351_workflow as w
PKG=w.BASE/'candidates/M382-sealed-ps-slot-01'
SHAPES=[6963200]*4+[389152,2621440,2621440]
def require(value,message):
    if not value:raise ValueError(message)
def never_submitted(s):
    require(all(s[k]==v for k,v in dict(ap_ctrl=4,ap_return=0,mm2s_dmasr=0,s2mm_dmasr=0,mm2s_error=False,s2mm_error=False,kernel_read_error='',return_read_error='',dma_read_error='').items()),'Never-submitted snapshot differs')
def decode(log):
    hashes=re.findall(r'(?m)^M382_RESULT_SHA256=([0-9a-f]{64})\s*$',log)
    codes=re.findall(r'(?m)^M382_SAVED_GATE_RC=([01])\s*$',log)
    chunks=re.findall(r'(?m)^M382_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',log)
    require(len(hashes)==len(codes)==1 and chunks and len(chunks)==int(chunks[0][1]),'Incomplete/duplicate raw')
    parts=[]
    for i,(index,total,value) in enumerate(chunks):
        b=base64.b64decode(value,validate=True)
        require(int(index)==i and int(total)==len(chunks) and 0<len(b)<=900,'Order/size differs');parts.append(b)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest();r=json.loads(raw)
    require(digest==hashes[0] and type(r['gate_return_code']) is int and r['gate_return_code']==int(codes[0]),'Raw SHA/rc differs')
    require(r['manifest_sha256']==w.sha(PKG/'PACKAGE_MANIFEST.json') and r['case']=='B1' and r['build_id']=='0x4D333537' and r['gate_level']=='sealed-DMA-load-only-PS-slot-diagnostic','Package/scope differs')
    require(not any(r[k] for k in ('memory_capacity_proven','numerical_pass','performance_pass','formal_promotion_allowed','serving_after_vision_capacity_proven','model_forward_calls','fpga_transactions','worker_started')),'Incorrect evidence scope')
    done=re.findall(r'M382_DONE case=B1 gate_rc=(\d+) export_rc=(\d+)',log)
    require(not done or done==[(codes[0],'0')],'Gate/export rc differs')
    if r['status']=='PASS_M382_SEALED_LOAD_ONLY_PS_SLOT':
        require(not r['gate_return_code'] and not r['errors'] and not r['unsafe_buffers_retained'],'Incomplete PASS')
        require([x['bytes'] for x in r['allocated_buffers']]==SHAPES and r['released_buffers']==list(reversed(r['allocated_buffers'])) and r['original_buffer_release_count']==7,'Seven original DMA release differs')
        require(not r['blocked_inference_attempts'] and r['host_calls']==r['logical_calls']==r['extra_pynq_allocations']==0 and not r['ps_prefetch_enabled'] and not r['additional_cma_requests_allowed'],'Unexpected inference/allocation')
        for k in ('safe_buffers_released','ps_slot_released','allocator_sealed','resident_before_slot','resident_after_slot_release','load_only_slot_pass','patch_registry_cleared','stable_overlay_reloaded','boot_unchanged','cmdline_unchanged','tokenizer_single_parse_reused'):
            require(r[k] is True,'Required lifecycle proof absent: '+k)
        require(not r['stable_restore_transaction_submitted'] and r['stable_bit_sha256']=='1cbf7bbb86cfe64c2349418d5a15890d735bea3fa4c999060c8a9da9ac3206ac','Stable rollback differs')
        require(r['ps_slot_port_count_before_release']==0 and r['elapsed_s_diagnostic_not_performance']<=600,'Resource or budget differs')
        never_submitted(r['loaded_snapshot']);never_submitted(r['final_snapshot'])
        require(r['sampled_memory']['observer_stopped'] and not r['sampled_memory']['stop_reason'],'Parent observer differs')
        p=r['ps_slot']
        require(p['slot_bytes']==27852800 and p['ordinary_bytearray_ports']==4 and p['budget_growth_bytes']==p['available_margin_bytes']==64<<20,'PS geometry/budget differs')
        require(type(p['page_bytes']) is int and p['page_bytes']>0 and len(p['ports'])==4,'Touch coverage absent')
        require(p['ports']==[dict(port=i,bytes=6963200,touched_pages=(6963200+p['page_bytes']-1)//p['page_bytes'],last_byte_touched=True,readback=True) for i in range(4)],'Page readback differs')
        require(p['observer_stopped'] and p['objects_released'] and p['load_only_slot_pass'] and not p['worker_started'] and not p['exact_native_peak_proven'] and not p['rss_return_to_baseline_required'],'PS lifecycle proof differs')
        require(p['release']==dict(released_ports=4,bytearrays_sole_owned_before_release=True,all_owner_weakrefs_dead=True,explicit_gc_or_trim=False),'Sole-owner release proof differs')
        require(p['sampled_memory']['sample_count']>0 and not p['sampled_memory']['stop_reason'],'Actual observation absent')
        baseline=p['baseline_before_slot']['process_bytes']['VmRSS'];initial=p['initial_cma_counts']
        names=['PS-slot:before-allocation-complete-runtime-retained']
        for i in range(4):names += ['PS-slot:before-port-'+str(i),'PS-slot:after-allocation-port-'+str(i),'PS-slot:after-touch-readback-port-'+str(i)]
        names += ['PS-slot:all-four-touched-runtime-retained','PS-slot:all-four-retained-after-settle']
        require([x['name'] for x in p['checkpoints']]==names and bool(initial),'Checkpoint coverage differs')
        for row in p['checkpoints']:
            require(row['retained_identity'] and row['cma_counts']==initial,'Resident/counters changed')
            m=row['memory'];d=row['decision'];s=m['system_bytes'];rss=m['process_bytes']['VmRSS'];growth=max(0,rss-baseline)
            require(growth<=64<<20 and s['MemAvailable']>=max(0,(64<<20)-growth)+(64<<20),'Actual ordinary memory budget exceeded')
            require(d==dict(observed_rss_growth_bytes=growth,required_available_bytes=max(0,(64<<20)-growth)+(64<<20),cma_free_bytes=s['CmaFree'],mem_available_bytes=s['MemAvailable'],production64MiB_would_admit=s['CmaFree']>=64<<20,additional_explicit_cma_requests=0),'Actual decision differs')
        for k in ('after_release_runtime_retained','after_release_settled_runtime_retained'):
            m=p[k];growth=max(0,m['process_bytes']['VmRSS']-baseline)
            require(growth<=64<<20 and m['system_bytes']['MemAvailable']>=max(0,(64<<20)-growth)+(64<<20),'Post-release budget exceeded')
        require('original_error' not in p,'Original probe failure cannot be PASS')
    else:
        require(r['gate_return_code']==1 and bool(r['errors']),'Invalid failure')
    return digest,raw,r
def collect(path):
    digest,raw,r=decode(Path(path).read_text(encoding='utf-8-sig'));out=w.BASE/'runs/M382-sealed-ps-slot-board-01'
    w.atomic(out/'BOARD_RESULT.json',raw,immutable=True)
    w.sync('latest_m382_sealed_ps_slot_board',dict(status=r['status'],result=(out/'BOARD_RESULT.json').relative_to(w.ROOT).as_posix(),sha256=digest,load_only_slot_pass=r.get('load_only_slot_pass',False),memory_capacity_proven=False,numerical_pass=False,performance_pass=False),f'## M382 完整runtime驻留＋封锁新增DMA的PS slot板端诊断（2026-10-03）\n\nBuild0x4D333537，裁决{r["status"]}，原rc{r["gate_return_code"]}；原字节 SHA {digest}。完整runtime＋七DMA，普通slot27,852,800B，0forward/事务/预读worker/额外PYNQ申请；记录实际触页/20ms内存及sole-owner/weakref释放，不要求RSS回落。生产64MiB不改，本次仅独立load-only条件；非视频峰值、数值或性能证明。下一步只离线裁决生命周期/内存；失败停止扩大，通过同步后才准备预读descriptor/chain绑定。')
    print(json.dumps(dict(status=r['status'],raw_sha256=digest,errors=r['errors'],slot=r.get('ps_slot'),production_admission=r.get('production_threshold_would_admit')),ensure_ascii=True))
if __name__=='__main__':collect(sys.argv[1])
