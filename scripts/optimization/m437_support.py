"""Actual timed provider/stream orchestration; isolated explicit fake fixtures."""
import ast,base64,copy,hashlib,json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
import m437_workflow as w
def main():
    stage=ROOT/'tmp/m43701/component_stage';stage.mkdir(parents=True,exist_ok=False)
    oldstage=ROOT/'tmp/m42501/component_stage'
    for p in oldstage.iterdir():
        if p.is_file() and p.suffix=='.py' and p.name!='entry.py':atomic(stage/p.name,p.read_bytes(),immutable=True)
    for name in ('m437_trials.py','m437_sequence.py','m425_environment.py','m432_trials.py','VISUAL_EXPECTED.json','WARM_PROTOCOL.json','PERFORMANCE_PLAN.json','m428_saved_features.py','m433_light_policy.py'):
        p=stage/name
        if p.exists():p.unlink()
        atomic(p,(w.PKG/name).read_bytes(),immutable=True)
    atomic(stage/'test_m437_trials.py',(HERE/'test_m437_trials.py').read_bytes(),immutable=True)
    atomic(stage/'test_m433_light_policy.py',(HERE/'test_m433_light_policy.py').read_bytes(),immutable=True)
    language=json.loads((BASE/'runs/M428-saved-language-board-01/BOARD_RESULT.json').read_bytes())
    for name,value in [('NUMERIC_FIXTURE.json',dict(counts=language['samples'][0]['counts'],transactions=language['transactions'])),('ENVIRONMENT_FIXTURE.json',json.loads((BASE/'runs/M424-environment-board-01/BOARD_RESULT.json').read_bytes()))]:
        atomic(stage/name,encoded(value),immutable=True)
    entry='\n'.join(['import json,sys','from pathlib import Path','assert sys.flags.isolated',"root=Path('/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026')","stage=root/'tmp/m43701/component_stage'",'sys.path[:0]=[str(stage)]','import torch','torch.set_num_threads(1)','from test_m425_environment import main as environment','from test_m437_trials import component as trials','from test_m433_light_policy import component as light','environment()',"print('M437_COMPONENT='+json.dumps(dict(trials=trials(root),light_policy=light()),sort_keys=True),flush=True)",''])
    atomic(stage/'entry.py',entry.encode('utf-8'),immutable=True)
    cp=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-I','-B','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m43701/component_stage/entry.py'],capture_output=True,timeout=150)
    out=ROOT/'tmp/m43701/component';atomic(out/'stdout.bin',cp.stdout,immutable=True);atomic(out/'stderr.bin',cp.stderr,immutable=True)
    if cp.returncode:raise RuntimeError('Actual component rc='+str(cp.returncode)+'; original stdout/stderr bytes saved')
    lines=[x.split('=',1)[1] for x in cp.stdout.decode('utf-8').splitlines() if x.startswith('M437_COMPONENT=')];assert len(lines)==1
    component=json.loads(lines[0]);fixture=json.loads((stage/'TRIALS_FIXTURE_RESULT.json').read_bytes())
    original=json.loads((BASE/'runs/M432-integrated-video-board-01/BOARD_RESULT.json').read_bytes())
    r=copy.deepcopy(original);r.update(fixture)
    # Explicit full-gate synthetic release metadata; stream fixture itself has no real DMA.
    r['released_buffers']=copy.deepcopy(original['released_buffers'])
    # Explicit synthetic metadata follows the actual tested sparse-policy storage rule.
    r['stage_memory']=[x for x in r['stage_memory'] if 'visual-submit:' not in x['label']]
    r['complete_request_numerical_source_sha256']=json.loads((w.PKG/'PERFORMANCE_PLAN.json').read_bytes())['integrated_numerical_sha256']
    r.update(status='PASS_M437_NATURAL_IO_MEASUREMENTS_COLLECTED',manifest_sha256=sha(w.PKG/'PACKAGE_MANIFEST.json'),gate_level='natural-IO-complete-request-performance',gate_return_code=0,errors=[],performance_pass=False,formal_promotion_allowed=False,fpga_transactions=11089,host_calls=9372,logical_calls=9336,additional_cma_requests_allowed=False,temperature_measurement_enabled=False)
    for i,s in enumerate(r['samples']):
        index=0 if s['variant']=='A' else 1;expected=language['samples'][index]
        s['numerical_SHA_after_timer']={k:expected[k] for k in ('input','visual','token','logits','keys','values')}
        s['semantic']['token'].update(knife_score=expected['decision']['knife_score'])
        s['counts']=copy.deepcopy(expected['counts']);s['sampled_memory']=dict(observer_stopped=True,stop_reason=None)
    r['warmup_samples']=r['samples'][:4];r['formal_samples']=r['samples'][4:]
    w.check(r)
    import contextlib,importlib.util,io,tempfile
    from pathlib import Path
    from unittest.mock import patch
    spec=importlib.util.spec_from_file_location('actual_m437_export',w.PKG/'m437_export.py')
    exporter=importlib.util.module_from_spec(spec);spec.loader.exec_module(exporter)
    export_dir=ROOT/'tmp/m43701/export_fixture';export_dir.mkdir(parents=True,exist_ok=False)
    exporter.OUTPUT=export_dir/'BOARD_RESULT.json'
    import os
    writer=next(n for n in ast.parse((w.PKG/'m437_gate.py').read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef) and n.name=='write_json')
    writer_namespace=dict(Path=Path,json=json,os=os)
    exec(compile(ast.Module(body=[writer],type_ignores=[]),str(w.PKG/'m437_gate.py'),'exec'),writer_namespace)
    def payload_bytes(value):
        writer_namespace['write_json'](exporter.OUTPUT,value)
        return exporter.OUTPUT.read_bytes()
    def export(value):
        payload=payload_bytes(value);out=io.StringIO()
        with patch.object(exporter.os,'geteuid',lambda:0,create=True),patch.object(exporter.time,'sleep',lambda *x:None),contextlib.redirect_stdout(out):exporter.emit_saved()
        return out.getvalue()+f'M437_DONE gate_rc={value["gate_return_code"]} export_rc=0\n'
    raw=payload_bytes(r);assert len(raw)<4<<20;assert w.decode(export(r))[2]==r
    log=export_dir/'run.log';log.write_text(export(r),encoding='utf-8');notes=[]
    dest=export_dir/'collected/BOARD_RESULT.json'
    with patch.object(w,'OUT',dest),patch.object(w,'sync',lambda *args:notes.append(args)),contextlib.redirect_stdout(io.StringIO()):w.collect(log)
    assert dest.read_bytes()==raw and len(notes)==1 and notes[0][0]=='latest_m437_warm_board'
    rejected=[]
    def reject(label,fn):
        try:fn()
        except (RuntimeError,ValueError,KeyError,AssertionError):rejected.append(label)
        else:raise AssertionError('Invalid saved evidence accepted: '+label)
    import sys
    helper_spec=importlib.util.spec_from_file_location('m428_saved_features',w.PKG/'m428_saved_features.py')
    helper=importlib.util.module_from_spec(helper_spec);helper_spec.loader.exec_module(helper)
    prior_helper=sys.modules.get('m428_saved_features');sys.modules['m428_saved_features']=helper
    try:
        spec=importlib.util.spec_from_file_location('actual_m437_prerequisite',w.PKG/'m437_prerequisite.py')
        prerequisite=importlib.util.module_from_spec(spec);spec.loader.exec_module(prerequisite)
    finally:
        if prior_helper is None:sys.modules.pop('m428_saved_features',None)
        else:sys.modules['m428_saved_features']=prior_helper
    p=json.loads((w.PKG/'PERFORMANCE_PLAN.json').read_bytes());p['integrated_numerical_result']=str(BASE/'runs/M432-integrated-video-board-01/BOARD_RESULT.json')
    def owned_read_fixture(path,size,digest):
        data=Path(path).read_bytes()
        if len(data)!=size or hashlib.sha256(data).hexdigest()!=digest:raise ValueError('Exact numerical saved SHA differs')
        return data
    with patch.object(prerequisite,'read_owned',owned_read_fixture):
        assert prerequisite.verify(p)==original
        path=export_dir/'invalid_prerequisite.json'
        for key,value in [('gate_return_code',True),('status','FAIL'),('selected_layers',[12,13]),('numerical_pass',False),('safe_buffers_released',False),('stable_overlay_reloaded',False),('visual_provider_disposed',False),('borrowed_extra_DMA',1),('fpga_transactions',1848),('unsafe_buffers_retained',True),('temperature_measurement_enabled',True)]:
            bad=copy.deepcopy(original);bad[key]=value;path.write_bytes(encoded(bad));q=copy.deepcopy(p)
            q.update(integrated_numerical_result=str(path),integrated_numerical_bytes=path.stat().st_size,integrated_numerical_sha256=sha(path))
            reject('prerequisite-'+key,lambda q=q:prerequisite.verify(q))
        q=copy.deepcopy(p);q['integrated_numerical_sha256']='0'*64
        reject('prerequisite-full-SHA',lambda:prerequisite.verify(q))
    for key,value in [('temperature_measurement_enabled',True),('performance_pass',True),('formal_promotion_allowed',True),('fpga_transactions',11088),('host_calls',1),('logical_calls',1),('vision_forward_calls',11),('borrowed_extra_DMA',1),('stable_overlay_reloaded',False),('visual_provider_disposed',False),('safe_buffers_released',False),('full_hashes_after_timers',False),('natural_IO_protocol_sha256','0'*64)]:
        bad=copy.deepcopy(r);bad[key]=value;reject(key,lambda bad=bad:w.check(bad))
    for label in ('missing-KV','bad-logits','bad-count','unsafe','bad-clock','negative-read','wrong-order','missing-stage','unreleased-worker'):
        bad=copy.deepcopy(r);s=bad['samples'][4]
        if label=='missing-KV':s['numerical_SHA_after_timer']['keys'].pop()
        elif label=='bad-logits':s['numerical_SHA_after_timer']['logits']['sha256']='0'*64
        elif label=='bad-count':s['language_physical_observed']=780
        elif label=='unsafe':s['final_snapshot']['ap_ctrl']=0
        elif label=='bad-clock':s['after_environment']['pl_clocks']['pl0_ref']=1
        elif label=='negative-read':s['io_delta']['read_bytes']=-1
        elif label=='wrong-order':s['variant']='B'
        elif label=='missing-stage':s['timing']['stages_ms'].pop('vision')
        else:s['sampled_memory']['observer_stopped']=False
        reject(label,lambda bad=bad:w.check(bad))
    text=export(r)
    for label,t in [('missing-chunks',text[:text.index('M437_RESULT_CHUNK=1/')]),('duplicate',text+text),('unordered',text.replace('M437_RESULT_CHUNK=1/','M437_RESULT_CHUNK=0/')),('export-error',text.replace('export_rc=0','export_rc=1')),('SHA',text.replace(hashlib.sha256(raw).hexdigest(),'0'*64))]:reject(label,lambda t=t:w.decode(t))
    fail=dict(r,status='FAIL',errors=['EXPLICIT synthetic pre-resource failure'],gate_return_code=1,model_forward_calls=0,vision_forward_calls=0);assert w.decode(export(fail))[2]==fail
    from m437_sequence import NaturalSequence,adjudicate,ORDER
    fixture_sample=copy.deepcopy(r['samples'][0]);reference=r['warm_environment_reference']
    def accept(rows):
        seq=NaturalSequence({},reference,clock=lambda:0)
        for i,s in enumerate(rows):seq.before(i);seq.record(s)
        return seq.result
    varied=[]
    for i,v in enumerate(ORDER):
        s=copy.deepcopy(fixture_sample);s.update(index=i+1,variant=v,major_fault_delta=i+3)
        s['io_delta']['read_bytes']=(123+i*71)<<20
        for side in ('before_cache','after_cache'):s[side].update(cache_entries=25 if v=='B' else 26,cache_bytes=62177280 if v=='B' else 66699264)
        varied.append(s)
    assert accept(varied)['preconditioning_completed']
    for label,field,value in [('cache-entry-bound','cache_entries',27),('cache-byte-bound','cache_bytes',66699265),('cache-flag','cache_within_budget',False)]:
        rows=copy.deepcopy(varied);rows[4]['after_cache'][field]=value
        reject(label,lambda rows=rows:accept(rows))
    rows=copy.deepcopy(varied);rows[4]['major_fault_delta']=-1;reject('invalid-fault-counter',lambda:accept(rows))
    rows=copy.deepcopy(varied);rows[4]['timing']['total_ms']=240001;reject('request-budget',lambda:accept(rows))
    seq=NaturalSequence({},reference,clock=lambda:0);reject('formal-before-preconditioning',lambda:seq.before(4))
    seq=NaturalSequence({},reference,clock=lambda:0);seq.recorded=12;reject('thirteenth-request',lambda:seq.before(12))
    def stats(a,b):
        rows=copy.deepcopy(varied[4:])
        for s in rows:s['timing']['total_ms']=a if s['variant']=='A' else b
        return adjudicate(rows)
    assert stats(100000,90000)['performance_pass'] is True
    assert stats(100000,100000)['performance_pass'] is False
    assert stats(100000,110000)['performance_pass'] is False
    for p in w.PKG.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
    g=(w.PKG/'m437_gate.py').read_text(encoding='utf-8');assert g.index('verify_complete_numerical(perf_plan)')<g.index('import pynq')
    envsource=(w.PKG/'m425_environment.py').read_text();assert '/sys/class/thermal' not in envsource and '/sys/class/hwmon' not in envsource and '/sys/bus/iio' not in envsource
    ps='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    control=subprocess.run([ps,'-NoProfile','-File',str(HERE/'m437_control.ps1'),'-Mode','SelfTest'],capture_output=True);assert control.returncode==0 and b'M437_CONTROL_SELF_TEST_PASS' in control.stdout
    bash=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/bin/bash','-n','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+(w.PKG/'run_m437.sh').relative_to(ROOT).as_posix()],capture_output=True);assert bash.returncode==0
    value=dict(status='PASS_M437_ACTUAL_STREAM_NATURAL_IO_HOST_SUPPORT_ONLY',manifest_sha256=sha(w.PKG/'PACKAGE_MANIFEST.json'),component=component,explicit_synthetic_collector=True, actual_gate_writer_exporter_and_atomic_collector=True, root_and_pacing_explicit_fake=True,negative_checks=rejected,synthetic_compact_raw_bytes=len(raw),all_stdout_stderr_preserved_as_bytes=True,component_stdout_sha256=sha(out/'stdout.bin'),component_stderr_sha256=sha(out/'stderr.bin'),no_temperature_reads=True,control_failure_collect=True,Python310_syntax=True,runner_bash_n=True,host_sources={n:sha(HERE/n) for n in ('m437_workflow.py','m437_control.ps1','m437_support.py','m437_sequence.py','test_m437_trials.py')},candidate_remote='/home/ubuntu/m437_natural_IO_candidate_01',evidence_remote='/home/ubuntu/m437_natural_IO_result_01',board_run=False,performance_pass=False)
    p=BASE/'runs/M437-natural-IO-support-01/RESULT.json';atomic(p,encoded(value),immutable=True)
    sync('latest_m437_support',dict(status=value['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=value['manifest_sha256']),f'## M437 完整暖请求组件及回收（2026-10-07）\n\nSHA {sha(p)}；实际后11层provider组件已另存/原stream AST与12次调度、计时后全端点核对/0新增DMA/逐请求计数和观察器复位，fake模型、DMA和环境明确；温度接口未访问。{len(rejected)}合成严格回收负例、原子紧凑记录预算及控制故意失败收集/Python3.10/bash-n通过。未上板或新性能；下一步一次预定4＋8完整暖请求。')
    print('M437_SUPPORT_SYNC',sha(p),len(rejected),len(raw))
if __name__=='__main__':main()
