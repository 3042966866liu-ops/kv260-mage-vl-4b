"""Freeze the bounded chain diagnostic and recover raw board bytes only."""
import ast
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace
sys.dont_write_bytecode=True
import m351_workflow as w
from m355_reference import activation,full_reference,digest

ROOT=w.ROOT;HERE=w.HERE;BASE=w.BASE
PKG=BASE/'candidates/M355-device-phase-01'
PREP=BASE/'runs/M355-device-phase-preparation-01'
RUN=BASE/'runs/M355-device-phase-board-01'
PRIOR='4181626b690f131e27722195244684b48f6bd2e2adf87328a0979873fddb43ff'
STABLE=ROOT/'deployment/mage_vl4b/m175_m120_fixed_text_candidate'
FROZEN=BASE/'candidates/M352-load-ps-slot-01'
RELEASE=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'

def decode(log,spec,manifest,contract):
    hashes=re.findall(r'M355_RESULT_SHA256=([0-9a-f]{64})',log)
    codes=re.findall(r'M355_SAVED_GATE_RC=(\d+)',log)
    parts=re.findall(r'M355_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)',log)
    if len(hashes)!=1 or len(codes)!=1 or not parts or len(parts)!=int(parts[0][1]):raise RuntimeError('Incomplete/duplicate export')
    raw=[]
    for i,(index,total,data) in enumerate(parts):
        if int(index)!=i or int(total)!=len(parts):raise RuntimeError('Unordered chunks')
        part=base64.b64decode(data,validate=True)
        if not 0<len(part)<=1800:raise RuntimeError('Chunk limit')
        raw.append(part)
    raw=b''.join(raw)
    if digest(raw)!=hashes[0]:raise RuntimeError('Raw SHA mismatch')
    r=json.loads(raw);code=int(codes[0])
    if r['build_id']!='0x4D395832' or r['gate_level']!='stable-chain-phase-diagnostic':raise RuntimeError('Wrong identity')
    if type(r['gate_return_code']) is not int or code!=r['gate_return_code'] or code not in (0,1):raise RuntimeError('Original rc mismatch')
    if r.get('manifest_sha256')!=manifest or r.get('contract_sha256')!=contract:raise RuntimeError('Package/contract mismatch')
    for k in ('full_model_run','ps_preread_started','performance_pass','promoted'):
        if r[k] is not False:raise RuntimeError('Wrong evidence scope')
    done=re.findall(r'M355_DONE gate_rc=(\d+) export_rc=(\d+)',log)
    if done and (len(done)!=1 or done[0]!=(str(code),'0')):raise RuntimeError('Runner rc mismatch')
    if code==0:
        if r['status']!='PASS_STABLE_CHAIN_DEVICE_PHASE_DIAGNOSTIC' or r['errors'] or r['unsafe_buffers_retained'] or not r['safe_buffers_released']:raise RuntimeError('Incomplete PASS')
        if not r['boot_unchanged'] or not r['cmdline_unchanged'] or not r['overlay_loaded']:raise RuntimeError('Environment identity')
        if r['physical_transactions_started']!=4 or r['kernel_start_writes_completed']!=4 or len(r['transactions'])!=4:raise RuntimeError('Transaction count')
        maxima=[max(c['window_bytes_per_port'] for c in spec['cases'])]*4+[max(c['chain']['input_bytes'] for c in spec['cases']),max(c['chain']['output_bytes'] for c in spec['cases'])]
        allocated=r['allocated_buffers']
        if [b['bytes'] for b in allocated]!=maxima or r['released_buffers']!=allocated[::-1] or len({b['address'] for b in allocated})!=6:raise RuntimeError('Allocation/free lifecycle')
        if any(b['address']<0 or b['address']+b['bytes']>0x80000000 for b in allocated):raise RuntimeError('Low DDR range')
        if len(r['memory'])!=9 or any(m['required_bytes']!=67108864 or m['cma_free_bytes']<67108864 for m in r['memory']):raise RuntimeError('Real allocation/staging capacity')
        for t,c in zip(r['transactions'],spec['cases']):
            chain=c['chain']
            if t['chain_index']!=chain['chain_index'] or t['chain_sha256']!=c['chain_sha256'] or t['input_bytes']!=chain['input_bytes'] or t['output_bytes']!=chain['output_bytes']:raise RuntimeError('Chain geometry')
            if t['bank_addresses']!=[b['address'] for b in allocated[:4]]:raise RuntimeError('Bank identity')
            if t['full_output_exact'] is not True or t['output_sha256']!=c['expected_ftz_sha256'] or t['expected_sha256']!=c['expected_ftz_sha256']:raise RuntimeError('Full output mismatch')
            o=t['observation'];s=o['last_snapshot'];events=o['events'];submitted=o['submitted_ns']
            if o.get('completion_proven') is not True or o['pure_compute_time_proven'] is not False or o['polls']<1:raise RuntimeError('Observation completion')
            if s['ap_return']!=0x4D395832 or not s['mm2s_idle'] or not s['s2mm_idle'] or not events['ap_done']['clear_on_read_latched']:raise RuntimeError('Completion registers')
            if any(s[k]!='' for k in ('kernel_read_error','return_read_error','dma_read_error')) or s['mm2s_error'] or s['s2mm_error'] or (s['mm2s_dmasr']|s['s2mm_dmasr'])&0x770:raise RuntimeError('Completion errors')
            if set(o['dma_timing_unresolved'])!={k for k in ('mm2s','s2mm') if k not in events}:raise RuntimeError('Unresolved timing inconsistent')
            if o['completed_ns']-submitted!=o['wait_ns'] or not 0<o['wait_ns']<11_000_000_000:raise RuntimeError('Timing budget')
            for k,event in events.items():
                if not submitted<=event['lower_ns']<=event['upper_ns']<=o['completed_ns']:raise RuntimeError('Invalid interval')
                if k!='ap_done' and event['causal_busy_seen'] is not True:raise RuntimeError('Initial idle used as completion')
    elif r['status'] not in ('FAIL_DEVICE_PHASE_DIAGNOSTIC','FAIL_UNSAFE_RETAINED') or not r['errors']:raise RuntimeError('Wrong failure status')
    return digest(raw),raw,r

def prepare():
    if PKG.exists() or PREP.exists():raise RuntimeError('Immutable preparation exists')
    recovery={n:dict(sha256=w.sha(ROOT/n),bytes=(ROOT/n).stat().st_size,characters=len((ROOT/n).read_text(encoding='utf-8-sig'))) for n in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')}
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    prior=BASE/'runs/M354-device-schedule-audit-01/RESULT.json'
    assert w.sha(prior)==PRIOR and all(PRIOR in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    audit=json.loads(prior.read_text(encoding='utf-8'));closure=json.loads((FROZEN/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))
    assert len(closure['checked'])==47 and not closure['errors']
    for row in closure['checked']:
        assert w.sha(ROOT/row['path'])==row['sha256']
        if row.get('recovered_exact_snapshot'):
            recovered=(ROOT/row['recovered_exact_snapshot']).read_bytes()
            assert digest(recovered)==row['recovered_sha256']==row['expected_sha256']
            assert len(recovered)==row['historical_bytes'] and (ROOT/row['path']).read_bytes().startswith(recovered)
        else:assert row['sha256']==row['expected_sha256']
    for row in audit['verified_files']:assert w.sha(ROOT/row['path'])==row['sha256']
    manifest=json.loads((STABLE/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'));members={r['path']:r for r in manifest['files']}
    assert w.sha(STABLE/'PACKAGE_MANIFEST.json')=='406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f'
    names=('runtime/board_runtime.py','runtime/contract_runtime.py','contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json')
    for n in names:assert w.sha(STABLE/n)==members[n]['sha256']
    source=(STABLE/'runtime/board_runtime.py').read_text(encoding='utf-8');node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='chain_window')
    ns={'VerifiedLayout':SimpleNamespace};exec(ast.get_source_segment(source,node),ns)
    module_spec=importlib.util.spec_from_file_location('contract_runtime',STABLE/'runtime/contract_runtime.py');module=importlib.util.module_from_spec(module_spec);sys.modules['contract_runtime']=module;module_spec.loader.exec_module(module)
    contract=json.loads((STABLE/names[2]).read_text(encoding='utf-8'));lp=RELEASE/'external_assets/weights/language_fourport/SIXPORT_LAYOUT_MANIFEST.json'
    assert w.sha(lp)==contract['source_manifest_sha256'];layout=SimpleNamespace(manifest=json.loads(lp.read_text(encoding='utf-8')))
    tests={}
    for name in ('test_completion_observer.py','test_m355_reference.py'):
        tested=subprocess.run([sys.executable,'-B',str(HERE/name)],capture_output=True,text=True,encoding='utf-8')
        if tested.returncode:raise RuntimeError(tested.stdout+tested.stderr)
        tests[name]=tested.stdout+tested.stderr
    cases=[];goldens={}
    for selected in audit['representative_original_chains']:
        chain=contract['chains'][selected['chain_index']];canonical=digest(json.dumps(chain,sort_keys=True,separators=(',',':')).encode())
        assert canonical==selected['chain_sha256']
        words,size=ns['chain_window'](layout,chain);windows=[];rows=[]
        for f in layout.manifest['files']:
            p=lp.parent/f['path'];identity=p.stat();assert identity.st_size==f['bytes']
            with p.open('rb') as stream:stream.seek(words*16);raw=stream.read(size)
            after=p.stat()
            assert len(raw)==size and (after.st_size,after.st_mtime_ns,after.st_ctime_ns)==(identity.st_size,identity.st_mtime_ns,identity.st_ctime_ns)
            windows.append(raw);rows.append(dict(file=f['path'],file_bytes=f['bytes'],sha256=digest(raw)))
        packet=module.pack_chain_input(chain,activation(chain['groups']),words,0)
        expected=full_reference(chain,windows,words,packet)
        label=str(chain['layer'])+':'+chain['family'];print('M355_FROZEN_REFERENCE '+label+' output_bytes='+str(len(expected)),flush=True)
        goldens[str(chain['chain_index'])+'.bin']=expected
        cases.append(dict(chain=chain,chain_sha256=canonical,base_words=words,window_bytes_per_port=size,windows=rows,packet_sha256=digest(packet),expected_ftz_sha256=digest(expected)))
    spec=dict(build_id='0x4D395832',prior_sha256=PRIOR,layout_path=lp.relative_to(RELEASE).as_posix(),layout_sha256=w.sha(lp),cases=cases,
        stable_sources={n:dict(path='deployment/mage_vl4b/m175_m120_fixed_text_candidate/'+n,sha256=w.sha(STABLE/n)) for n in names},
        scope='Four original chains, deterministic nonzero T32, selected windows exact SHA, complete FTZ output. Not full model, pure compute, performance or runtime capacity.')
    files={n:(FROZEN/n).read_bytes() for n in ('m341_build_id_gate.py','m120_board_common.py','m120_board_env_preflight.py','measurement.py','board_safety.py','HARDWARE_CLOSURE.json')}
    files.update({n:(HERE/n).read_bytes() for n in ('m355_device_phase_probe.py','m355_export_result.py','completion_observer.py','owned_buffer_release.py')})
    files['CASE_CONTRACT.json']=w.encoded(spec)
    files['run_m355_device_phase.sh']='\n'.join(['#!/usr/bin/env bash','set -euo pipefail','cd "$(dirname "${BASH_SOURCE[0]}")"','manifest_sha=${1:?manifest SHA required}',
        '[[ "${2:-}" == "--enable-device-phase-probe" ]] || { echo M355_DISABLED; exit 2; }',
        "printf '%s  PACKAGE_MANIFEST.json\\n' \"$manifest_sha\" | sha256sum -c -",'sha256sum -c SHA256SUMS','sudo -n true',
        '[[ ! -e /home/ubuntu/m355_device_phase_evidence_01 ]] || { echo M355_EXISTS_COLLECT_ONLY; exit 2; }','set +e',
        'sudo -n env XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python3 -B ./m355_device_phase_probe.py "$manifest_sha" --enable-device-phase-probe',
        'gate_rc=$?','sudo -n /usr/local/share/pynq-venv/bin/python3 -B ./m355_export_result.py','export_rc=$?','set -e',
        "printf 'M355_DONE gate_rc=%s export_rc=%s\\n' \"$gate_rc\" \"$export_rc\"",'if [[ "$gate_rc" -ne 0 ]]; then exit "$gate_rc"; fi','exit "$export_rc"','']).encode('utf-8')
    for n,raw in files.items():
        if n.endswith('.py'):ast.parse(raw.decode('utf-8'),feature_version=(3,10))
    # The exact board package entry imports recursively without constructing PYNQ.
    PKG.mkdir(parents=True);PREP.mkdir(parents=True)
    for n,raw in files.items():w.atomic(PKG/n,raw)
    imported=subprocess.run([sys.executable,'-B',str(HERE/'m355_import_preflight.py'),str(PKG)],capture_output=True,text=True,encoding='utf-8')
    if imported.returncode:raise RuntimeError(imported.stdout+imported.stderr)
    rows=[dict(path=n,bytes=len(raw),sha256=w.sha(PKG/n)) for n,raw in sorted(files.items())]
    w.atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=w.sha(PKG/'SHA256SUMS')))
    w.atomic(PKG/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='m355-stable-chain-phase-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    assert {p.name for p in PKG.iterdir()}=={r['path'] for r in rows}|{'PACKAGE_MANIFEST.json'}
    negatives=selftest()
    for n,raw in goldens.items():w.atomic(PREP/'golden'/n,raw,immutable=True)
    w.atomic(PREP/'TEST_OUTPUT.txt',w.encoded(tests));w.atomic(PREP/'IMPORT_OUTPUT.txt',(imported.stdout+imported.stderr).encode('utf-8'))
    r=dict(status='PASS_OFFLINE_DEVICE_PHASE_PREPARATION',build_id='0x4D395832',prior_sha256=PRIOR,recovery_read=recovery,
        observer_tests=13,frozen_reference_cases=7,original_chains=4,hardware_same_sha_items=47,python310_syntax=True,entry_import_preflight=True,collector_negative_checks=negatives,
        package_files=len(rows),package_bytes=sum(r['bytes'] for r in rows),manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),
        controller_sha256=w.sha(HERE/'m355_control.ps1'),workflow_sha256=w.sha(Path(__file__)),board_run=False,performance_pass=False,
        full_model_run=False,promoted=False,cma_reserve_bytes=67108864,automation_remains_paused=True,
        rejected_attempts=['Initial local closure check rejected documented appended hls.log. Exact existing M341 recovered prefix and original current SHA both verified; no original evidence edit or hardware rerun.'],
        next_step='One COM3 chain diagnostic, exact manifest, same-terminal sudo, bash-n, fixed environment; four chains once. Then pause.')
    w.atomic(PREP/'RESULT.json',w.encoded(r),immutable=True);value=dict(status=r['status'],result=(PREP/'RESULT.json').relative_to(ROOT).as_posix(),sha256=w.sha(PREP/'RESULT.json'),manifest_sha256=r['manifest_sha256'],board_run=False,performance_pass=False)
    note='## M355 设备分段计时包离线准备完成（2026-10-02）\n\n稳定Build0x4D395832；用户仅恢复本次设备分段测试，自动推进仍暂停。13项观察器检查、7项原真实记录完整参考比较、4条非零T32原chain全输出参考及47项同SHA硬件闭包通过。新包默认关闭，无上板/Overlay/模型或提速结果。原始准备SHA `'+value['sha256']+'`；证据 `'+value['result']+'`。下一步COM3同终端sudo、包SHA/bash-n和固定环境后执行四条chain各一次，保留实际分配后64MiB CMA余量；活动故障保留缓冲/进程。收集原字节并同步后暂停，稳定源/服务/回滚/boot/DTB/CMA保持。\n\n'
    w.sync('latest_m355_device_phase_preparation',value,note)
    print(json.dumps(value))

def selftest():
    spec=json.loads((PKG/'CASE_CONTRACT.json').read_text(encoding='utf-8'));manifest=w.sha(PKG/'PACKAGE_MANIFEST.json');contract=w.sha(PKG/'CASE_CONTRACT.json')
    allocated=[dict(bytes=x,address=0x10000000+i*0x1000000) for i,x in enumerate([max(c['window_bytes_per_port'] for c in spec['cases'])]*4+[max(c['chain']['input_bytes'] for c in spec['cases']),max(c['chain']['output_bytes'] for c in spec['cases'])])]
    r=dict(status='PASS_STABLE_CHAIN_DEVICE_PHASE_DIAGNOSTIC',gate_level='stable-chain-phase-diagnostic',build_id='0x4D395832',manifest_sha256=manifest,contract_sha256=contract,gate_return_code=0,
        errors=[],full_model_run=False,ps_preread_started=False,performance_pass=False,promoted=False,unsafe_buffers_retained=False,safe_buffers_released=True,
        boot_unchanged=True,cmdline_unchanged=True,overlay_loaded=True,physical_transactions_started=4,kernel_start_writes_completed=4,transactions=[],allocated_buffers=allocated,released_buffers=allocated[::-1],memory=[dict(required_bytes=67108864,cma_free_bytes=67108864)]*9)
    for c in spec['cases']:
        chain=c['chain'];o=dict(submitted_ns=100,polls=2,completed_ns=1100,wait_ns=1000,pure_compute_time_proven=False,completion_proven=True,dma_timing_unresolved=[],events={},last_snapshot=dict(ap_return=0x4D395832,mm2s_idle=True,s2mm_idle=True,mm2s_error=False,s2mm_error=False,mm2s_dmasr=4098,s2mm_dmasr=4098,kernel_read_error='',return_read_error='',dma_read_error=''))
        for k in ('mm2s','s2mm','ap_done'):o['events'][k]=dict(lower_ns=200,upper_ns=1100,causal_busy_seen=True,clear_on_read_latched=True)
        r['transactions'].append(dict(label=str(chain['layer'])+':'+chain['family'],chain_index=chain['chain_index'],chain_sha256=c['chain_sha256'],input_bytes=chain['input_bytes'],output_bytes=chain['output_bytes'],bank_addresses=[b['address'] for b in allocated[:4]],output_sha256=c['expected_ftz_sha256'],expected_sha256=c['expected_ftz_sha256'],full_output_exact=True,observation=o))
    def export(value):
        raw=w.encoded(value);parts=[raw[i:i+1800] for i in range(0,len(raw),1800)]
        return 'M355_RESULT_SHA256='+digest(raw)+'\nM355_SAVED_GATE_RC='+str(value['gate_return_code'])+'\n'+''.join('M355_RESULT_CHUNK='+str(i)+'/'+str(len(parts))+':'+base64.b64encode(part).decode()+'\n' for i,part in enumerate(parts))+'M355_DONE gate_rc='+str(value['gate_return_code'])+' export_rc=0\n'
    good=export(r);assert decode(good,spec,manifest,contract)[2]==r
    fail=dict(r,status='FAIL_DEVICE_PHASE_DIAGNOSTIC',gate_return_code=1,errors=['明确测试失败'])
    assert decode(export(fail),spec,manifest,contract)[2]==fail
    bads=[good.replace('M355_SAVED_GATE_RC=0','M355_SAVED_GATE_RC=1'),good.replace('M355_RESULT_CHUNK=1/','M355_RESULT_CHUNK=0/'),good.replace('export_rc=0','export_rc=1'),good+'M355_RESULT_SHA256='+'0'*64]
    for k,v in [('physical_transactions_started',3),('performance_pass',True),('unsafe_buffers_retained',True),('released_buffers',allocated),('memory',[]),('contract_sha256','0'*64)]:bads.append(export(dict(r,**{k:v})))
    for key,value in [('chain_sha256','0'*64),('output_sha256','0'*64),('full_output_exact',False)]:
        mutated=json.loads(json.dumps(r));mutated['transactions'][0][key]=value;bads.append(export(mutated))
    for bad in bads:
        try:decode(bad,spec,manifest,contract)
        except (RuntimeError,ValueError,KeyError):pass
        else:raise AssertionError('Bad evidence accepted')
    print('M355_COLLECTOR_SELF_TEST_PASS negatives='+str(len(bads)))
    return len(bads)

def collect(logpath):
    spec=json.loads((PKG/'CASE_CONTRACT.json').read_text(encoding='utf-8'))
    sha,raw,r=decode((ROOT/logpath).read_text(encoding='utf-8-sig'),spec,w.sha(PKG/'PACKAGE_MANIFEST.json'),w.sha(PKG/'CASE_CONTRACT.json'))
    w.atomic(RUN/'BOARD_RESULT.json',raw,immutable=True)
    note='## M355 设备分段上板测试 '+r['status']+'（2026-10-02）\n\n稳定Build0x4D395832；4条代表性原chain的独立诊断，物理启动'+str(r['physical_transactions_started'])+'次。原rc'+str(r['gate_return_code'])+'；原始证据 `'+(RUN/'BOARD_RESULT.json').relative_to(ROOT).as_posix()+'` SHA `'+sha+'`。错误 `'+json.dumps(r['errors'],ensure_ascii=False)+'`。主机轮询记录输入DMA/AP_DONE/输出DMA完成区间，不能当纯计算时间或整请求提速。PS预读容量与视频数值/性能仍未解锁。按用户要求本次结束后暂停；自动推进保持PAUSED，稳定源/服务/回滚/boot/DTB/CMA保持。\n\n'
    value=dict(status=r['status'],result=(RUN/'BOARD_RESULT.json').relative_to(ROOT).as_posix(),sha256=sha,build_id=r['build_id'],physical_transactions=r['physical_transactions_started'],performance_pass=False,promoted=False,unsafe_buffers_retained=r['unsafe_buffers_retained'],automation_remains_paused=True)
    w.sync('latest_m355_device_phase_board',value,note)
    report='# M355 设备分段上板测试\n\n'+note+'各时间为从提交起的主机观察区间，单位ms，非独立可相加的阶段。\n\n| chain | 输入DMA完成 | AP_DONE | 输出DMA完成 | 合成完成等待 | 全输出一致 |\n|---|---|---|---|---|---|\n'
    for t in r['transactions']:
        o=t.get('observation')
        if not o:continue
        def interval(k):
            e=o['events'].get(k)
            return 'UNRESOLVED' if e is None else f"{(e['lower_ns']-o['submitted_ns'])/1e6:.3f}–{(e['upper_ns']-o['submitted_ns'])/1e6:.3f}"
        report+='| '+t['label']+' | '+interval('mm2s')+' | '+interval('ap_done')+' | '+interval('s2mm')+f" | {o['wait_ns']/1e6:.3f} | {t.get('full_output_exact')} |\n"
    report+='\n轮询影响和区间重叠均保留原始证据；输入完成到AP_DONE还包含权重DDR访问、计算、合并及输出背压。没有内部计数器，不能精确拆分。每条仅一次，不是重复性能对照。\n'
    w.atomic(RUN/'REPORT.md',report.encode('utf-8'))
    print(json.dumps(dict(status='M355_RESULT_SYNCHRONIZED',sha256=sha,board_status=r['status'])))

if __name__=='__main__':
    if sys.argv[1:]==['prepare']:prepare()
    elif sys.argv[1:]==['selftest']:selftest()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':collect(sys.argv[2])
    else:raise SystemExit('prepare | collect logpath')
