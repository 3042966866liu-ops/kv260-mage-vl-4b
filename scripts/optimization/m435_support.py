"""Actual observer, original stream orchestration and collector on explicit fixtures."""
import ast
import base64
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
import m435_workflow as w


def main():
    stage=ROOT/'tmp/m43501/component_stage'
    stage.mkdir(parents=True,exist_ok=True)
    oldstage=ROOT/'tmp/m43302/component_stage'
    for p in oldstage.iterdir():
        if p.is_file() and p.suffix=='.py' and p.name!='entry.py':atomic(stage/p.name,p.read_bytes(),immutable=True)
    for n in ('m435_trials.py','m435_io_observer.py','test_m435_io_observer.py','VISUAL_EXPECTED.json','WARM_PROTOCOL.json','PERFORMANCE_PLAN.json','OBSERVATION_PLAN.json','m428_saved_features.py'):
        atomic(stage/n,(w.PKG/n).read_bytes(),immutable=True)
    for n in ('NUMERIC_FIXTURE.json','ENVIRONMENT_FIXTURE.json'):
        atomic(stage/n,(oldstage/n).read_bytes(),immutable=True)
    text=(HERE/'test_m433_trials.py').read_text(encoding='utf-8').replace('import m433_trials as trials','import m435_trials as trials')
    text=text.replace('trials.run(engine,runtime,policy,base,here,here,result,patch,[],provider_proxy)', 'trials.run(engine,runtime,policy,base,here,here,result,patch,[],provider_proxy,observer)')
    text=text.replace("result['all12_requests_completed'] and result['model_forward_calls']==result['vision_forward_calls']==12", "result['all2_requests_completed'] and result['model_forward_calls']==result['vision_forward_calls']==2")
    text=text.replace("result['completed_language_physical']==9372 and result['completed_visual_physical']==1716", "result['completed_language_physical']==1562 and result['completed_visual_physical']==572")
    text=text.replace("assert len(result['warmup_samples'])==4 and len(result['formal_samples'])==8 and not result['transactions']", "assert result['diagnostic_order']=='BB' and not result['transactions']")
    anchor="    original_env,original_io=trials.read_environment,trials.io_snapshot"
    assert text.count(anchor)==1
    text=text.replace(anchor,"""    import m435_io_observer as obs
    plan=json.loads((here/'OBSERVATION_PLAN.json').read_bytes())
    observer=SimpleNamespace(request=0,phase='none',reads=[],snapshots=[])
    def snapshot(label):
        observer.snapshots.append(dict(request=observer.request,label=label))
        if label=='after-language':
            observer.reads.extend(dict(request=observer.request,returned_bytes=x['bytes'],**{k:x[k] for k in ('group','path','offset')}) for x in plan['expected_reads'])
    observer.snapshot=snapshot
    original_counter=obs.counters
    obs.counters=lambda:dict(io={'read_bytes':0,'rchar':0},major=0)
"""+anchor)
    text=text.replace("        trials.read_environment,trials.io_snapshot=original_env,original_io", "        obs.counters=original_counter\n        trials.read_environment,trials.io_snapshot=original_env,original_io")
    text=text.replace('actual_trials_12_sequence=True','actual_BB_trials_sequence=True')
    atomic(stage/'test_m435_trials.py',text.encode(),immutable=True)
    entry="""import json,sys,unittest
from pathlib import Path
assert sys.flags.isolated
root=Path('/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026')
here=root/'tmp/m43501/component_stage'
sys.path.insert(0,str(here))
from test_m435_io_observer import ObserverTests
tests=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ObserverTests))
assert tests.wasSuccessful() and tests.testsRun==15 and not tests.skipped
import torch
torch.set_num_threads(1)
from test_m435_trials import component
print('M435_COMPONENT='+json.dumps(dict(observer_tests=tests.testsRun,trials=component(root)),sort_keys=True),flush=True)
"""
    atomic(stage/'entry.py',entry.encode(),immutable=True)
    saved=ROOT/'tmp/m43501/component/stdout.bin'
    if saved.exists():
        stdout=saved.read_bytes();stderr=saved.with_name('stderr.bin').read_bytes()
        assert b'Ran 15 tests' in stderr and b'\nOK\n' in stderr
    else:
        cp=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-I','-B','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m43501/component_stage/entry.py'],capture_output=True,timeout=120)
        atomic(saved,cp.stdout,immutable=True);atomic(saved.with_name('stderr.bin'),cp.stderr,immutable=True)
        if cp.returncode:raise RuntimeError('Actual component rc='+str(cp.returncode)+'; original receipts preserved')
        stdout=cp.stdout
    lines=[x.split('=',1)[1] for x in stdout.decode().splitlines() if x.startswith('M435_COMPONENT=')]
    assert len(lines)==1;component=json.loads(lines[0])
    fixture=json.loads((stage/'TRIALS_FIXTURE_RESULT.json').read_bytes())
    r=json.loads((ROOT/'tmp/m43305/export_fixture/collected/BOARD_RESULT.json').read_bytes());r.update(fixture)
    r['released_buffers']=list(reversed(r['allocated_buffers']))  # Explicit collector lifecycle fixture, not model test cleanup.
    for k in ('warmup_samples','formal_samples'):
        r.pop(k,None)  # These old protocol fixtures are not part of the new two-request result.
    r.update(status='PASS_M435_BB_IO_DIAGNOSTIC',manifest_sha256=sha(w.PKG/'PACKAGE_MANIFEST.json'),gate_level='fixed-BB-file-IO-residency-diagnostic',gate_return_code=0,errors=[],fpga_transactions=2135,host_calls=1562,logical_calls=1556,observer_checked_before_overlay=True,io_observer_hooks_restored=True)
    language=json.loads((BASE/'runs/M428-saved-language-board-01/BOARD_RESULT.json').read_bytes())
    for s in r['samples']:
        expected=language['samples'][1]
        s['numerical_SHA_after_timer']={k:expected[k] for k in ('input','visual','token','logits','keys','values')}
        s['semantic']['token']['knife_score']=expected['decision']['knife_score']
        s['counts']=expected['counts'];s['sampled_memory']=dict(observer_stopped=True,stop_reason=None)
    plan=json.loads((w.PKG/'OBSERVATION_PLAN.json').read_bytes())
    reads=[dict(request=n,phase='vision' if x['group']=='visual' else 'prefill',group=x['group'],path=x['path'],offset=x['offset'],requested_bytes=x['bytes'],returned_bytes=x['bytes'],elapsed_ns_diagnostic=1,io={'read_bytes':0},major=0) for n in (1,2) for x in plan['expected_reads']]
    snapshots=[]
    for n in (1,2):
        for label in plan['mincore_boundaries']:
            rows=[]
            for x in sorted(plan['files'],key=lambda x:x['path']):
                bits=b'\x03'
                rows.append(dict(path=x['path'],group=x['group'],identity=[1],pages=2,page_bytes=4096,resident_pages=2,permission_proven=True,bits_b64=base64.b64encode(bits).decode(),bits_sha256=hashlib.sha256(bits).hexdigest()))
            snapshots.append(dict(request=n,label=label,files=rows,counters=dict(io={'read_bytes':0},major=0)))
    r['read_observation']=dict(reads=reads,decodes=[dict(request=n,name='explicit synthetic decode',io={'read_bytes':0}) for n in (1,2)],snapshots=snapshots,cache_eviction=False,additional_weight_cache=False)
    r['observer_component_tests']=dict(run=15,skipped=0,success=True,output='explicit synthetic board proof; actual Linux tests separately')
    r['linux_residency_probe']=dict(sparse_initial_resident=0,buffered_write_resident=1,fixture_removed=True,first_page_observed=True,maps_and_fds_closed=True)
    assert w.check(r)==r
    export_dir=ROOT/'tmp/m43501/export_fixture03';export_dir.mkdir(parents=True,exist_ok=False)
    spec=importlib.util.spec_from_file_location('actual_m435_export',w.PKG/'m435_export.py');exporter=importlib.util.module_from_spec(spec);spec.loader.exec_module(exporter)
    exporter.OUTPUT=export_dir/'BOARD_RESULT.json'
    def export(value):
        exporter.OUTPUT.write_bytes(encoded(value));out=io.StringIO()
        with patch.object(exporter.os,'geteuid',lambda:0,create=True),patch.object(exporter.time,'sleep',lambda *unused:None),contextlib.redirect_stdout(out):exporter.emit_saved()
        return out.getvalue()+f'M435_DONE gate_rc={value["gate_return_code"]} export_rc=0\n'
    good=export(r);assert w.decode(good)[2]==r
    log=export_dir/'run.log';log.write_text(good,encoding='utf-8');notes=[];dest=export_dir/'collected/BOARD_RESULT.json'
    with patch.object(w,'OUT',dest),patch.object(w,'sync',lambda *args:notes.append(args)),contextlib.redirect_stdout(io.StringIO()):w.collect(log)
    assert dest.read_bytes()==encoded(r) and notes[0][0]=='latest_m435_IO_board'
    rejected=[]
    def reject(label,fn):
        try:fn()
        except (RuntimeError,ValueError,AssertionError,KeyError):rejected.append(label)
        else:raise AssertionError('Invalid result accepted:'+label)
    for key,value in [('fpga_transactions',2134),('visual_provider_disposed',False),('io_observer_hooks_restored',False),('observer_checked_before_overlay',False),('temperature_measurement_enabled',True),('performance_pass',True),('host_calls',1),('safe_buffers_released',False),('all2_requests_completed',False)]:
        bad=copy.deepcopy(r);bad[key]=value;reject(key,lambda bad=bad:w.check(bad))
    for label in ('window','missing-read','wrong-order','permission','bitmap','boundary','probe','tests','KV','unsafe'):
        bad=copy.deepcopy(r)
        if label=='window':bad['read_observation']['reads'][0]['offset']+=16
        elif label=='missing-read':bad['read_observation']['reads'].pop()
        elif label=='wrong-order':bad['samples'][0]['variant']='A'
        elif label=='permission':bad['read_observation']['snapshots'][0]['files'][0]['permission_proven']=False
        elif label=='bitmap':bad['read_observation']['snapshots'][0]['files'][0]['bits_sha256']='0'*64
        elif label=='boundary':bad['read_observation']['snapshots'][0]['label']='unexpected'
        elif label=='probe':bad['linux_residency_probe']['sparse_initial_resident']=1
        elif label=='tests':bad['observer_component_tests']['skipped']=1
        elif label=='KV':bad['samples'][0]['numerical_SHA_after_timer']['keys'].pop()
        else:bad['samples'][0]['final_snapshot']['ap_ctrl']=0
        reject(label,lambda bad=bad:w.check(bad))
    for label,text in [('missing-chunks',good[:good.index('M435_RESULT_CHUNK=1/')]),('duplicate',good+good),('unordered',good.replace('M435_RESULT_CHUNK=1/','M435_RESULT_CHUNK=0/')),('export-error',good.replace('export_rc=0','export_rc=1')),('SHA',good.replace(hashlib.sha256(encoded(r)).hexdigest(),'0'*64))]:reject(label,lambda text=text:w.decode(text))
    fail=dict(r,status='FAIL',gate_return_code=1,errors=['Explicit failure fixture']);assert w.decode(export(fail))[2]==fail
    # Actual unchanged-file assembler on self-owned staging.
    old=BASE/'candidates/M433-late11-complete-request-warm-01'
    with tempfile.TemporaryDirectory(prefix='m435-assembly-',dir=ROOT/'tmp') as temp:
        src=Path(temp)/'old';dst=Path(temp)/'new';shutil.copytree(old,src);dst.mkdir()
        for n in w.upload_names():shutil.copyfile(w.PKG/n,dst/n)
        assembly=(w.PKG/'m435_assemble.py').read_text().replace("Path('/home/ubuntu/m433_late11_warm_candidate_01')",'Path('+repr(src.as_posix())+')')
        with patch.object(sys,'argv',[str(dst/'m435_assemble.py'),sha(w.PKG/'PACKAGE_MANIFEST.json')]),contextlib.redirect_stdout(io.StringIO()):exec(compile(assembly,str(w.PKG/'m435_assemble.py'),'exec'),dict(__file__=str(dst/'m435_assemble.py')))
        assert {p.name:sha(p) for p in dst.iterdir()}=={p.name:sha(p) for p in w.PKG.iterdir()}
    # Every referenced non-standard module must resolve to the same SHA, recursively.
    closure=json.loads((w.PKG/'DEPENDENCY_CLOSURE.json').read_bytes());modules={p.stem:p for p in w.PKG.glob('*.py')}
    for folder in (BASE/'candidates').iterdir():
        if folder.is_dir():
            for p in folder.glob('*.py'):
                if p.stem in closure['files'] and sha(p)==closure['files'][p.stem]:modules.setdefault(p.stem,p)
    for p in HERE.glob('*.py'):
        if p.stem in closure['files'] and sha(p)==closure['files'][p.stem]:modules.setdefault(p.stem,p)
    for row in json.loads((w.PKG/'SOURCE_CLOSURE.json').read_bytes())['files']:
        for p in (ROOT/row['path'],ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'/row['path']):
            if p.is_file() and p.stem in closure['files'] and sha(p)==closure['files'][p.stem]:modules.setdefault(p.stem,p)
    seen=set();missing=[]
    def visit(n):
        if n in seen:return
        seen.add(n);assert sha(modules[n])==closure['files'][n]
        tree=ast.parse(modules[n].read_text(encoding='utf-8-sig'),feature_version=(3,10))
        imports=[a.name.split('.')[0] for node in ast.walk(tree) if isinstance(node,ast.Import) for a in node.names]+[(node.module or '').split('.')[0] for node in ast.walk(tree) if isinstance(node,ast.ImportFrom)]
        for dep in imports:
            if dep in modules:visit(dep)
            elif len(dep)>1 and dep[0]=='m' and dep[1].isdigit():missing.append((n,dep))
    for n in ('m435_gate','m435_entry','m435_export','m435_assemble'):visit(n)
    assert not missing, repr(missing)
    ps='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    ctrl=subprocess.run([ps,'-NoProfile','-File',str(HERE/'m435_control.ps1'),'-Mode','SelfTest'],capture_output=True)
    assert ctrl.returncode==0 and b'M435_CONTROL_SELF_TEST_PASS' in ctrl.stdout
    record=dict(status='PASS_M435_IO_OBSERVER_AND_HOST_FIXTURES_ONLY',manifest_sha256=sha(w.PKG/'PACKAGE_MANIFEST.json'),
                component=component,collector_negative_checks=rejected,actual_export_collect=True,actual_assembly=True,recursive_modules=len(seen),missing=missing,
                stdout_sha256=sha(ROOT/'tmp/m43501/component/stdout.bin'),stderr_sha256=sha(ROOT/'tmp/m43501/component/stderr.bin'),
                source_sha256={n:sha(HERE/n) for n in ('m435_control.ps1','m435_workflow.py','m435_io_observer.py','test_m435_io_observer.py','m435_support.py')},
                board_run=False,numerical_pass=False,performance_pass=False,temperature_measurement_enabled=False,
                note='Linux observer tests real owned files; stream/model/DMA/counters/residency collector fixtures explicit synthetic; not board proof')
    out=BASE/'runs/M435-IO-observation-support-01/RESULT.json';atomic(out,encoded(record),immutable=True)
    sync('latest_m435_IO_support',dict(status=record['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=record['manifest_sha256']),f'## M435 窄读取观察配套检查（2026-10-07）\n\nSHA {sha(out)}；Linux实际15项小文件/驻留/FD关闭与原stream固定BB组件通过，明确fake模型/DMA/窗口记录/回收驻留数据。真实export/collector原子字节、{len(rejected)}负例、assembler完整同SHA及递归missing=0/控制故意失败收集自测。未上板；下一步COM3一次授权确认、manifest-first差量900B上传，然后单次固定BB诊断；不性能/清缓存/测温。')
    print('M435_SUPPORT_SYNC',sha(out),len(rejected))


if __name__=='__main__':main()
