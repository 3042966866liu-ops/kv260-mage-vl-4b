"""Strict manifest-first receipt and exact saved-reference byte collection."""
import base64
import hashlib
import json
from pathlib import Path
import re
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
PKG=BASE/'candidates/M417-layer13-saved-reference-01'

def transfer(folder=ROOT/'tmp/m41701',save=True):
    manifest=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes());receipts=[]
    for name in ['PACKAGE_MANIFEST.json']+[r['path'] for r in manifest['files']]:
        prefix='upload_'+name.replace('.','_');final=folder/(prefix+'_final.log');t=final.read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in t or sha(PKG/name) not in t:raise RuntimeError('Final file receipt differs')
        size=(PKG/name).stat().st_size;count=(size+899)//900
        chunks=sorted(folder.glob(prefix+'_chunk_*.log'))
        if len(chunks)!=count:raise RuntimeError('Transfer count differs')
        for i,p in enumerate(chunks,1):
            if not re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,size))+r'\s',p.read_text(encoding='utf-8-sig')):raise RuntimeError('Chunk receipt differs')
        receipts.append(dict(path=name,sha256=sha(PKG/name),chunks=count,receipt_sha256=sha(final)))
    syntax=folder/'syntax.log'
    if '__M417_SYNTAX_RC_0__' not in syntax.read_text(encoding='utf-8-sig'):raise RuntimeError('Runner syntax missing')
    value=dict(status='PASS_M417_MANIFEST_FIRST_TRANSFER',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),files=receipts,syntax_sha256=sha(syntax),model_or_reference_started=False)
    if save:
        out=BASE/'runs/M417-layer13-reference-transfer-01/RESULT.json';atomic(out,encoded(value),immutable=True)
        sync('latest_m417_reference_transfer',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=value['manifest_sha256']),
            f'## M417 已保存输入参考传输（2026-10-06）\n\nSHA {sha(out)}；manifest-first/900B全部回执、完整SHA和bash-n通过。下一步仅一次PS精确参考，无新视觉捕获/Overlay/DMA/语言；尚未执行。')
    return value

def decode(t):
    hashes=re.findall(r'(?m)^M417_RESULT_SHA256=([0-9a-f]{64})\s*$',t)
    chunks=re.findall(r'(?m)^M417_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',t)
    if len(hashes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Missing/duplicate result')
    parts=[]
    for i,(idx,total,data) in enumerate(chunks):
        part=base64.b64decode(data,validate=True)
        if int(idx)!=i or int(total)!=len(chunks) or not 0<len(part)<=900:raise ValueError('Chunk order/size differs')
        parts.append(part)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest()
    if digest!=hashes[0]:raise ValueError('Original byte SHA differs')
    r=json.loads(raw)
    if r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or r['gate_level']!='PS-only-saved-input-exact-MLP-FTZ-reference' or r['selected_layer']!=13:raise ValueError('Gate identity differs')
    for k in ('overlay_loaded','semantic_quality_proven','PL_hardware_proven','performance_pass','formal_promotion_allowed'):
        if r[k] is not False:raise ValueError('Scope changed')
    for k in ('dma_allocations','fpga_transactions','visual_forward_calls','language_forward_calls'):
        if type(r[k]) is not int or r[k]!=0:raise ValueError('Unexpected transactions')
    if type(r['gate_return_code']) is not int or r['gate_return_code'] not in (0,1):raise ValueError('Invalid original rc')
    done=re.findall(r'M417_DONE gate_rc=(\d+) export_rc=(\d+)',t)
    if done and done!=[(str(r['gate_return_code']),'0')]:raise ValueError('Gate/export code differs')
    if r['status']=='PASS_M417_SAVED_MLP_EXACT_SOFTWARE_REFERENCE':
        if r['gate_return_code'] or r['errors'] or r['local_mlp_forward_calls']!=2 or r['logical_reference_calls']!=26:raise ValueError('Incomplete PASS call count')
        for k in ('original_replay_bit_exact','local_exact_arithmetic_screen_pass','bindings_restored','visual_owner_closed','no_pynq_import'):
            if r[k] is not True:raise ValueError('Numerical/lifecycle incomplete')
        expected=json.loads((PKG/'M416_CAPTURE_EXPECTED.json').read_bytes())
        if r['capture_manifest_sha256']!=expected['capture_manifest']['sha256'] or r['capture_source_raw_sha256']!=expected['raw_sha256'] or r['capture_tensors']!=expected['capture'] or r['target_matrices']!=expected['target_matrices'] or r['target_resolution']!=expected['target_resolution']:raise ValueError('Retained input/target differs')
        iso=r['component_isolation']
        if not iso['separate_process'] or not iso['parent_state_unchanged'] or iso['return_code']!=0:raise ValueError('Component parent-state isolation differs')
        c=r['component']
        for k in ('real_Torch_CPU','actual_M207_class','actual_SiglipMLP_GELU','native_single_batch_preserved','independent_int32_full_output_equal','nonzero_bias_PS_add','bindings_restored'):
            if c[k] is not True:raise ValueError('Actual component incomplete')
        if c['invalid_native_inputs_rejected']!=4 or c['T32_partial_rows']!=[32,8] or r['source_identities_verified']!=49:raise ValueError('Component/source coverage differs')
        from m407_mlp_contract import local_screen
        if set(r['quality_metrics'])!={'fc1','gelu','fc2','output','residual_sum'} or not all(local_screen(x) for x in r['quality_metrics'].values()) or not local_screen(r['boundary_residual_bf16']):raise ValueError('Predeclared quality threshold failed')
        if set(r['reference_batches'])!={'fc1','fc2'}:raise ValueError('Two Linear references incomplete')
        physical=0;expected_artifacts=set()
        chains=json.loads((PKG/'MLP_CHAINS.json').read_bytes())['chains']
        for k,rows in r['reference_batches'].items():
            chain=next(x for x in chains if x['module']==f'model.visual.encoder.layers.13.mlp.{k}')
            if [x['start'] for x in rows]!=list(range(0,392,32)) or [x['rows'] for x in rows]!=[32]*12+[8]:raise ValueError('T32 geometry differs')
            for x in rows:
                if type(x['initial_shift']) is not int or not 0<=x['selected_shift']<=x['initial_shift']<=6 or x['attempted_shifts']!=list(range(x['initial_shift'],x['selected_shift']-1,-1)) or x['physical_reference_attempts']!=len(x['attempted_shifts']):raise ValueError('Original adaptive retry differs')
                if x['logical_calls']!=1 or x['input_bytes']!=chain['input_bytes'] or x['output_bytes']!=chain['output_bytes']:raise ValueError('Complete packet/raw geometry differs')
                for suffix,key in (('packet','packet_sha256'),('raw','raw_sha256')):
                    name=f'{k}_{x["start"]:03d}_shift{x["selected_shift"]}.{suffix}';expected_artifacts.add(name)
                    a=next(v for v in r['artifacts'] if v['path']==name)
                    if a['sha256']!=x[key] or a['bytes']!=x['input_bytes' if suffix=='packet' else 'output_bytes']:raise ValueError('Artifact byte identity differs')
                physical+=x['physical_reference_attempts']
        expected_artifacts|={k+'.npy' for k in ('input','fc1','gelu','fc2','output')}
        if {x['path'] for x in r['artifacts']}!=expected_artifacts or len(r['artifacts'])!=57 or any('/' in x['path'] or '\\' in x['path'] or not re.fullmatch('[0-9a-f]{64}',x['sha256']) for x in r['artifacts']) or sum(x['bytes'] for x in r['artifacts'])>64<<20:raise ValueError('Artifacts incomplete/unbounded')
        if physical!=r['physical_reference_attempts'] or r['backend_before']!=r['backend_after'] or not 0<r['elapsed_s_diagnostic_not_performance']<=900:raise ValueError('Reference budget/backend/count differs')
    elif r['status']=='FAIL_M417_SAVED_MLP_EXACT_SOFTWARE_REFERENCE':
        if r['gate_return_code']!=1 or not r['errors']:raise ValueError('Failure lacks error')
    else:raise ValueError('Unknown status')
    return digest,raw,r,len(chunks)

def collect(log,out=None,sync_function=sync):
    digest,raw,r,count=decode(Path(log).read_text(encoding='utf-8-sig'))
    out=out or BASE/'runs/M417-layer13-reference-board-01/BOARD_RESULT.json';atomic(out,raw,immutable=True)
    report='# M417 已保存输入精确MLP参考\n\n'+r['status']+'；原rc '+str(r['gate_return_code'])+'。\n\n'
    report+='仅PS软件数学参考：原392行输入、原GELU/bias/T32重试、FP32顺序group、最终FP16/FTZ。无新视觉/语言前向、Overlay、DMA、FPGA或性能/语义质量结论。\n\n'
    report+=json.dumps(r.get('quality_metrics',r['errors']),ensure_ascii=False,indent=2)+'\n\n通过后才准备单descriptor/chain；未经过完整MLP净耗时门禁，不扩大24层。\n'
    atomic(out.with_name('REPORT.md'),report.encode('utf-8'),immutable=True)
    sync_function('latest_m417_reference_board',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256'],local_exact_arithmetic_screen_pass=r.get('local_exact_arithmetic_screen_pass',False),PL_hardware_proven=False,performance_pass=False),
        f'## M417 已保存输入精确MLP软件参考（2026-10-06）\n\n原SHA {digest}，{count}个≤900B严格回收，rc{r["gate_return_code"]}。{r["status"]}；只原第13层局部PS参考，无新视觉/语言/Overlay/DMA/PL。通过才准备descriptor/chain，失败只停本级；没有性能、语义质量或24层结论。')
    print('M417_RESULT_SYNC',digest,count)
    return r

if __name__=='__main__':
    import sys
    if sys.argv[1:]==['transfer']:transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':collect(sys.argv[2])
    else:raise SystemExit('transfer | collect LOG')
