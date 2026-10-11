"""Strict complete-visual performance recovery; no board/model execution."""
import base64,collections,hashlib,json,math,re
from pathlib import Path
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
from m425_warm import WarmSequence,adjudicate,ORDER
PKG=BASE/'candidates/M430-late11-visual-warm-02'
OUT=BASE/'runs/M430-complete-visual-warm-board-01/BOARD_RESULT.json'
def score(samples):
    r=adjudicate(samples);r['scope']='Fixed-input controlled warm complete visual only; no language or production promotion.'
    reliable=r['performance_pass'];worthwhile=reliable and r['gain_percent']>=5.
    r.update(reliable_positive_gain=reliable,worthwhile_complete_visual_gain_percent_minimum=5.,performance_pass=worthwhile,status='PASS_WORTHWHILE_COMPLETE_VISUAL_GAIN' if worthwhile else 'CLOSE_NO_WORTHWHILE_RELIABLE_COMPLETE_VISUAL_GAIN')
    return r
def complete(snapshot,build):
    from board_safety import safe_to_release
    return safe_to_release(snapshot) and type(snapshot.get('ap_return')) is int and snapshot['ap_return']==build and all(snapshot.get(k) is False for k in ('mm2s_error','s2mm_error')) and all(snapshot.get(k)=='' for k in ('kernel_read_error','return_read_error','dma_read_error'))
def check(r):
    plan=json.loads((PKG/'PLAN.json').read_bytes());protocol=json.loads((PKG/'PROTOCOL.json').read_bytes())
    if r['gate_level']!='late11-complete-visual-controlled-warm-performance' or r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or type(r['gate_return_code']) is not int or r['gate_return_code'] not in (0,1) or r['selected_layers']!=list(range(13,24)):raise ValueError('Gate/manifest/range differs')
    if any(r.get(k) not in (False,0) for k in ('temperature_measurement_enabled','formal_promotion_allowed','language_forward_calls')):raise ValueError('Forbidden scope')
    if r['status'] in ('FAIL_M430_COMPLETE_VISUAL_WARM','FAIL_UNSAFE_RETAINED'):
        if r['gate_return_code']!=1 or not r['errors'] or r['numerical_hardware_proven']:raise ValueError('Failure evidence incomplete')
        return r
    if r['status']!='PASS_M430_COMPLETE_VISUAL_WARM_COLLECTED' or r['gate_return_code'] or r['errors'] or r['build_id']!='0x4D333537':raise ValueError('Complete visual status differs')
    for k in ('overlay_loaded','safe_buffers_released','stable_restored','DMA_allocator_restored','DMA_sealed_after_main','original_reference_pass','saved_original_all24_boundaries_verified','CPU_component_before_Overlay','bindings_restored','visual_owner_closed','feature_screen_pass','numerical_hardware_proven','boot_unchanged','cmdline_unchanged','warm_conditions_established'):
        if r.get(k) is not True:raise ValueError('Incomplete lifecycle/identity '+k)
    if r['unsafe_dma_buffers_retained'] or r['unexpected_DMA_requests'] or r['visual_forward_calls']!=12 or r['original_visual_forward_calls']!=6 or r['physical_transactions_started']!=1718 or r['fpga_transactions']!=1718:raise ValueError('Actual sample/transaction count differs')
    if r['numerical_source_sha256']!=plan['numerical_result_sha256'] or r['warm_protocol_sha256']!=sha(PKG/'PROTOCOL.json') or r['source_identities_verified']!=49:raise ValueError('Prerequisite/source differs')
    numeric=json.loads((BASE/'runs/M429-late11-visual-PL-board-02/BOARD_RESULT.json').read_bytes());soft=json.loads((BASE/'runs/M427-half-software-board-01/BOARD_RESULT.json').read_bytes());refs=next(x for x in soft['ranges'] if x['name']=='late_13_23')['reference_batches']
    if r['backend_before']!=r['backend_after'] or r['targets']!=numeric['targets'] or r['prefix_topology']!=numeric['prefix_topology'] or r['preprocessed']!=numeric['preprocessed'] or r['candidate_visual']!=numeric['candidate_visual'] or r['original_visual']!=numeric['original_visual']:raise ValueError('Input/backend/full features differ')
    comp=r['component']
    if comp['complete_wire_batches']!=286 or len(comp['negative_checks'])!=20 or len(comp['timed_light_negative_checks'])!=8 or not comp['restored'] or not comp['fake_PL_submit']:raise ValueError('Timed actual fixture absent')
    samples=r['warmup_samples']+r['formal_samples']
    if len(samples)!=12 or ''.join(s['variant'] for s in samples)!=ORDER or r['warm_sequence']!=ORDER:raise ValueError('Fixed twelve visual samples required')
    recovered={};seq=WarmSequence(recovered,r['reference_environment'],clock=lambda:0.,protocol_sha=plan['protocol_sha256'])
    total_rows=0
    for i,s in enumerate(samples):
        seq.before(i);seq.record(dict(s))
        if s['index']!=i+1 or not s['feature_complete_exact'] or not s['bindings_restored'] or type(s['elapsed_ns']) is not int or s['elapsed_ns']/1e6!=s['timing']['total_ms']:raise ValueError('Measured interval/result incomplete')
        if s['feature']!=numeric['original_visual' if s['variant']=='A' else 'candidate_visual']:raise ValueError('Post-timer complete feature differs')
        if s['physical_calls']!=(0 if s['variant']=='A' else 286):raise ValueError('Per-sample transaction count differs')
        for side in ('before_memory','after_memory'):
            if s[side]['MemAvailable']<64<<20 or not all(type(s[side][k]) is int and s[side][k]>=0 for k in ('VmRSS','CmaFree','MemAvailable')):raise ValueError('Sample memory reserve invalid')
        if s['variant']=='A':
            if s['PL_batches'] or s['staging_rows'] or s['device_wait_ns'] or s['staging_ns']:raise ValueError('A unexpectedly uses PL')
        else:
            if set(s['PL_batches'])!=set(map(str,range(13,24))) or len(s['staging_rows'])!=22:raise ValueError('All11 PL MLPs required')
            if [(x['layer'],x['part'],x['bytes']) for x in s['staging_rows']]!=[(i,p,4*557056) for i in range(13,24) for p in ('fc1','fc2')]:raise ValueError('Original staging geometry/order differs')
            if s['staging_ns']!=sum(x['elapsed_ns'] for x in s['staging_rows']):raise ValueError('Light stage timer sum differs')
            rows=r['PL_rows'][total_rows:total_rows+286];total_rows+=286
            if s['device_wait_ns']!=sum(x['wait_ns'] for x in rows):raise ValueError('Light wait timer sum differs')
            index=0
            for layer in range(13,24):
                if set(s['PL_batches'][str(layer)])!={'fc1','fc2'}:raise ValueError('Both MLP Linears required')
                for part in ('fc1','fc2'):
                    batches=s['PL_batches'][str(layer)][part]
                    if len(batches)!=13:raise ValueError('Original T32 partition differs')
                    for batch,ref in zip(batches,refs[str(layer)][part]):
                        expected={k:ref[k] for k in ('start','rows','initial_shift','attempted_shifts','selected_shift')}|{'physical_calls':1}
                        if batch!=expected:raise ValueError('Saved shifts/retry contract differs')
                        row=rows[index];index+=1
                        if {k:row[k] for k in ('layer','part','start','shift','input_bytes','output_bytes')}!=dict(layer=layer,part=part,start=ref['start'],shift=ref['selected_shift'],input_bytes=ref['input_bytes'],output_bytes=ref['output_bytes']) or not complete(row['completed_snapshot'],0x4D333537) or type(row['wait_ns']) is not int or row['wait_ns']<0:raise ValueError('Actual complete DMA transaction differs')
                        if 'packet_sha256' in row or 'raw_sha256' in row:raise ValueError('Heavy per-wire hash still timed')
    if total_rows!=1716 or len(r['PL_rows'])!=1716 or len(r['staging'])!=132:raise ValueError('All timed PL/staging records required')
    expected=score(r['formal_samples'])
    if r['performance_adjudication']!=expected or r['performance_pass'] is not expected['performance_pass']:raise ValueError('Prespecified statistical decision differs')
    if r['retained_features'] or r.get('experiment_stop') or r['matched_wire_batches_reused']!=286:raise ValueError('Timed scope/historical evidence differs')
    if len(r['transactions'])!=2:raise ValueError('Candidate and stable legal minimum required')
    for tx,label,build in zip(r['transactions'],('candidate-legal-build-id','stable-restored-build-id'),(0x4D333537,0x4D395832)):
        if tx['label']!=label or not tx['full_output_exact'] or not complete(tx['completed_snapshot'],build):raise ValueError('Legal build/restore completion differs')
    sizes=([144]*4+[2576,4096],plan['main_DMA_sizes'],[144]*4+[2576,4096])
    if r['dma_allocations']!=19 or len(r['allocations'])!=19 or len(r['releases'])!=19 or [x['bytes'] for x in r['allocations']]!=sum((list(s) for s in sizes),[]):raise ValueError('Exact owner allocation plan differs')
    ledger=lambda rows:collections.Counter((x['label'],x['bytes'],x['address']) for x in rows)
    if ledger(r['allocations'])!=ledger(r['releases']) or not complete(r['final_snapshot'],0x4D395832):raise ValueError('Owner release/final state incomplete')
    if r['DMA_admission_groups']!=numeric['DMA_admission_groups'] or r['elapsed_s_diagnostic_not_performance']>2400:raise ValueError('Sealed allocator/budget differs')
    return r
def decode(log):
    hashes=re.findall(r'(?m)^M430_RESULT_SHA256=([0-9a-f]{64})\s*$',log);codes=re.findall(r'(?m)^M430_SAVED_GATE_RC=([01])\s*$',log);chunks=re.findall(r'(?m)^M430_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',log)
    if len(hashes)!=1 or len(codes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Exact saved export receipt required')
    parts=[]
    for i,(index,total,data) in enumerate(chunks):
        b=base64.b64decode(data,validate=True)
        if int(index)!=i or int(total)!=len(chunks) or not 0<len(b)<=900:raise ValueError('Chunk order/size differs')
        parts.append(b)
    raw=b''.join(parts)
    if not 0<len(raw)<=2<<20 or hashlib.sha256(raw).hexdigest()!=hashes[0]:raise ValueError('Whole SHA/budget differs')
    r=check(json.loads(raw))
    if r['gate_return_code']!=int(codes[0]):raise ValueError('Original rc differs')
    done=re.findall(r'M430_DONE gate_rc=(\d+) export_rc=(\d+)',log)
    if done and done!=[(codes[0],'0')]:raise ValueError('Gate/export original rc differs')
    return hashes[0],raw,r,len(chunks)
def collect(log):
    digest,raw,r,count=decode((ROOT/log).read_text(encoding='utf-8-sig'));atomic(OUT,raw,immutable=True)
    sync('latest_m430_complete_visual_board',dict(status=r['status'],result=OUT.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256'],performance_pass=r['performance_pass'],full_request_timing_unlocked=False,temperature_measurement_enabled=False),f'## M430 完整视觉暖态原结果（2026-10-06）\n\nSHA {digest}，{count}块≤900B原字节严格回收，rc{r["gate_return_code"]}，{r["status"]}。仅固定12视觉、0语言，不测温；原样保存预热/正式条件、计时及原裁决。需独立闭合后判断完整视觉收益，未接生产。')
    print('M430_VISUAL_BOARD_SYNC',digest,r['status'])
def transfer():
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes());folder=ROOT/'tmp/m43003';rows=[]
    for name in ['PACKAGE_MANIFEST.json']+[x['path'] for x in m['files']]:
        p=PKG/name;size=p.stat().st_size;prefix='upload_'+name.replace('.','_');count=(size+899)//900
        if sha(p) not in (folder/(prefix+'_final.log')).read_text(encoding='utf-8-sig'):raise ValueError('Whole transfer SHA absent')
        logs=sorted(folder.glob(prefix+'_chunk_*.log'))
        if len(logs)!=count:raise ValueError('Transfer ordinal count differs')
        for i,log in enumerate(logs,1):
            if not re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,size))+r'\s',log.read_text(encoding='utf-8-sig')):raise ValueError('Transfer ordinal/bytes differs')
        rows.append(dict(path=name,sha256=sha(p),chunks=count))
    if '__M430_SYNTAX_RC_0__' not in (folder/'syntax.log').read_text(encoding='utf-8-sig'):raise ValueError('Board bash-n absent')
    r=dict(status='PASS_M430_MANIFEST_FIRST_HASHED_TRANSFER',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),receipts=rows,hardware_gate_started=False);out=BASE/'runs/M430-complete-visual-transfer-01/RESULT.json';atomic(out,encoded(r),immutable=True)
    sync('latest_m430_complete_visual_transfer',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=r['manifest_sha256']),f'## M430 完整视觉计时包传输（2026-10-06）\n\nSHA {sha(out)}，manifest-first900B全部回执/逐文件整SHA及bash-n通过，尚未开始样本；不测温。')
    print('M430_TRANSFER_SYNC',sha(out))
if __name__=='__main__':
    import sys
    if sys.argv[1:]==['transfer']:transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':collect(sys.argv[2])
    else:raise SystemExit('transfer | collect LOG')
