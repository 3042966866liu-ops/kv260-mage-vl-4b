"""Pre-run fix: frozen runtime.evidence returns its live retry ledger."""
import ast,importlib.util,json,subprocess,sys
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

def main():
    oldpkg=BASE/'candidates/M415-saved-feature-language-01';pkg=BASE/'candidates/M415-saved-feature-language-02'
    if pkg.exists():raise RuntimeError('Immutable snapshot repair exists')
    expected='fd6844cab70d42f049346b8c6e0f8db96cfd5c565600d930c5e4a8cffe004439'
    assert sha(oldpkg/'PACKAGE_MANIFEST.json')==expected
    assert not (ROOT/'tmp/m41501/run.log').exists()
    evidence=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/deployment/mage_vl4b/m181_m120_video_board_candidate/text_runtime/runtime/board_runtime.py'
    assert '"scale_attempts": self.scale_attempts' in evidence.read_text(encoding='utf-8')
    source=(oldpkg/'m415_trials.py').read_text(encoding='utf-8')
    source=source.replace('import json,threading,time','import copy,json,threading,time').replace('before=runtime.evidence();','before=copy.deepcopy(runtime.evidence());').replace('after=runtime.evidence();','after=copy.deepcopy(runtime.evidence());')
    assert source.count('copy.deepcopy(runtime.evidence())')==2
    atomic(HERE/'m415_trials02.py',source.encode('utf-8'),immutable=True)
    workflow=(HERE/'m415_workflow.py').read_text(encoding='utf-8').replace('M415-saved-feature-language-01','M415-saved-feature-language-02').replace("ROOT/'tmp/m41501'","ROOT/'tmp/m41502'").replace('candidates/M368-staged-video-03/PACKAGE_MANIFEST.json','candidates/M415-saved-feature-language-01/PACKAGE_MANIFEST.json')
    atomic(HERE/'m415_workflow02.py',workflow.encode('utf-8'),immutable=True)
    control=(HERE/'m415_control.ps1').read_text(encoding='utf-8').replace('M415-saved-feature-language-01','M415-saved-feature-language-02').replace('m415_saved_feature_candidate_01','m415_saved_feature_candidate_02').replace('tmp/m41501','tmp/m41502').replace('m415_workflow.py','m415_workflow02.py').replace('candidates/M368-staged-video-03/PACKAGE_MANIFEST.json','candidates/M415-saved-feature-language-01/PACKAGE_MANIFEST.json')
    atomic(HERE/'m415_control02.ps1',control.encode('utf-8'),immutable=True)
    pkg.mkdir()
    m=json.loads((oldpkg/'PACKAGE_MANIFEST.json').read_bytes())
    for row in m['files']:
        if row['path']=='SHA256SUMS':continue
        raw=(oldpkg/row['path']).read_bytes();assert sha(oldpkg/row['path'])==row['sha256']
        if row['path']=='m415_trials.py':raw=source.encode('utf-8')
        elif row['path']=='m415_assemble.py':
            raw=raw.decode('utf-8').replace('m368_staged_video_candidate_03','m415_saved_feature_candidate_01').replace('f5937684306cd0ce40683a9bc46097b69cc7a9c7625bf208883eaada8071fb66',expected).encode('utf-8')
        atomic(pkg/row['path'],raw,immutable=True)
    files=sorted(pkg.iterdir());atomic(pkg/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in files).encode('ascii'),immutable=True)
    files=sorted(pkg.iterdir());manifest=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files])
    atomic(pkg/'PACKAGE_MANIFEST.json',encoded(manifest),immutable=True)
    for p in pkg.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
    r=dict(status='PASS_M415_PRE_RUN_LIVE_LEDGER_SNAPSHOT_REPAIR',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),
        rejected_unexecuted_manifest_sha256=expected,old_transfer_sha256=sha(BASE/'runs/M415-saved-feature-transfer-01/RESULT.json'),
        actual_evidence_source_sha256=sha(evidence),live_retry_list_reference_confirmed=True,
        both_counter_boundaries_deepcopied=True,unchanged_gate_source_sha256=sha(pkg/'m415_gate.py'),
        no_hardware_attempt_from01=True,board_run=False,accuracy_proven=False,performance_pass=False,
        next_concrete_step='Explicit live-list fixture and controller check, then delta-upload02 and one existing saved-feature comparison.')
    p=BASE/'runs/M415-snapshot-preparation-02/RESULT.json';atomic(p,encoded(r),immutable=True)
    sync('latest_m415_saved_feature_preparation',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=r['manifest_sha256']),
         f'## M415 执行前重试列表快照修正（2026-10-06）\n\nSHA {sha(p)}；冻结实际evidence返回self.scale_attempts共享列表，01已传输但0Run/Overlay/FPGA，原准备/组件/传输记录保留。02只将两次运行前后计数deepcopy，原M238/M241及gate源码不变，新manifest {r["manifest_sha256"]}。需要实际live-list fixture补查，再差量上传执行一次，不硬件重跑。')
    # Reuse fixture math but change only the fake evidence API to the real aliasing behavior.
    fixture=(HERE/'m415_support.py').read_text(encoding='utf-8').replace('import m415_trials as trials','import m415_trials02 as trials').replace('import m415_workflow as workflow','import m415_workflow02 as workflow').replace('scale_attempts=copy.deepcopy(self.attempts)','scale_attempts=self.attempts')
    namespace={'__name__':'m415_live_alias_component','__file__':str(HERE/'m415_support.py')}
    exec(compile(fixture,'<M415-real-live-ledger-fixture>','exec'),namespace)
    c=namespace['cpu_components']()
    oldsupport=BASE/'runs/M415-saved-feature-support-02/RESULT.json'
    assert sha(oldsupport)=='3ed64c7ce3c79d49abfdd44e68655fda4f88aa4b050e1f0c3272b6509e18695d'
    prior=json.loads(oldsupport.read_bytes());assert len(prior['PASS_validator_negative_checks'])==14
    pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    checked=subprocess.run([pwsh,'-NoProfile','-File',str(HERE/'m415_control02.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    if checked.returncode or 'M415_CONTROL_SELF_TEST_PASS' not in checked.stdout:raise RuntimeError(checked.stdout+checked.stderr)
    v=dict(status='PASS_M415_LIVE_LEDGER_SNAPSHOT_COMPONENT_SUPPORT',manifest_sha256=r['manifest_sha256'],components=c,
        fake_evidence_returns_actual_live_list_behavior=True,prior_PASS_and_negative_validator_reused_sha256=sha(oldsupport),
        new_workflow_only_package_transfer_paths_changed=True,gate_runner_math_policy_unchanged=True,board_run=False,
        source_sha256={n:sha(HERE/n) for n in ('m415_saved_features.py','m415_trials02.py','m415_workflow02.py','m415_control02.ps1','m415_snapshot02.py')})
    p=BASE/'runs/M415-snapshot-support-03/RESULT.json';atomic(p,encoded(v),immutable=True)
    sync('latest_m415_saved_feature_support',dict(status=v['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=v['manifest_sha256']),
         f'## M415 真实live-list计数API组件补查（2026-10-06）\n\nSHA {sha(p)}；实际新02两次trial分支、明确返回共享retry列表fixture，运行前后独立快照，累计1556逻辑差值正确；冻结输入嵌入/决策和8负例通过，原14PASS/13回收拒绝证据复用，控制自测通过。仍fake PL/runtime/KV/memory；未板端质量，允许02差量传输/一次Run。')
    print('M415_SNAPSHOT02_READY',sha(p),r['manifest_sha256'])
if __name__=='__main__':main()
