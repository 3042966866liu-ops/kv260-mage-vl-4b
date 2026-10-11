"""Actual complete exporter/host evidence; explicit synthetic timing fixtures."""
import ast,contextlib,copy,importlib.util,io,json,subprocess,tempfile
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
import m430_workflow as w
def control():
    text=(HERE/'m429_control04.ps1').read_text(encoding='utf-8')
    old="'latest_m427_half_closure','latest_m428_saved_language_closure','latest_m429_streamed_scope_component','latest_m429_repair_packet','latest_m429_repair_support'"
    new="'latest_m429_late11_visual_numerical_closure','latest_m430_complete_visual_protocol','latest_m430_timed_scope_component','latest_m430_complete_visual_packet','latest_m430_complete_visual_support'"
    assert text.count(old)==1;text=text.replace(old,new).replace('latest_m429_repair_support','latest_m430_complete_visual_support')
    for old,new in [('M429-late11-visual-PL-numeric-03','M430-late11-visual-warm-02'),('/home/ubuntu/m429_late11_visual_candidate_03','/home/ubuntu/m430_late11_visual_warm_candidate_02'),('tmp/m42904','tmp/m43002'),('m429_workflow04.py','m430_workflow.py'),('M429-late11-visual-PL-board-02','M430-complete-visual-warm-board-01'),('latest_m429_late11_visual_transfer','latest_m430_complete_visual_transfer'),('run_m429.sh','run_m430.sh')]:text=text.replace(old,new)
    text=text.replace('M429','M430').replace('M430_ENABLE_PL_NUMERICAL','M430_ENABLE_VISUAL_PERFORMANCE').replace('-TimeoutSeconds 1800','-TimeoutSeconds 2400')
    atomic(HERE/'m430_control.ps1',text.encode(),immutable=True)
    print('M430_CONTROL_PREPARED')
def fixture():
    n=json.loads((BASE/'runs/M429-late11-visual-PL-board-02/BOARD_RESULT.json').read_bytes());r=copy.deepcopy(n);plan=json.loads((w.PKG/'PLAN.json').read_bytes())
    r.update(status='PASS_M430_COMPLETE_VISUAL_WARM_COLLECTED',gate_level='late11-complete-visual-controlled-warm-performance',gate_return_code=0,manifest_sha256=sha(w.PKG/'PACKAGE_MANIFEST.json'),visual_forward_calls=12,original_visual_forward_calls=6,physical_transactions_started=1718,fpga_transactions=1718,numerical_source_sha256=plan['numerical_result_sha256'],warm_protocol_sha256=plan['protocol_sha256'],warm_conditions_established=True,warm_sequence=w.ORDER,retained_features=[],matched_wire_batches_reused=286)
    r['component']=json.loads((BASE/'runs/M430-timed-scope-component-01/RESULT.json').read_bytes())['component']
    oldwarm=json.loads((BASE/'runs/M425-warm-performance-board-01/BOARD_RESULT.json').read_bytes());env=oldwarm['formal_samples'][0]['before_environment'];cache=oldwarm['formal_samples'][0]['after_cache'];r['reference_environment']=env
    r['PL_rows']=[];r['staging']=[];samples=[]
    for i,variant in enumerate(w.ORDER):
        rows=[{k:v for k,v in x.items() if k not in ('packet_sha256','raw_sha256')} for x in n['PL_rows']] if variant=='B' else []
        stages=copy.deepcopy(n['staging']) if variant=='B' else []
        ns=40000000000 if variant=='A' else 35000000000
        s=dict(index=i+1,variant=variant,timing=dict(total_ms=ns/1e6),elapsed_ns=ns,feature=n['original_visual' if variant=='A' else 'candidate_visual'],feature_complete_exact=True,bindings_restored=True,before_environment=env,after_environment=env,before_cache=cache,after_cache=cache,io_delta=dict(read_bytes=0,rchar=100),major_fault_delta=0,before_memory=n['memory_after_constructor'],after_memory=n['memory_after_constructor'],physical_calls=len(rows),PL_batches=n['PL_batches'] if variant=='B' else {},staging_rows=stages,device_wait_ns=sum(x['wait_ns'] for x in rows),staging_ns=sum(x['elapsed_ns'] for x in stages),phase='warmup' if i<4 else 'formal',phase_index=i+1 if i<4 else i-3)
        # The real producer independently snapshots each environment/cache read.
        for key in ('before_environment','after_environment','before_cache','after_cache','feature','before_memory','after_memory'):s[key]=copy.deepcopy(s[key])
        samples.append(s);r['PL_rows']+=rows;r['staging']+=stages
    r['warmup_samples']=samples[:4];r['formal_samples']=samples[4:];r['performance_adjudication']=w.score(r['formal_samples']);r['performance_pass']=r['performance_adjudication']['performance_pass']
    return r
def main():
    for row in json.loads((w.PKG/'PACKAGE_MANIFEST.json').read_bytes())['files']:assert sha(w.PKG/row['path'])==row['sha256']
    spec=importlib.util.spec_from_file_location('actual_m430_export',w.PKG/'m430_export.py');export=importlib.util.module_from_spec(spec);spec.loader.exec_module(export)
    good=fixture();w.check(good);rejected=[]
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as d:
        export.OUTPUT=__import__('pathlib').Path(d)/'BOARD_RESULT.json'
        def emit(r):
            raw=json.dumps(r,separators=(',',':'),allow_nan=False).encode();export.OUTPUT.write_bytes(raw);capture=io.StringIO()
            with patch_root(export),contextlib.redirect_stdout(capture):export.emit_saved()
            return capture.getvalue(),raw
        text,raw=emit(good);decoded=w.decode(text+'M430_DONE gate_rc=0 export_rc=0\n');assert decoded[1]==raw
        no_gain=copy.deepcopy(good)
        for sample in no_gain['formal_samples']:sample['elapsed_ns']=40000000000;sample['timing']['total_ms']=40000.
        no_gain['performance_adjudication']=w.score(no_gain['formal_samples']);no_gain['performance_pass']=False;assert w.decode(emit(no_gain)[0])[2]['performance_pass'] is False
        failure=copy.deepcopy(good);failure.update(status='FAIL_M430_COMPLETE_VISUAL_WARM',gate_return_code=1,errors=['Explicit synthetic failure'],numerical_hardware_proven=False);assert w.decode(emit(failure)[0]+'M430_DONE gate_rc=1 export_rc=0\n')[2]['gate_return_code']==1
        def reject(name,fn):
            try:fn()
            except (ValueError,RuntimeError,KeyError):rejected.append(name)
            else:raise AssertionError('Invalid accepted '+name)
        edits=[('scope',lambda r:r.__setitem__('language_forward_calls',1)),('temperature',lambda r:r.__setitem__('temperature_measurement_enabled',True)),('rc-bool',lambda r:r.__setitem__('gate_return_code',False)),('samples',lambda r:r['formal_samples'].pop()),('order',lambda r:r['formal_samples'][0].__setitem__('variant','B')),('feature',lambda r:r['formal_samples'][0]['feature'].__setitem__('sha256','0'*64)),('timer',lambda r:r['formal_samples'][0].__setitem__('elapsed_ns',1)),('read-drift',lambda r:r['formal_samples'][0]['io_delta'].__setitem__('read_bytes',2<<20)),('major-fault',lambda r:r['formal_samples'][0].__setitem__('major_fault_delta',1)),('cache',lambda r:r['formal_samples'][0]['after_cache'].__setitem__('cache_entries',25)),('clock',lambda r:r['formal_samples'][0]['after_environment']['pl_clocks'].__setitem__('pl0_ref',1)),('CMA-plan',lambda r:r.__setitem__('dma_allocations',20)),('free',lambda r:r['releases'].pop()),('retained',lambda r:r.__setitem__('unsafe_dma_buffers_retained',True)),('PL-count',lambda r:r.__setitem__('physical_transactions_started',1719)),('PL-order',lambda r:r['PL_rows'][0].__setitem__('start',32)),('DMA-fault',lambda r:r['PL_rows'][0]['completed_snapshot'].__setitem__('s2mm_error',True)),('heavy-hash',lambda r:r['PL_rows'][0].__setitem__('packet_sha256','0'*64)),('stage',lambda r:r['formal_samples'][1]['staging_rows'].pop()),('retry',lambda r:r['formal_samples'][1]['PL_batches']['13']['fc1'][0].__setitem__('physical_calls',2)),('decision',lambda r:r.__setitem__('performance_pass',False)),('prior',lambda r:r.__setitem__('numerical_source_sha256','0'*64)),('restore',lambda r:r.__setitem__('stable_restored',False)),('memory',lambda r:r['formal_samples'][0]['after_memory'].__setitem__('MemAvailable',1))]
        for name,edit in edits:
            r=copy.deepcopy(good);edit(r);reject(name,lambda r=r:w.decode(emit(r)[0]))
        for name,bad in [('missing-chunk','\n'.join(x for x in text.splitlines() if not x.startswith('M430_RESULT_CHUNK=0/'))),('duplicate-sha',text+'M430_RESULT_SHA256='+'0'*64+'\n'),('main-rc',text+'M430_DONE gate_rc=1 export_rc=0\n'),('export-rc',text+'M430_DONE gate_rc=0 export_rc=1\n')]:reject(name,lambda bad=bad:w.decode(bad))
    pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe';cp=subprocess.run([pwsh,'-NoProfile','-File',str(HERE/'m430_control.ps1'),'-Mode','SelfTest'],capture_output=True);atomic(ROOT/'tmp/m43002/control_stdout.bin',cp.stdout,immutable=True);atomic(ROOT/'tmp/m43002/control_stderr.bin',cp.stderr,immutable=True);assert cp.returncode==0 and b'M430_CONTROL_SELF_TEST_PASS' in cp.stdout
    cp=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/bin/bash','-n','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/deployment/mage_vl4b/optimization_v1/candidates/M430-late11-visual-warm-02/run_m430.sh'],capture_output=True);atomic(ROOT/'tmp/m43002/bash_stdout.bin',cp.stdout,immutable=True);atomic(ROOT/'tmp/m43002/bash_stderr.bin',cp.stderr,immutable=True);assert cp.returncode==0
    for name in ('m430_workflow.py','m430_support.py'):ast.parse((HERE/name).read_text(encoding='utf-8'),feature_version=(3,10))
    r=dict(status='PASS_M430_ACTUAL_EXPORT_HOST_CONTROL_SUPPORT',manifest_sha256=sha(w.PKG/'PACKAGE_MANIFEST.json'),fixture_raw_bytes=len(raw),fixture_chunks=decoded[3],actual_export_decoder_PASS_no_gain_FAIL=True,negative_checks=rejected,synthetic_timers_and_root_API_explicit=True,control_intentional_failure_collect=True,bash_n=True,source_sha256={n:sha(HERE/n) for n in ('m430_control.ps1','m430_workflow.py','m430_support.py')},board_run=False,performance_pass=False,temperature_measurement_enabled=False)
    out=BASE/'runs/M430-complete-visual-support-01/RESULT.json';atomic(out,encoded(r),immutable=True)
    sync('latest_m430_complete_visual_support',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=r['manifest_sha256']),f'## M430 实际完整导出与计时回收支持（2026-10-06）\n\nSHA {sha(out)}，实际exporter→host完整PASS/无收益/FAIL原字节，{len(rejected)}拒绝及控制故意失败后收集、Python3.10/bash-n通过。计时/root明确synthetic，不证明性能；包已齐，下一步COM3一次sudo后上传运行固定12次视觉，无语言/测温/加样本。')
    print('M430_SUPPORT_SYNC',sha(out),len(rejected),len(raw))
@contextlib.contextmanager
def patch_root(export):
    from unittest.mock import patch
    with patch.object(export.os,'geteuid',lambda:0,create=True),patch.object(export.time,'sleep',lambda *x:None):yield
if __name__=='__main__':
    import sys
    if sys.argv[1:]==['control']:control()
    elif sys.argv[1:]==['run']:main()
    else:raise SystemExit('control | run')
