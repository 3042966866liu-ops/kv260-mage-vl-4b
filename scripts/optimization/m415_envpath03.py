"""Repair only the closed, zero-Overlay environment-runner location failure."""
import ast,json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
def main():
    old=BASE/'candidates/M415-saved-feature-language-02';pkg=BASE/'candidates/M415-saved-feature-language-03'
    if pkg.exists():raise RuntimeError('Immutable environment-path repair exists')
    failed=BASE/'runs/M415-saved-feature-language-board-01/BOARD_RESULT.json';r=json.loads(failed.read_bytes())
    assert sha(failed)=='0ebaed5449998ea753b24baf25d10a4571e11ce9dac70307ef30f82b7aa459f1' and r['status']=='FAIL' and r['fpga_transactions']==0 and r['model_forward_calls']==0 and not r['overlay_loaded'] and not r['allocated_buffers'] and not r['unsafe_buffers_retained']
    closure=BASE/'runs/M415-saved-feature-language-closure-01/RESULT.json';assert sha(closure)=='304fe5ac6868a7e6c309972e3295778b888879a0c173fb45770371a3d90dafe1'
    source=(old/'m415_gate.py').read_text(encoding='utf-8');anchor="str(HERE/'m120_board_env_preflight.py')";assert source.count(anchor)==2
    source=source.replace(anchor,"str(reuse/'m120_board_env_preflight.py')").replace("Path('/home/ubuntu/m415_saved_feature_language_01')","Path('/home/ubuntu/m415_saved_feature_language_02')")
    reuse=BASE/'candidates/M368-staged-video-03';m=json.loads((reuse/'PACKAGE_MANIFEST.json').read_bytes());env=next(x for x in m['files'] if x['path']=='m120_board_env_preflight.py');assert sha(reuse/env['path'])==env['sha256']
    pkg.mkdir();m=json.loads((old/'PACKAGE_MANIFEST.json').read_bytes())
    for row in m['files']:
        if row['path']=='SHA256SUMS':continue
        assert sha(old/row['path'])==row['sha256'];data=(old/row['path']).read_bytes()
        if row['path']=='m415_gate.py':data=source.encode('utf-8')
        elif row['path']=='m415_assemble.py':data=data.decode('utf-8').replace('m415_saved_feature_candidate_01','m415_saved_feature_candidate_02').replace('fd6844cab70d42f049346b8c6e0f8db96cfd5c565600d930c5e4a8cffe004439',sha(old/'PACKAGE_MANIFEST.json')).encode('utf-8')
        elif row['path'] in ('m415_export.py','run_m415.sh'):data=data.decode('utf-8').replace('/home/ubuntu/m415_saved_feature_language_01','/home/ubuntu/m415_saved_feature_language_02').encode('utf-8')
        atomic(pkg/row['path'],data,immutable=True)
    for p in pkg.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
    names=sorted(p.name for p in pkg.iterdir());atomic(pkg/'SHA256SUMS',''.join(f'{sha(pkg/n)}  {n}\n' for n in names).encode('ascii'),immutable=True)
    files=sorted(pkg.iterdir());manifest=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(pkg/'PACKAGE_MANIFEST.json',encoded(manifest),immutable=True)
    workflow=(HERE/'m415_workflow03.py').read_text(encoding='utf-8').replace('M415-saved-feature-language-02','M415-saved-feature-language-03').replace("ROOT/'tmp/m41502'","ROOT/'tmp/m41503'").replace('candidates/M415-saved-feature-language-01/PACKAGE_MANIFEST.json','candidates/M415-saved-feature-language-02/PACKAGE_MANIFEST.json').replace('runs/M415-saved-feature-transfer-02/RESULT.json','runs/M415-saved-feature-transfer-03/RESULT.json').replace('runs/M415-saved-feature-language-board-01/BOARD_RESULT.json','runs/M415-saved-feature-language-board-02/BOARD_RESULT.json')
    atomic(HERE/'m415_workflow04.py',workflow.encode('utf-8'),immutable=True)
    control=(HERE/'m415_control03.ps1').read_text(encoding='utf-8').replace('M415-saved-feature-language-02','M415-saved-feature-language-03').replace('m415_saved_feature_candidate_02','m415_saved_feature_candidate_03').replace('tmp/m41502','tmp/m41503').replace('m415_workflow03.py','m415_workflow04.py').replace('candidates/M415-saved-feature-language-01/PACKAGE_MANIFEST.json','candidates/M415-saved-feature-language-02/PACKAGE_MANIFEST.json').replace('runs/M415-saved-feature-language-board-01/BOARD_RESULT.json','runs/M415-saved-feature-language-board-02/BOARD_RESULT.json')
    atomic(HERE/'m415_control04.ps1',control.encode('utf-8'),immutable=True)
    close=(HERE/'m415_close.py').read_text(encoding='utf-8').replace('from m415_workflow03 import check','from m415_workflow04 import check').replace('runs/M415-saved-feature-language-closure-01/RESULT.json','runs/M415-saved-feature-language-closure-02/RESULT.json').replace('/home/ubuntu/m415_saved_feature_language_01','/home/ubuntu/m415_saved_feature_language_02')
    atomic(HERE/'m415_close02.py',close.encode('utf-8'),immutable=True)
    value=dict(status='PASS_M415_CLOSED_ENVIRONMENT_RUNNER_PATH_REPAIR',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),prior_raw_sha256=sha(failed),prior_closure_sha256=sha(closure),
        prior_Overlay_DMA_model_all_zero=True,environment_runner_reused_sha256=env['sha256'],both_environment_calls_repaired=True,original_math_and_snapshot_trial_unchanged=True,
        trial_sha256=sha(pkg/'m415_trials.py'),board_run=False)
    p=BASE/'runs/M415-environment-path-preparation-03/RESULT.json';atomic(p,encoded(value),immutable=True)
    sync('latest_m415_saved_feature_preparation',dict(status=value['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=value['manifest_sha256']),
        f'## M415 零Overlay失败环境路径修复（2026-10-06）\n\nSHA {sha(p)}；首轮raw {sha(failed)}及闭合{sha(closure)}保持，0Overlay/0DMA/0模型。初次及stable恢复检查器均指向已验证完整M368包SHA {env["sha256"]}，两次执行规则不删；03新结果目录避开原结果，原数学/快照trial不改。先完整依赖及控制检查，再只重试同失败前置级入口，0视觉。')
    # Resolve every HERE/filename literal against the package before any board allocation.
    tree=ast.parse(source);relative_files=set()
    for n in ast.walk(tree):
        if isinstance(n,ast.BinOp) and isinstance(n.op,ast.Div) and isinstance(n.left,ast.Name) and n.left.id=='HERE' and isinstance(n.right,ast.Constant) and isinstance(n.right.value,str):relative_files.add(n.right.value)
    assert all((pkg/n).is_file() for n in relative_files)
    for name in ('m415_gate.py','m415_trials.py'):
        for n in ast.walk(ast.parse((pkg/name).read_text(encoding='utf-8'))):
            if isinstance(n,ast.ImportFrom) and n.module and n.level==0:
                if n.module.startswith(('m415_','m368_','m363_','m341_','m369_')):assert (pkg/(n.module+'.py')).exists() or (reuse/(n.module+'.py')).exists()
    pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    checked=subprocess.run([pwsh,'-NoProfile','-File',str(HERE/'m415_control04.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8');assert checked.returncode==0 and 'M415_CONTROL_SELF_TEST_PASS' in checked.stdout
    checked=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/bin/bash','-n','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/'+(pkg/'run_m415.sh').relative_to(ROOT).as_posix()],capture_output=True);assert checked.returncode==0
    prior=BASE/'runs/M415-host-recovery-support-05/RESULT.json';oldproof=json.loads(prior.read_bytes());assert len(oldproof['components']['negative_checks'])==8
    support=dict(oldproof,status='PASS_M415_ENVIRONMENT_PATH_DEPENDENCY_AND_CONTROL_SUPPORT',manifest_sha256=value['manifest_sha256'],prior_support_sha256=sha(prior),component_and_PASS_checks_reused_no_forward=True,
        package_HERE_literals_resolved=sorted(relative_files),environment_runner_reused_sha256=env['sha256'],bash_n=True,control_selftest=True,
        source_sha256={n:sha(HERE/n) for n in ('m415_saved_features.py','m415_trials02.py','m415_workflow04.py','m415_control04.ps1','m415_envpath03.py','m415_close02.py')})
    p=BASE/'runs/M415-environment-path-support-06/RESULT.json';atomic(p,encoded(support),immutable=True)
    sync('latest_m415_saved_feature_support',dict(status=support['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=support['manifest_sha256']),
        f'## M415 环境路径及递归支持补查（2026-10-06）\n\nSHA {sha(p)}；全部HERE文件及本级m415/m368/m363/m341/m369支持路径闭合，检查器使用完整旧SHA包；Python3.10/b​​ash-n/控制故意失败收集通过。原真实尺寸live-list/14PASS/13回收检查复用不模型重跑，03可同COM3差量上传并一次执行，失败级不扩层。')
    print('M415_ENV_PATH_READY',sha(p),value['manifest_sha256'])
if __name__=='__main__':main()
