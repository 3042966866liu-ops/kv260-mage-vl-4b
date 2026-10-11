"""Restore the original post-load tokenizer boundary; one closed failing level."""
import ast,json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
def main():
    old=BASE/'candidates/M415-saved-feature-language-03';pkg=BASE/'candidates/M415-saved-feature-language-04'
    if pkg.exists():raise RuntimeError('Immutable tokenizer repair exists')
    failed=BASE/'runs/M415-saved-feature-language-board-02/BOARD_RESULT.json';r=json.loads(failed.read_bytes())
    assert sha(failed)=='bc616d877d6775e3e4d946d6666c2ffc4e40e3ae6631e2db4406ebc9bf430e21' and r['errors']==['RuntimeError: Unexpected additional tokenizer parse'] and r['model_forward_calls']==0 and r['fpga_transactions']==1 and len(r['allocated_buffers'])==len(r['released_buffers'])==7 and r['safe_buffers_released'] and r['stable_overlay_reloaded'] and not r['unsafe_buffers_retained']
    closure=BASE/'runs/M415-saved-feature-language-closure-02/RESULT.json';assert sha(closure)=='276a611bc6c4b2d8f6d15bcfd6b9c1f82f2e1d74cdbeffb0ba8f8af0e0bf3fcc'
    source=(old/'m415_gate.py').read_text(encoding='utf-8');anchor='        from m415_trials import run';assert source.count(anchor)==1
    source=source.replace(anchor,"        # Original M368 restores loader-only proxy before the original request tokenizer.\n        patch(tokenizers,'Tokenizer',original_tokenizer)\n        result['request_tokenizer_restored_before_prefill']=tokenizers.Tokenizer is original_tokenizer\n"+anchor).replace('/home/ubuntu/m415_saved_feature_language_02','/home/ubuntu/m415_saved_feature_language_03')
    pkg.mkdir()
    for row in json.loads((old/'PACKAGE_MANIFEST.json').read_bytes())['files']:
        if row['path']=='SHA256SUMS':continue
        assert sha(old/row['path'])==row['sha256'];data=(old/row['path']).read_bytes()
        if row['path']=='m415_gate.py':data=source.encode('utf-8')
        elif row['path']=='m415_assemble.py':data=data.decode('utf-8').replace('m415_saved_feature_candidate_02','m415_saved_feature_candidate_03').replace('ffb00d21e1c7bfbc65850ca59e414ba276f700d18449eaa7aa04b817437668e0',sha(old/'PACKAGE_MANIFEST.json')).encode('utf-8')
        elif row['path'] in ('m415_export.py','run_m415.sh'):data=data.decode('utf-8').replace('/home/ubuntu/m415_saved_feature_language_02','/home/ubuntu/m415_saved_feature_language_03').encode('utf-8')
        atomic(pkg/row['path'],data,immutable=True)
    for p in pkg.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
    files=sorted(pkg.iterdir());atomic(pkg/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in files).encode('ascii'),immutable=True)
    files=sorted(pkg.iterdir());manifest=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(pkg/'PACKAGE_MANIFEST.json',encoded(manifest),immutable=True)
    workflow=(HERE/'m415_workflow04.py').read_text(encoding='utf-8').replace('M415-saved-feature-language-03','M415-saved-feature-language-04').replace("ROOT/'tmp/m41503'","ROOT/'tmp/m41504'").replace('candidates/M415-saved-feature-language-02/PACKAGE_MANIFEST.json','candidates/M415-saved-feature-language-03/PACKAGE_MANIFEST.json').replace('runs/M415-saved-feature-transfer-03/RESULT.json','runs/M415-saved-feature-transfer-04/RESULT.json').replace('runs/M415-saved-feature-language-board-02/BOARD_RESULT.json','runs/M415-saved-feature-language-board-03/BOARD_RESULT.json')
    workflow=workflow.replace("'features_verified_before_overlay','head_AST_checked_before_overlay'","'features_verified_before_overlay','head_AST_checked_before_overlay','request_tokenizer_restored_before_prefill'")
    atomic(HERE/'m415_workflow05.py',workflow.encode('utf-8'),immutable=True)
    control=(HERE/'m415_control04.ps1').read_text(encoding='utf-8').replace('M415-saved-feature-language-03','M415-saved-feature-language-04').replace('m415_saved_feature_candidate_03','m415_saved_feature_candidate_04').replace('tmp/m41503','tmp/m41504').replace('m415_workflow04.py','m415_workflow05.py').replace('candidates/M415-saved-feature-language-02/PACKAGE_MANIFEST.json','candidates/M415-saved-feature-language-03/PACKAGE_MANIFEST.json').replace('runs/M415-saved-feature-language-board-02/BOARD_RESULT.json','runs/M415-saved-feature-language-board-03/BOARD_RESULT.json')
    atomic(HERE/'m415_control05.ps1',control.encode('utf-8'),immutable=True)
    close=(HERE/'m415_close02.py').read_text(encoding='utf-8').replace('from m415_workflow04 import check','from m415_workflow05 import check').replace('runs/M415-saved-feature-language-closure-02/RESULT.json','runs/M415-saved-feature-language-closure-03/RESULT.json').replace('/home/ubuntu/m415_saved_feature_language_02','/home/ubuntu/m415_saved_feature_language_03')
    atomic(HERE/'m415_close03.py',close.encode('utf-8'),immutable=True)
    value=dict(status='PASS_M415_ORIGINAL_POST_LOAD_TOKENIZER_BOUNDARY_REPAIR',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),prior_raw_sha256=sha(failed),prior_closure_sha256=sha(closure),
        previous_model_and_visual_forwards_zero=True,previous_legal_minimal_physical_calls=1,previous_all7_buffers_released=True,previous_stable_restored=True,
        restore_same_original_Tokenizer_before_request=True,original_math_snapshot_trial_unchanged=True,trial_sha256=sha(pkg/'m415_trials.py'),board_run=False)
    p=BASE/'runs/M415-tokenizer-preparation-04/RESULT.json';atomic(p,encoded(value),immutable=True)
    sync('latest_m415_saved_feature_preparation',dict(status=value['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=value['manifest_sha256']),
        f'## M415 原request分词边界恢复（2026-10-06）\n\nSHA {sha(p)}；原raw {sha(failed)}及闭合 {sha(closure)}保持。03 legal minimal1次、安全释放7块及稳定恢复，0语言/视觉；旧M368本来在load之后恢复原Tokenizer，手动接特征漏了恢复。04仅补同一原类恢复，数学/提示/输入/快照trial不变，新结果目录保留全部旧失败。真实原Tokenizer组件复现后才同级重试。')
    cmd=['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-B','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/scripts/optimization/m415_tokenizer_component07.py']
    checked=subprocess.run(cmd,capture_output=True)
    if checked.returncode or b'M415_TOKENIZER_COMPONENT_PASS' not in checked.stdout:raise RuntimeError((checked.stdout+checked.stderr).decode('utf-8',errors='replace'))
    component=BASE/'runs/M415-tokenizer-component-07/RESULT.json';proof=json.loads(component.read_bytes());assert proof['actual_missing_restore_failure_reproduced'] and proof['restored_original_request_parse'] and proof['exact159_original_token_ids']
    pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    checked=subprocess.run([pwsh,'-NoProfile','-File',str(HERE/'m415_control05.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8');assert checked.returncode==0 and 'M415_CONTROL_SELF_TEST_PASS' in checked.stdout
    checked=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/bin/bash','-n','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+(pkg/'run_m415.sh').relative_to(ROOT).as_posix()],capture_output=True);assert checked.returncode==0
    prior=BASE/'runs/M415-environment-path-support-06/RESULT.json';oldproof=json.loads(prior.read_bytes())
    support=dict(oldproof,status='PASS_M415_REAL_TOKENIZER_BOUNDARY_AND_DEPENDENCY_SUPPORT',manifest_sha256=value['manifest_sha256'],actual_tokenizer_component_sha256=sha(component),
        prior_support_sha256=sha(prior),new_math_forward_component_not_repeated=True,
        source_sha256={n:sha(HERE/n) for n in ('m415_saved_features.py','m415_trials02.py','m415_workflow05.py','m415_control05.ps1','m415_close03.py','m415_tokenizer_component07.py','m415_tokenizer_repair04.py')})
    p=BASE/'runs/M415-tokenizer-support-07/RESULT.json';atomic(p,encoded(support),immutable=True)
    sync('latest_m415_saved_feature_support',dict(status=support['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=support['manifest_sha256']),
        f'## M415 实际Tokenizer衔接组件闭合（2026-10-06）\n\nSHA {sha(p)}；真实库/11,422,064B实际冻结tokenizer JSON与原render/tokenize：同对象load复用、实际第三解析保护失败、原类恢复后159IDs精确一致；组件SHA {sha(component)}，WSL CPU非板端质量。原数学/快照/收集检查不重跑，控制/bash-n通过。04只调回原post-load边界，无视觉，允许同级差量上传和一次运行。')
    print('M415_TOKENIZER_REPAIR_READY',sha(p),value['manifest_sha256'])
if __name__=='__main__':main()
