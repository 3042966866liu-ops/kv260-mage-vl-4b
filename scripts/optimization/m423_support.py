"""Actual prerequisite/provider plus strict collector, explicit fake CPU fixtures."""
import ast,base64,copy,hashlib,importlib.util,json,subprocess,tempfile
from pathlib import Path
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
import m423_workflow as w

def main():
    pkg=w.PKG;plan=json.loads((pkg/'PLAN.json').read_bytes());digest=sha(pkg/'PACKAGE_MANIFEST.json');b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());rejected=[]
    spec=importlib.util.spec_from_file_location('m423_actual_provider',pkg/'m423_request_visual.py');producer=importlib.util.module_from_spec(spec);spec.loader.exec_module(producer)
    local=copy.deepcopy(plan)
    local['integrated_sources']['visual']['path']=str(ROOT/b['latest_m420_combination_board']['result']);local['integrated_sources']['language']['path']=str(ROOT/b['latest_m421_saved_language_board']['result'])
    packages=['M420-layers12-13-full-visual-02','M417-layer13-saved-reference-02','M418-visual-linear-01','M409-saved-MLP-reference-01','M410-visual-linear-01','M414-layer12-full-visual-01']
    for entry,name in zip(local['visual_reused_packages'],packages):entry['directory']=str(BASE/'candidates'/name);assert sha(Path(entry['directory'])/'PACKAGE_MANIFEST.json')==entry['manifest_sha256']
    actual=producer.verify_sources(local)
    def reject(label,call):
        try:call()
        except (RuntimeError,ValueError,KeyError,AssertionError):rejected.append(label)
        else:raise AssertionError('Invalid evidence accepted: '+label)
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
        p=Path(temp)/'bad.json'
        for name,key,value in [('visual','status','PASS_M414_LAYER12_FULL_VISUAL_FEATURE_QUALITY'),('visual','selected_layers',[12]),('visual','gate_return_code',True),('visual','stable_restored',False),('visual','software_PL_complete_features_exact',False),('language','status','FAIL'),('language','gate_return_code',1),('language','safe_buffers_released',False),('language','stable_overlay_reloaded',False),('language','decision_consistency_pass',False),('language','vision_forward_calls',1)]:
            bad=copy.deepcopy(actual[name]);bad[key]=value;p.write_bytes(encoded(bad));q=copy.deepcopy(local);q['integrated_sources'][name].update(path=str(p),sha256=sha(p));reject('actual-before-resource-'+name+key,lambda q=q:producer.verify_sources(q))
        q=copy.deepcopy(local);q['integrated_sources']['language']['sha256']='0'*64;reject('actual-source-SHA',lambda:producer.verify_sources(q))
    stage=ROOT/'tmp/m42301/component_stage';stage.mkdir(parents=True,exist_ok=False)
    for name,p in [('m423_request_visual.py',pkg/'m423_request_visual.py'),('m423_saved_features.py',pkg/'m423_saved_features.py'),('m422_borrowed_visual.py',pkg/'m422_borrowed_visual.py'),('m411_mlp_binding.py',pkg/'m411_mlp_binding.py'),('board_safety.py',HERE/'board_safety.py'),('test_m422_borrowed_visual.py',HERE/'test_m422_borrowed_visual.py'),('test_m423_provider_component.py',HERE/'test_m423_provider_component.py'),('test_m420_combination.py',ROOT/'tmp/m42002/component_stage/test_m420_combination.py'),('m420_combination.py',ROOT/'tmp/m42002/component_stage/m420_combination.py')]:atomic(stage/name,p.read_bytes(),immutable=True)
    harness='\n'.join(['import json,sys','from pathlib import Path','assert sys.flags.isolated',"root=Path('/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026')","stage=root/'tmp/m42301/component_stage';ref=root/'deployment/mage_vl4b/optimization_v1/candidates/M417-layer13-saved-reference-02'",'sys.path[:0]=[str(stage),str(ref)]','import torch','torch.set_num_threads(1)','from test_m423_provider_component import component',"print('M423_PROVIDER_COMPONENT='+json.dumps(component(root),sort_keys=True),flush=True)",''])
    atomic(stage/'entry.py',harness.encode('utf-8'),immutable=True)
    cp=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-I','-B','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+(stage/'entry.py').relative_to(ROOT).as_posix()],capture_output=True,timeout=90)
    out=ROOT/'tmp/m42301/component';atomic(out/'stdout.txt',cp.stdout,immutable=True);atomic(out/'stderr.txt',cp.stderr,immutable=True)
    if cp.returncode:raise RuntimeError('Isolated actual provider rejected: '+cp.stderr.decode('utf-8',errors='replace')[-2500:])
    lines=[x.split('=',1)[1] for x in cp.stdout.decode('utf-8').splitlines() if x.startswith('M423_PROVIDER_COMPONENT=')];assert len(lines)==1;component=json.loads(lines[0])
    r=copy.deepcopy(actual['language']);r.update(status='PASS_M423_INTEGRATED_VIDEO_NUMERICAL',manifest_sha256=digest,gate_level='integrated-fixed159-visual-language-quality',vision_forward_calls=2,integrated_sources_checked_before_overlay=True,visual_provider_disposed=True,borrowed_buffer_identity_preserved=True,visual_static_cache_invalidated=True,borrowed_extra_DMA=0,integrated_visual=[x['tensor'] for x in plan['features']],integrated_exact_comparisons=[{k:True for k in ('input','visual','token','logits','keys','values','families','grouped_attention_calls','counts')} for _ in range(2)])
    r['fpga_transactions']+=52;r['visual_transactions']=[dict(layer=x['layer'],part=x['part'],start=x['start'],shift=x['shift'],completed=True,completed_snapshot=x['completed_snapshot']) for x in actual['visual']['PL_rows']];r['visual_staging']=actual['visual']['staging']
    w.check(r)
    def export(value):
        raw=encoded(value);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M423_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM423_SAVED_GATE_RC='+str(value['gate_return_code'])+'\n'+''.join(f'M423_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode('ascii')+'\n' for i,p in enumerate(parts))+f'M423_DONE gate_rc={value["gate_return_code"]} export_rc=0\n'
    assert w.decode(export(r))[2]==r
    for label in ('extra-buffer','missing-visual','unfinished-visual','bad-visual-Build','bad-stage','missing-KV','bad-B-logits','bad-original','bad-count','no-provider-release','no-cache-clear','before-resources','lost-comparison'):
        bad=copy.deepcopy(r)
        if label=='extra-buffer':bad['borrowed_extra_DMA']=1
        elif label=='missing-visual':bad['visual_transactions'].pop()
        elif label=='unfinished-visual':bad['visual_transactions'][0]['completed']=False
        elif label=='bad-visual-Build':bad['visual_transactions'][0]['completed_snapshot']['ap_return']=0
        elif label=='bad-stage':bad['visual_staging'][0]['bytes']-=1
        elif label=='missing-KV':bad['samples'][1]['keys'].pop()
        elif label=='bad-B-logits':bad['samples'][1]['logits']['shape']=[1]
        elif label=='bad-original':bad['samples'][0]['logits']['sha256']='0'*64
        elif label=='bad-count':bad['fpga_transactions']-=1
        elif label=='no-provider-release':bad['visual_provider_disposed']=False
        elif label=='no-cache-clear':bad['visual_static_cache_invalidated']=False
        elif label=='before-resources':bad['integrated_sources_checked_before_overlay']=False
        else:bad['integrated_exact_comparisons'][1]['counts']=False
        reject('collector-'+label,lambda bad=bad:w.check(bad))
    text=export(r)
    for label,t in [('missing-chunks',text[:text.index('M423_RESULT_CHUNK=1/')]),('duplicate',text+text),('unordered',text.replace('M423_RESULT_CHUNK=1/','M423_RESULT_CHUNK=0/')),('wrong-export',text.replace('export_rc=0','export_rc=1')),('wrong-SHA',text.replace(hashlib.sha256(encoded(r)).hexdigest(),'0'*64))]:reject(label,lambda t=t:w.decode(t))
    failure=dict(r,status='FAIL',errors=['EXPLICIT synthetic pre-resource failure'],gate_return_code=1,vision_forward_calls=0,model_forward_calls=0,features_verified_before_overlay=False)
    assert w.decode(export(failure))[2]==failure
    for p in pkg.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
    g=(pkg/'m423_gate.py').read_text(encoding='utf-8');assert g.index('verify_sources(plan)')<g.index('import pynq') and g.index("patch(tokenizers,'Tokenizer',original_tokenizer)")>g.index('engine.load()')
    ps='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    control=subprocess.run([ps,'-NoProfile','-File',str(HERE/'m423_control.ps1'),'-Mode','SelfTest'],capture_output=True);assert control.returncode==0 and b'M423_CONTROL_SELF_TEST_PASS' in control.stdout
    bash=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/bin/bash','-n','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+(pkg/'run_m423.sh').relative_to(ROOT).as_posix()],capture_output=True);assert bash.returncode==0
    v=dict(status='PASS_M423_INTEGRATED_SUPPORT_ONLY',manifest_sha256=digest,component=component,component_clean_Linux_I=True,component_rc=cp.returncode,component_stdout_sha256=sha(out/'stdout.txt'),component_stderr_sha256=sha(out/'stderr.txt'),actual_saved_prerequisites_checked_before_resources=True,negative_checks=rejected,synthetic_collector_fixture=True,runner_bash_n=True,control_failure_collection_selftest=True,source_sha256={n:sha(HERE/n) for n in ('m423_prepare.py','m423_request_visual.py','m423_support.py','m423_host_prepare.py','m423_workflow.py','m423_control.ps1','test_m423_provider_component.py')},board_run=False,full_numerical_pass=False,performance_pass=False)
    p=BASE/'runs/M423-integrated-support-01/RESULT.json';atomic(p,encoded(v),immutable=True)
    sync('latest_m423_integrated_support',dict(status=v['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=digest),f'## M423 完整接入组件/回收准备闭合（2026-10-06）\n\nSHA {sha(p)}；实际来源helper资源前核对、隔离WSL-I原24包装/M207四实例覆盖/52包wire/完整特征及二层活动timeout保留，权重Attention和DMA明确fake；原七缓冲真实普通数组几何不等于CMA证明。声明合成完整PASS回收和{len(rejected)}来源/计数/KV/缓存/释放/分块负例，控制故意失败收集及bash-n通过。未上板/完整请求数值或净收益；同COM3一次执行此数值级，不能先性能。')
    print('M423_SUPPORT_SYNC',sha(p),len(rejected))
if __name__=='__main__':main()
