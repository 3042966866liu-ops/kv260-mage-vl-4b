"""Actual timed provider/stream orchestration; isolated explicit fake fixtures."""
import ast,base64,copy,hashlib,json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
import m425_workflow as w
def main():
    stage=ROOT/'tmp/m42501/component_stage';stage.mkdir(parents=True,exist_ok=False)
    oldstage=ROOT/'tmp/m42301/component_stage'
    for p in oldstage.iterdir():
        if p.is_file() and p.suffix=='.py' and p.name!='entry.py':atomic(stage/p.name,p.read_bytes(),immutable=True)
    for name in ('m425_trials.py','m425_timed_visual.py','m425_warm.py','m425_environment.py','m423_trials.py','m369_light_policy.py','VISUAL_EXPECTED.json','WARM_PROTOCOL.json','PERFORMANCE_PLAN.json'):atomic(stage/name,(w.PKG/name).read_bytes(),immutable=True)
    for name in ('test_m425_trials.py','test_m425_warm.py','test_m425_environment.py','memory_lifecycle.py','m368_video_contract.py'):atomic(stage/name,(HERE/name).read_bytes(),immutable=True)
    atomic(stage/'m368_stage_policy.py',(BASE/'candidates/M368-staged-video-03/m368_stage_policy.py').read_bytes(),immutable=True)
    language=json.loads((BASE/'runs/M421-saved-language-board-01/BOARD_RESULT.json').read_bytes())
    atomic(stage/'NUMERIC_FIXTURE.json',encoded(dict(counts=language['samples'][0]['counts'])),immutable=True)
    env=json.loads((BASE/'runs/M424-environment-board-01/BOARD_RESULT.json').read_bytes());atomic(stage/'ENVIRONMENT_FIXTURE.json',encoded(env),immutable=True)
    source=(stage/'test_m423_provider_component.py').read_text(encoding='utf-8')
    source=source.replace('from m423_request_visual import VisualProvider','from m425_timed_visual import TimedVisualProvider as VisualProvider')
    source=source.replace('provider=VisualProvider.__new__(VisualProvider);','provider=VisualProvider.__new__(VisualProvider);provider.enabled=True;')
    source=source.replace("        provider.dispose();assert provider.disposed and provider.targets is None","        submitted.clear();provider.result['visual_transactions']=[]\n        with torch.inference_mode():assert tensor(provider(1))==expected[1]\n        assert len(submitted)==52 and provider.current_owner is None\n        provider.dispose();assert provider.disposed and provider.targets is None")
    atomic(stage/'test_m425_provider.py',source.encode('utf-8'),immutable=True)
    entry='\n'.join(['import json,sys','from pathlib import Path','assert sys.flags.isolated',"root=Path('/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026')","stage=root/'tmp/m42501/component_stage';ref=root/'deployment/mage_vl4b/optimization_v1/candidates/M417-layer13-saved-reference-02'",'sys.path[:0]=[str(stage),str(ref)]','import torch','torch.set_num_threads(1)','from test_m425_environment import main as environment','from test_m425_warm import main as warm','from test_m425_provider import component as provider','from test_m425_trials import component as trials','environment();warm()',"print('M425_COMPONENT='+json.dumps(dict(provider=provider(root),trials=trials(root)),sort_keys=True),flush=True)",''])
    atomic(stage/'entry.py',entry.encode('utf-8'),immutable=True)
    ref=BASE/'candidates/M417-layer13-saved-reference-02';manifest=json.loads((ref/'PACKAGE_MANIFEST.json').read_bytes())
    plan=json.loads((w.PKG/'PLAN.json').read_bytes());refrow=next(x for x in plan['visual_reused_packages'] if 'm417_' in x['directory'])
    assert sha(ref/'PACKAGE_MANIFEST.json')==refrow['manifest_sha256']
    for row in manifest['files']:assert sha(ref/row['path'])==row['sha256']
    cp=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-I','-B','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/tmp/m42501/component_stage/entry.py'],capture_output=True,timeout=150)
    out=ROOT/'tmp/m42501/component';atomic(out/'stdout.bin',cp.stdout,immutable=True);atomic(out/'stderr.bin',cp.stderr,immutable=True)
    if cp.returncode:raise RuntimeError('Actual component rc='+str(cp.returncode)+'; original stdout/stderr bytes saved')
    lines=[x.split('=',1)[1] for x in cp.stdout.decode('utf-8').splitlines() if x.startswith('M425_COMPONENT=')];assert len(lines)==1
    component=json.loads(lines[0]);fixture=json.loads((stage/'TRIALS_FIXTURE_RESULT.json').read_bytes())
    original=json.loads((BASE/'runs/M423-integrated-video-board-01/BOARD_RESULT.json').read_bytes())
    r=copy.deepcopy(original);r.update(fixture)
    r.update(status='PASS_M425_CONTROLLED_WARM_MEASUREMENTS_COLLECTED',manifest_sha256=sha(w.PKG/'PACKAGE_MANIFEST.json'),gate_level='controlled-warm-complete-request-performance',gate_return_code=0,errors=[],performance_pass=False,formal_promotion_allowed=False,fpga_transactions=9685,host_calls=9372,logical_calls=9336,additional_cma_requests_allowed=False,temperature_measurement_enabled=False)
    for i,s in enumerate(r['samples']):
        index=0 if s['variant']=='A' else 1;expected=language['samples'][index]
        s['numerical_SHA_after_timer']={k:expected[k] for k in ('input','visual','token','logits','keys','values')}
        s['semantic']['token'].update(knife_score=expected['decision']['knife_score'])
        s['counts']=copy.deepcopy(expected['counts']);s['sampled_memory']=dict(observer_stopped=True,stop_reason=None)
    r['warmup_samples']=r['samples'][:4];r['formal_samples']=r['samples'][4:]
    w.check(r)
    def export(value):
        raw=json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8');parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M425_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM425_SAVED_GATE_RC='+str(value['gate_return_code'])+'\n'+''.join(f'M425_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode('ascii')+'\n' for i,p in enumerate(parts))+f'M425_DONE gate_rc={value["gate_return_code"]} export_rc=0\n'
    raw=json.dumps(r,separators=(',',':')).encode();assert len(raw)<4<<20;assert w.decode(export(r))[2]==r
    rejected=[]
    def reject(label,fn):
        try:fn()
        except (RuntimeError,ValueError,KeyError,AssertionError):rejected.append(label)
        else:raise AssertionError('Invalid saved evidence accepted: '+label)
    for key,value in [('temperature_measurement_enabled',True),('performance_pass',True),('formal_promotion_allowed',True),('fpga_transactions',9684),('host_calls',1),('logical_calls',1),('vision_forward_calls',11),('borrowed_extra_DMA',1),('stable_overlay_reloaded',False),('visual_provider_disposed',False),('safe_buffers_released',False),('full_hashes_after_timers',False),('warm_protocol_sha256','0'*64)]:
        bad=copy.deepcopy(r);bad[key]=value;reject(key,lambda bad=bad:w.check(bad))
    for label in ('missing-KV','bad-logits','bad-count','unsafe','bad-clock','cold-read','wrong-order','missing-stage','unreleased-worker'):
        bad=copy.deepcopy(r);s=bad['samples'][4]
        if label=='missing-KV':s['numerical_SHA_after_timer']['keys'].pop()
        elif label=='bad-logits':s['numerical_SHA_after_timer']['logits']['sha256']='0'*64
        elif label=='bad-count':s['language_physical_observed']=780
        elif label=='unsafe':s['final_snapshot']['ap_ctrl']=0
        elif label=='bad-clock':s['after_environment']['pl_clocks']['pl0_ref']=1
        elif label=='cold-read':s['io_delta']['read_bytes']=1048577
        elif label=='wrong-order':s['variant']='B'
        elif label=='missing-stage':s['timing']['stages_ms'].pop('vision')
        else:s['sampled_memory']['observer_stopped']=False
        reject(label,lambda bad=bad:w.check(bad))
    text=export(r)
    for label,t in [('missing-chunks',text[:text.index('M425_RESULT_CHUNK=1/')]),('duplicate',text+text),('unordered',text.replace('M425_RESULT_CHUNK=1/','M425_RESULT_CHUNK=0/')),('export-error',text.replace('export_rc=0','export_rc=1')),('SHA',text.replace(hashlib.sha256(raw).hexdigest(),'0'*64))]:reject(label,lambda t=t:w.decode(t))
    fail=dict(r,status='FAIL',errors=['EXPLICIT synthetic pre-resource failure'],gate_return_code=1,model_forward_calls=0,vision_forward_calls=0);assert w.decode(export(fail))[2]==fail
    for p in w.PKG.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
    g=(w.PKG/'m425_gate.py').read_text(encoding='utf-8');assert g.index("if sha256(p)!=perf_plan['integrated_numerical_sha256']")<g.index('import pynq')
    envsource=(w.PKG/'m425_environment.py').read_text();assert '/sys/class/thermal' not in envsource and '/sys/class/hwmon' not in envsource and '/sys/bus/iio' not in envsource
    ps='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    control=subprocess.run([ps,'-NoProfile','-File',str(HERE/'m425_control.ps1'),'-Mode','SelfTest'],capture_output=True);assert control.returncode==0 and b'M425_CONTROL_SELF_TEST_PASS' in control.stdout
    bash=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/bin/bash','-n','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+(w.PKG/'run_m425.sh').relative_to(ROOT).as_posix()],capture_output=True);assert bash.returncode==0
    value=dict(status='PASS_M425_OFFLINE_TIMED_PROVIDER_STREAM_RECOVERY',manifest_sha256=sha(w.PKG/'PACKAGE_MANIFEST.json'),component=component,explicit_synthetic_collector=True,negative_checks=rejected,synthetic_compact_raw_bytes=len(raw),all_stdout_stderr_preserved_as_bytes=True,component_stdout_sha256=sha(out/'stdout.bin'),component_stderr_sha256=sha(out/'stderr.bin'),no_temperature_reads=True,control_failure_collect=True,Python310_syntax=True,runner_bash_n=True,source_sha256={n:sha(HERE/n) for n in ('m425_workflow.py','m425_control.ps1','m425_support.py')},board_run=False,performance_pass=False)
    p=BASE/'runs/M425-performance-support-01/RESULT.json';atomic(p,encoded(value),immutable=True)
    sync('latest_m425_performance_support',dict(status=value['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=value['manifest_sha256']),f'## M425 完整暖请求组件及回收（2026-10-06）\n\nSHA {sha(p)}；实际四绑定/原stream AST与12次调度、计时后全端点核对/0新增DMA/逐请求计数和观察器复位，fake模型、DMA和环境明确；温度接口未访问。{len(rejected)}合成严格回收负例、原子紧凑记录预算及控制故意失败收集/Python3.10/bash-n通过。未上板或新性能；下一步一次预定4＋8完整暖请求。')
    print('M425_SUPPORT_SYNC',sha(p),len(rejected),len(raw))
if __name__=='__main__':main()
