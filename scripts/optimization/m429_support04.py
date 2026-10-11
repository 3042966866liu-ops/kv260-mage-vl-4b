"""Actual exporter -> strict actual decoder, with explicit owner/root fixture API."""
import ast,contextlib,copy,hashlib,importlib.util,io,json,subprocess,tempfile
from pathlib import Path
from unittest.mock import patch
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m429_workflow04 import PKG,decode,check

def fixture():
    plan=json.loads((PKG/'PLAN.json').read_bytes());board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    evidence=board['latest_m420_combination_board'];assert sha(ROOT/evidence['result'])==evidence['sha256']
    old=json.loads((ROOT/evidence['result']).read_bytes())
    soft=json.loads((BASE/'runs/M427-half-software-board-01/BOARD_RESULT.json').read_bytes());half=next(x for x in soft['ranges'] if x['name']=='late_13_23')
    comp=json.loads((BASE/'runs/M429-streamed-scope-component-01/RESULT.json').read_bytes())['component']
    r=copy.deepcopy(old)
    r.update(status='PASS_M429_LATE11_COMPLETE_VISUAL_PL_NUMERICAL',gate_level='late11-complete-visual-PL-numerical',gate_return_code=0,errors=[],manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
        selected_layers=list(range(13,24)),temperature_measurement_enabled=False,performance_pass=False,formal_promotion_allowed=False,language_forward_calls=0,original_visual_forward_calls=0,
        visual_forward_calls=1,numerical_hardware_proven=True,overlay_loaded=True,bindings_restored=True,visual_owner_closed=True,original_reference_pass=True,saved_original_all24_boundaries_verified=True,
        CPU_component_before_Overlay=True,feature_screen_pass=True,source_identities_verified=49,targets=soft['targets'],prefix_topology=soft['prefix_topology'],preprocessed=soft['preprocessed'],
        software_reference_source_sha256=plan['M427_raw_sha256'],task_source_sha256=plan['M428_raw_sha256'],baseline_source_sha256=plan['M426_raw_sha256'],hardware_closure_sha256=plan['hardware_closure_sha256'],
        original_visual=soft['original_visual'],candidate_visual=half['candidate_visual'],full_visual_quality=half['full_visual_quality'],boundary_comparison=half['boundary_comparison'],
        weight_windows=plan['windows'],staging=[dict(layer=i,part=p,bytes=4*557056,elapsed_ns=1) for i in range(13,24) for p in ('fc1','fc2')],
        physical_transactions_started=288,fpga_transactions=288,dma_allocations=19,matched_wire_batches=286,peak_live_layer_scopes=1,component=comp,
        retained_features=[dict(half['saved_feature'],path='late_13_23_PL_visual.npy')],elapsed_s_diagnostic_not_performance=1.)
    r['component_bootstrap']=json.loads((BASE/'runs/M429-isolated-bootstrap-board-01/BOARD_RESULT.json').read_bytes())['bootstrap']
    r['isolated_bootstrap_source_sha256']=plan['isolated_bootstrap_source_sha256']
    r['PL_rows']=[];r['PL_batches']={}
    snapshot=copy.deepcopy(old['PL_rows'][0]['completed_snapshot'])
    for i in range(13,24):
        r['PL_batches'][str(i)]={}
        for p in ('fc1','fc2'):
            r['PL_batches'][str(i)][p]=[]
            for ref in half['reference_batches'][str(i)][p]:
                r['PL_rows'].append(dict(layer=i,part=p,start=ref['start'],shift=ref['selected_shift'],input_bytes=ref['input_bytes'],output_bytes=ref['output_bytes'],packet_sha256=ref['packet_sha256'],raw_sha256=ref['raw_sha256'],wait_ns=1,completed_snapshot=snapshot))
                r['PL_batches'][str(i)][p].append({k:ref[k] for k in ('start','rows','initial_shift','attempted_shifts','selected_shift')}|{'physical_calls':1})
    return r

def main():
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes())
    for row in m['files']:assert sha(PKG/row['path'])==row['sha256']
    good=fixture();assert check(good)==good
    spec=importlib.util.spec_from_file_location('actual_m429_export',PKG/'m429_export.py');export=importlib.util.module_from_spec(spec);spec.loader.exec_module(export)
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
        output=Path(directory)/'BOARD_RESULT.json';export.OUTPUT=output
        def emit(r,root=True):
            raw=encoded(r);output.write_bytes(raw);capture=io.StringIO()
            with patch.object(export.os,'geteuid',lambda:0 if root else 1000,create=True),patch.object(export.time,'sleep',lambda x:None),contextlib.redirect_stdout(capture):export.emit_saved()
            return capture.getvalue(),raw
        text,raw=emit(good);parsed=decode(text+'M429_DONE gate_rc=0 export_rc=0\n');assert parsed[1]==raw and parsed[2]==good
        failure=copy.deepcopy(good);failure.update(status='FAIL_M429_LATE11_VISUAL_NUMERICAL',gate_return_code=1,errors=[dict(type='ExplicitFixtureFailure',message='No board execution')],numerical_hardware_proven=False)
        ftext,fraw=emit(failure);assert decode(ftext+'M429_DONE gate_rc=1 export_rc=0\n')[1]==fraw
        rejected=[]
        def reject(label,fn):
            try:fn()
            except (ValueError,RuntimeError):rejected.append(label)
            else:raise AssertionError('Invalid accepted '+label)
        for label,edit in [('bootstrap',lambda r:r['component_bootstrap'].__setitem__('threads',2)),('bool-rc',lambda r:r.__setitem__('gate_return_code',False)),('wrong-level',lambda r:r.__setitem__('gate_level','CPU-only-two-half-visual-MLP-screen')),
                ('wrong-range',lambda r:r.__setitem__('selected_layers',[12,13])),('temperature',lambda r:r.__setitem__('temperature_measurement_enabled',True)),
                ('performance',lambda r:r.__setitem__('performance_pass',True)),('missing-row',lambda r:r['PL_rows'].pop()),
                ('wrong-wire',lambda r:r['PL_rows'][0].__setitem__('raw_sha256','0'*64)),('wrong-packet',lambda r:r['PL_rows'][0].__setitem__('packet_sha256','0'*64)),
                ('wrong-order',lambda r:r['PL_rows'][0].__setitem__('start',32)),('extra-retry',lambda r:r['PL_batches']['13']['fc1'][0].__setitem__('physical_calls',2)),
                ('double-minimal-count',lambda r:r.__setitem__('fpga_transactions',290)),('boundary',lambda r:r['boundary_comparison'][0]['candidate'].__setitem__('sha256','0'*64)),
                ('feature',lambda r:r['candidate_visual'].__setitem__('sha256','0'*64)),('unsafely-retained',lambda r:r.__setitem__('unsafe_dma_buffers_retained',True)),
                ('new-DMA',lambda r:r['unexpected_DMA_requests'].append('fixture')),('release',lambda r:r['releases'].pop()),
                ('wrong-release-owner',lambda r:r['releases'][0].__setitem__('address',1)),('wrong-final-build',lambda r:r['final_snapshot'].__setitem__('ap_return',0)),
                ('failed-transaction',lambda r:r['PL_rows'][0]['completed_snapshot'].__setitem__('s2mm_error',True)),('source',lambda r:r.__setitem__('task_source_sha256','0'*64)),
                ('old-prereq',lambda r:r.__setitem__('hardware_closure_sha256','0'*64)),('lifecycle',lambda r:r.__setitem__('DMA_allocator_restored',False))]:
            altered=copy.deepcopy(good);edit(altered);reject(label,lambda altered=altered:decode(emit(altered)[0]))
        for label,altered in [('chunk-order',text.replace('M429_RESULT_CHUNK=1/','M429_RESULT_CHUNK=0/')),('missing-chunk','\n'.join(x for x in text.splitlines() if not x.startswith('M429_RESULT_CHUNK=0/'))),
                ('duplicate-sha',text+'M429_RESULT_SHA256='+'0'*64+'\n'),('main-rc',text+'M429_DONE gate_rc=1 export_rc=0\n'),('export-rc',text+'M429_DONE gate_rc=0 export_rc=1\n')]:reject(label,lambda altered=altered:decode(altered))
        reject('nonroot-export',lambda:emit(good,root=False))
    pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    control=subprocess.run([pwsh,'-NoProfile','-File',str(HERE/'m429_control04.ps1'),'-Mode','SelfTest'],capture_output=True)
    atomic(ROOT/'tmp/m42904/support_control_stdout.bin',control.stdout,immutable=True);atomic(ROOT/'tmp/m42904/support_control_stderr.bin',control.stderr,immutable=True)
    assert control.returncode==0 and b'M429_CONTROL_SELF_TEST_PASS' in control.stdout
    for name in ('m429_workflow04.py','m429_pl_range.py','m429_support04.py'):
        ast.parse((HERE/name).read_text(encoding='utf-8'),feature_version=(3,10))
    # Actual runner syntax under the explicitly selected distro; no runner execution.
    syntax=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/bin/bash','-n','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/deployment/mage_vl4b/optimization_v1/candidates/M429-late11-visual-PL-numeric-03/run_m429.sh'],capture_output=True)
    atomic(ROOT/'tmp/m42904/support_bash_stdout.bin',syntax.stdout,immutable=True);atomic(ROOT/'tmp/m42904/support_bash_stderr.bin',syntax.stderr,immutable=True)
    assert syntax.returncode==0
    sources={name:sha(HERE/name) for name in ('m429_control04.ps1','m429_workflow04.py','m429_support04.py')}
    record=dict(status='PASS_M429_ACTUAL_EXPORT_DECODER_AND_CONTROL_SUPPORT',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),source_sha256=sources,
        actual_exporter_to_actual_host_full_PASS_and_FAIL=True,negative_checks=rejected,control_intentional_failure_collect_and_parse=True,bash_n=True,
        fixture_raw_bytes=len(raw),fixture_chunks=parsed[3],root_and_pacing_API_explicitly_mocked=True,
        arithmetic_or_model_outputs_not_recomputed=True,board_run=False,hardware_visual_numerics_pass=False,performance_pass=False,temperature_measurement_enabled=False)
    out=BASE/'runs/M429-numeric-support-02/RESULT.json';atomic(out,encoded(record),immutable=True)
    sync('latest_m429_repair_support',dict(status=record['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=record['manifest_sha256']),
        f'## M429 实际export→hostdecode及控制门禁（2026-10-06）\n\nSHA {sha(out)}；实际exporter完整{len(raw)}B/{parsed[3]}块PASS及FAIL原字节经实际host严格裁决，{len(rejected)}项拒绝、控制故意失败始终collect与bash-n通过；root/pacing仅fixture明确模拟，不证明板端权限或新PL数值。未上板，不测温。')
    print('M429_SUPPORT_SYNC',sha(out),len(rejected))

if __name__=='__main__':main()
