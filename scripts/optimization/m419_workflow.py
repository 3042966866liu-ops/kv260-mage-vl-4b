"""Same saved inputs; strict complete numerical/lifecycle/timing decision collection."""
import base64,hashlib,json,re
from pathlib import Path
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m411_mlp_binding import decision
from m412_policy import POLICY,MAIN_SIZES,MINIMAL_SIZES
from board_safety import safe_to_release
PKG=BASE/'candidates/M419-layer13-complete-MLP-01'
def transfer(folder=ROOT/'tmp/m41901',save=True):
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes());receipts=[]
    for name in ['PACKAGE_MANIFEST.json']+[x['path'] for x in m['files']]:
        prefix='upload_'+name.replace('.','_');p=folder/(prefix+'_final.log');t=p.read_text(encoding='utf-8-sig');size=(PKG/name).stat().st_size;count=(size+899)//900
        if 'M212_CHUNKED_FILE_PASS' not in t or sha(PKG/name) not in t:raise ValueError('Final SHA receipt missing')
        chunks=sorted(folder.glob(prefix+'_chunk_*.log'))
        if len(chunks)!=count:raise ValueError('Chunk receipt count differs')
        for i,p in enumerate(chunks,1):
            if not re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,size))+r'\s',p.read_text(encoding='utf-8-sig')):raise ValueError('Incomplete chunk receipt')
        receipts.append(dict(path=name,sha256=sha(PKG/name),chunks=count))
    if '__M419_SYNTAX_RC_0__' not in (folder/'syntax.log').read_text(encoding='utf-8-sig'):raise ValueError('Bash syntax receipt missing')
    v=dict(status='PASS_M419_MANIFEST_FIRST_TRANSFER',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),files=receipts,hardware_gate_started=False)
    if save:
        p=BASE/'runs/M419-complete-MLP-transfer-01/RESULT.json';atomic(p,encoded(v),immutable=True)
        sync('latest_m419_complete_mlp_transfer',dict(status=v['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=v['manifest_sha256']),f'## M419 完整视觉MLP包传输（2026-10-06）\n\nSHA {sha(p)}；全部manifest-first/900B回执、逐SHA和bash-n核对，只准备一个原保存输入MLP段，不重跑视觉/语言。尚未执行。')
    return v
def decode(t):
    hashes=re.findall(r'(?m)^M419_RESULT_SHA256=([0-9a-f]{64})\s*$',t);codes=re.findall(r'(?m)^M419_SAVED_GATE_RC=([01])\s*$',t);chunks=re.findall(r'(?m)^M419_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',t)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Incomplete/duplicate saved result')
    pieces=[]
    for i,(index,total,data) in enumerate(chunks):
        p=base64.b64decode(data,validate=True)
        if int(index)!=i or int(total)!=len(chunks) or not 0<len(p)<=900:raise ValueError('Chunk order/size differs')
        pieces.append(p)
    raw=b''.join(pieces);digest=hashlib.sha256(raw).hexdigest();r=json.loads(raw);rc=int(codes[0]);plan=json.loads((PKG/'PLAN.json').read_bytes())
    if digest!=hashes[0] or r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or r['gate_level']!='isolated-complete-visual-MLP' or r['build_id']!='0x4D333537' or type(r['gate_return_code']) is not int or r['gate_return_code']!=rc:raise ValueError('Raw identity/rc differs')
    if any(r[k] is not False for k in ('full_model','video','promoted','expanded_24_layers')) or r['visual_forward_calls']!=0 or r['language_forward_calls']!=0:raise ValueError('Scope expanded')
    done=re.findall(r'M419_DONE gate_rc=(\d+) export_rc=(\d+)',t)
    if done and done!=[(str(rc),'0')]:raise ValueError('Gate/export rc differs')
    if r['status'] in ('PASS_M419_COMPLETE_MLP_NET_GAIN','CLOSED_M419_COMPLETE_MLP_NO_RELIABLE_NET_GAIN'):
        if rc or r['errors'] or not all(r[k] is True for k in ('package_verified','numerical_pass','bindings_restored','PS_owner_closed','safe_buffers_released','stable_restored','boot_unchanged','cmdline_unchanged')) or r['unsafe_dma_buffers_retained']:raise ValueError('Incomplete numerical/lifecycle decision')
        if r['prior_chain_sha256']!=plan['chain_raw_sha256'] or r['source_identities_verified']!=49 or r['full_wire_reference_batches_exact']!=26 or r['local_mlp_calls']!=12:raise ValueError('Source/full numerical/count differs')
        iso=r['component_isolation']
        if not iso['separate_process'] or not iso['parent_state_unchanged'] or iso['return_code']!=0:raise ValueError('Component parent isolation differs')
        ref=json.loads((ROOT/plan['reference_result']).read_bytes())
        if r['target_resolution']!=ref['target_resolution'] or r['target_matrices']!=ref['target_matrices'] or r['quality_metrics']!=ref['quality_metrics'] or r['boundary_residual_bf16']!=ref['boundary_residual_bf16']:raise ValueError('Original input/math/quality differs')
        if r['backend_before']!=r['backend_after'] or r['release_preflight']['status']!='READY_FOR_BOARD_PREFLIGHT':raise ValueError('Backend/assets changed')
        if [x['variant'] for x in r['warmups']]!=['A','B'] or len(r['samples'])!=8:raise ValueError('Prespecified sample/warmup count differs')
        if any(x['output_exact_outside_timer'] is not True or type(x['elapsed_ns']) is not int or x['elapsed_ns']<=0 or x['read_bytes']<0 or x['rchar']<0 or x['logical_PL_calls']!=(26 if x['variant']=='B' else 0) or x['physical_PL_calls']!=(26 if x['variant']=='B' else 0) or x['staging_bytes']!=(4456448 if x['variant']=='B' else 0) for x in r['samples']+r['warmups']):raise ValueError('Timed boundary/output/staging/calls incomplete')
        if r['comparison']!=decision(r['samples']) or r['performance_pass'] is not r['comparison']['performance_pass'] or (r['status']=='PASS_M419_COMPLETE_MLP_NET_GAIN')!=r['performance_pass']:raise ValueError('Original decision inconsistent')
        if r['CPU_store_after']['uncached_decode_calls']-r['CPU_store_before']['uncached_decode_calls']!=12:raise ValueError('Original CPU restore count differs')
        if len(r['PL_rows'])!=156 or r['physical_transactions_started']!=158 or len(r['transactions'])!=2 or len(r['staging'])!=12:raise ValueError('Physical/lifecycle counts differ')
        for part in ('fc1','fc2'):
            if r['numerical_batches'][part]!=[{k:b[k] for k in ('start','rows','initial_shift','attempted_shifts','selected_shift')}|{'physical_calls':b['physical_reference_attempts']} for b in ref['reference_batches'][part]]:raise ValueError('Original numerical batching/retry differs')
        allocations=r['allocations'];expected=[];start=0
        if len(allocations)!=19:raise ValueError('Six+seven+six actual allocation count differs')
        for count in (6,7,6):expected.extend(reversed(allocations[start:start+count]));start+=count
        if expected!=r['releases'] or sum(x['bytes'] for x in allocations[6:13])!=3440656:raise ValueError('Original seven-buffer payload/release differs')
        if r.get('admission_policy')!=POLICY or r.get('DMA_allocator_restored') is not True or r.get('DMA_sealed_after_main') is not True or r.get('unexpected_DMA_requests'):raise ValueError('Independent allocation seal/policy unproven')
        groups=r['DMA_admission_groups']
        labels=['candidate-legal-build-id','completeMLP-seven','stable-restored-build-id']
        if len(groups)!=3 or [x['label'] for x in groups]!=labels:raise ValueError('Exact allocation groups differ')
        for g,sizes in zip(groups,(MINIMAL_SIZES,MAIN_SIZES,MINIMAL_SIZES)):
            if g!=dict(label=g['label'],sizes=list(sizes),attempted=len(sizes),returned=len(sizes),complete=True):raise ValueError('Incomplete planned allocation group')
        if len(r['memory'])!=161 or len(r['PS_checkpoints'])!=24:raise ValueError('Independent memory checkpoint coverage differs')
        labels=['allocated:candidate-legal-build-id','before-submit:candidate-legal-build-id','allocated:completeMLP-seven']+['MLP-before-submit']*156+['allocated:stable-restored-build-id','before-submit:stable-restored-build-id']
        if [x['label'] for x in r['memory']]!=labels or [x['recovery'] for x in r['memory']]!=[False]*159+[True]*2:raise ValueError('Actual submit/recovery checkpoint identity differs')
        ps_labels=['after-constructor','before-numerical-original','after-numerical-original','after-numerical-PL']
        for phase in ['warmup-A','warmup-B']+['timed-'+v for v in 'ABBABAAB']:ps_labels.extend(['before-'+phase,'after-'+phase])
        if [x['label'] for x in r['PS_checkpoints']]!=ps_labels or any(x['recovery'] for x in r['PS_checkpoints']):raise ValueError('Actual segment boundary checkpoint identity differs')
        for x in r['memory']+r['PS_checkpoints']:
            if x['admission_policy']!=POLICY['name'] or x['required_cma_free_bytes'] is not None or type(x['CmaFree']) is not int or x['CmaFree']<0:raise ValueError('Memory statistics/policy identity differs')
            growth=max(0,x['VmRSS']-r['memory_after_constructor']['VmRSS'])
            required=(64<<20)+(0 if x['recovery'] else max(0,(256<<20)-growth))
            if x['RSS_growth_bytes']!=growth or x['required_MemAvailable_bytes']!=required or x['MemAvailable']<required or (not x['recovery'] and growth>256<<20):raise ValueError('Actual ordinary memory budget rejected')
        if not safe_to_release(r['final_snapshot']) or r['final_snapshot']['ap_return']!=0x4d395832:raise ValueError('Stable final DMA/Build completion differs')
        if not 0<r['elapsed_s_diagnostic_not_performance']<=840:raise ValueError('Fixed gate budget differs')
    elif r['status'].startswith('FAIL_'):
        if rc!=1 or not r['errors'] or r['performance_pass']:raise ValueError('Failure lacks original errors/scope')
    else:raise ValueError('Unknown status')
    return digest,raw,r,len(chunks)
def collect(log,out=None,sync_function=sync):
    digest,raw,r,count=decode(Path(log).read_text(encoding='utf-8-sig'));out=out or BASE/'runs/M419-complete-MLP-board-01/BOARD_RESULT.json';atomic(out,raw,immutable=True)
    report=f'# M419 原保存输入完整视觉MLP段\n\n{r["status"]}；原rc {r["gate_return_code"]}，SHA {digest}。\n\n只第13层392行fc1→原GELU→fc2。独立准入按实际七块3.281265MiB分配后封锁新增DMA，256MiB普通增长预算＋64MiB普通余量；CmaFree仅统计，生产政策不改。完整段计时从第一权重读/恢复到输出可供PS使用，包括暂存/量化/pack/DMA/等待/原解析/重试/bias/GELU；哈希和数值导出在计时外。非完整视觉、语义或请求性能，未扩24层。\n\n'
    if r.get('samples'):
        report+='|次序|分支|完整段秒|磁盘读取字节|\n|---|---|---:|---:|\n'
        report+=''.join(f'|{i+1}|{x["variant"]}|{x["elapsed_ns"]/1e9:.6f}|{x["read_bytes"]}|\n' for i,x in enumerate(r['samples']))
    report+='\n'+json.dumps(r.get('comparison',r['errors']),ensure_ascii=False,indent=2)+'\n'
    atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync_function('latest_m419_complete_mlp_board',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256'],build_id=r['build_id'],numerical_pass=r.get('numerical_pass',False),performance_pass=r['performance_pass'],expanded_24_layers=False),
        f'## M419 完整视觉MLP段数值与净耗时裁决（2026-10-06）\n\n原SHA {digest}，{count}个≤900B严格回收，rc{r["gate_return_code"]}；{r["status"]}。只原第13层完整392行，0完整视觉/语言，数值通过后才原warmup+ABBABAAB8完整段，含所有准备/转换/传输/解析/GELU/bias；原输入、其他路径和稳定回滚保持。无完整请求或语义质量结论，尚未扩大24层；失败只停本级，无无限加测。')
    print('M419_RESULT_SYNC',digest,count);return r
if __name__=='__main__':
    import sys
    if sys.argv[1:]==['transfer']:transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':collect(sys.argv[2])
    else:raise SystemExit('transfer | collect LOG')
