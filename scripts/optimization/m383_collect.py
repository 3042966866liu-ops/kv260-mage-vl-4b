"""Strict saved-byte recovery for one descriptor; never executes hardware."""
import base64,hashlib,json,re,sys
from pathlib import Path
import m351_workflow as w
from board_safety import safe_to_release
from m382_collect import require
PKG=w.BASE/'candidates/M383-ps-descriptor-01'
def decode(log):
    hashes=re.findall(r'(?m)^M383_RESULT_SHA256=([0-9a-f]{64})\s*$',log)
    codes=re.findall(r'(?m)^M383_SAVED_GATE_RC=([01])\s*$',log)
    chunks=re.findall(r'(?m)^M383_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',log)
    require(len(hashes)==len(codes)==1 and chunks and len(chunks)==int(chunks[0][1]),'Incomplete/duplicate raw')
    parts=[]
    for i,(index,total,data) in enumerate(chunks):
        b=base64.b64decode(data,validate=True)
        require(int(index)==i and int(total)==len(chunks) and 0<len(b)<=900,'Chunk order/size differs');parts.append(b)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest();r=json.loads(raw)
    require(digest==hashes[0] and type(r['gate_return_code']) is int and r['gate_return_code']==int(codes[0]),'SHA/rc differs')
    require(r['manifest_sha256']==w.sha(PKG/'PACKAGE_MANIFEST.json') and r['gate_level']=='sealed-DMA-PS-single-descriptor-numerical' and r['case']=='B1' and r['build_id']=='0x4D333537','Wrong package/scope')
    require(not any(r[k] for k in ('memory_capacity_proven','performance_pass','formal_promotion_allowed','serving_after_vision_capacity_proven','model_forward_calls')),'Scope improperly promoted')
    done=re.findall(r'M383_DONE case=B1 gate_rc=(\d+) export_rc=(\d+)',log)
    require(not done or done==[(codes[0],'0')],'Gate/export rc differs')
    if r['status']=='PASS_M383_PS_DESCRIPTOR_NUMERICAL':
        require(not r['gate_return_code'] and not r['errors'] and not r['unsafe_buffers_retained'] and r['safe_buffers_released'] and r['numerical_pass'],'Incomplete PASS')
        require([x['bytes'] for x in r['allocated_buffers']]==[6963200]*4+[389152,2621440,2621440] and r['released_buffers']==list(reversed(r['allocated_buffers'])) and r['original_buffer_release_count']==7,'DMA lifetime differs')
        require(r['host_calls']==r['logical_calls']==r['extra_pynq_allocations']==0 and not r['blocked_inference_attempts'] and r['fpga_transactions']==3 and len(r['transactions'])==2,'Raw descriptor coverage differs')
        require(r['slot_prerequisite_sha256']=='178a914e34cf0cb9a74b19853b01ee5f7fd549059b9b7a9a42cc3827332d7a5a' and r['original_parser_workers']==1 and r['stage_pair_bytes']==2949120,'Prerequisite/parser/stage differs')
        require(r['ps_prefetch_enabled'] and r['worker_started'] and r['session_weakref_dead'] and r['patch_registry_cleared'],'PS worker/owner proof absent')
        require(r['same_overlay_minimal_proof']['full_output_exact'] and r['same_overlay_minimal_proof']['output_bytes']==4096,'Minimum proof absent')
        for key in ('baseline_descriptor','candidate_descriptor'):
            row=r[key]
            require(row['packet_sha256']=='97d1b37537669c003146b4d6c1bc3c338e5af5e47ef442c3b85fb1b84eb8d629' and row['output_sha256']=='60f403730b76a4860412c9e8865447404c822d0d8347301327ff222b7b21e859' and row['output_bytes']==262144 and row['full_output_exact'] and len(row['weight_sha256'])==4,'Descriptor raw reference differs')
            require(safe_to_release(row['snapshot']) and row['snapshot']['ap_return']==0x4d333537,'Completion differs')
        require(r['baseline_descriptor']['weight_sha256']==r['candidate_descriptor']['weight_sha256'],'Staged weights differ')
        p=r['ps_session'];c=p['component']
        require(not p['production_policy_changed'] and not p['additional_dma_allocations'] and p['source_component_unchanged'],'Production scope differs')
        require(all(c[k]==v for k,v in dict(status='COMPLETE_COMPONENT_ONLY',stages=1,submissions=1,ps_payload_bytes=27852800,extra_cma_allocation_calls=0,total_weight_bytes=1474560,open_files=0,live_views=0,performance_pass=False,hardware_contract_changed=False).items()),'PS plan/lifetime differs')
        require(p['slot_release']==dict(released_ports=4,bytearrays_sole_owned_before_release=True,all_owner_weakrefs_dead=True,explicit_gc_or_trim=False),'Slot release proof differs')
        require(len(p['independent_memory_checks'])>=5,'Memory coverage absent')
        counts=p['independent_memory_checks'][0]['cma_counts'];baselines=set()
        for row in p['independent_memory_checks']:
            d=row['decision'];s=row['memory']['system_bytes'];growth=d['observed_rss_growth_bytes']
            require(row['cma_counts']==counts and bool(counts) and 0<=growth<=64<<20 and s['MemAvailable']>=max(0,(64<<20)-growth)+(64<<20),'Actual memory/counters differ')
            require(d['cma_free_bytes']==s['CmaFree'] and d['mem_available_bytes']==s['MemAvailable'] and d['required_available_bytes']==max(0,(64<<20)-growth)+(64<<20) and d['production64MiB_would_admit']==(s['CmaFree']>=64<<20) and not d['additional_explicit_cma_requests'],'Actual admission differs')
            if growth:baselines.add(row['memory']['process_bytes']['VmRSS']-growth)
        require(len(baselines)<=1,'Baseline inconsistent')
        if baselines:
            base=next(iter(baselines))
            require(all(max(0,x['memory']['process_bytes']['VmRSS']-base)==x['decision']['observed_rss_growth_bytes'] for x in p['independent_memory_checks']),'Growth inconsistent')
        require(safe_to_release(r['final_snapshot']) and r['final_snapshot']['ap_return']==0x4d333537 and r['sampled_memory']['observer_stopped'] and not r['sampled_memory']['stop_reason'],'Final completion/observer differs')
        require(all(r[k] for k in ('stable_overlay_reloaded','boot_unchanged','cmdline_unchanged','tokenizer_single_parse_reused')) and r['elapsed_s_diagnostic_not_performance']<=600,'Restore/budget differs')
    else:require(r['gate_return_code']==1 and r['errors'],'Invalid failure')
    return digest,raw,r
def collect(path):
    digest,raw,r=decode(Path(path).read_text(encoding='utf-8-sig'));out=w.BASE/'runs/M383-ps-descriptor-board-01';w.atomic(out/'BOARD_RESULT.json',raw,immutable=True)
    w.sync('latest_m383_ps_descriptor_board',dict(status=r['status'],result=(out/'BOARD_RESULT.json').relative_to(w.ROOT).as_posix(),sha256=digest,numerical_pass=r['numerical_pass'],memory_capacity_proven=False,performance_pass=False),f'## M383 单descriptor PS暂存板端结果（2026-10-03）\n\nBuild0x4D333537，{r["status"]}，原rc{r["gate_return_code"]}，SHA {digest}。仅原固定Q第一descriptor，完整runtime/七DMA驻留；同Overlay合法最小后原暂存/PS暂存完整wire FTZ与权重字节、worker/slot/session释放核对。0新增DMA/模型forward；非链/模型/视频性能或生产准入。下一步本级裁决，通过同步后才准备代表chain；容量/生命周期问题停止扩大。')
    print(json.dumps(dict(status=r['status'],sha256=digest,errors=r['errors'],ps_session=r.get('ps_session'))))
if __name__=='__main__':collect(sys.argv[1])
