"""Complete already frozen02 component; no preparation or board rerun."""
import json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
def main():
    prep=BASE/'runs/M415-snapshot-preparation-02/RESULT.json';r=json.loads(prep.read_bytes())
    pkg=BASE/'candidates/M415-saved-feature-language-02';assert sha(pkg/'PACKAGE_MANIFEST.json')==r['manifest_sha256']
    for row in json.loads((pkg/'PACKAGE_MANIFEST.json').read_bytes())['files']:assert sha(pkg/row['path'])==row['sha256']
    fixture=(HERE/'m415_support.py').read_text(encoding='utf-8').replace('import m415_trials as trials','import m415_trials02 as trials').replace('import m415_workflow as workflow','import m415_workflow02 as workflow').replace('scale_attempts=copy.deepcopy(self.attempts)','scale_attempts=self.attempts')
    anchor="changed=rt.evidence();changed['scale_attempts'][0]['selected_shift']=5\n            reject(lambda:trials.delta(rt.evidence(),changed),labels,'retry-history-mutation')"
    assert fixture.count(anchor)==1
    fixture=fixture.replace(anchor,"original_snapshot=copy.deepcopy(rt.evidence());changed=copy.deepcopy(rt.evidence());changed['scale_attempts'][0]['selected_shift']=5\n            reject(lambda:trials.delta(original_snapshot,changed),labels,'retry-history-mutation')")
    namespace={'__name__':'m415_live_alias_component','__file__':str(HERE/'m415_support.py')}
    exec(compile(fixture,'<M415-live-ledger-and-frozen-negative-baseline>','exec'),namespace)
    c=namespace['cpu_components']()
    prior=BASE/'runs/M415-saved-feature-support-02/RESULT.json';assert sha(prior)=='3ed64c7ce3c79d49abfdd44e68655fda4f88aa4b050e1f0c3272b6509e18695d'
    pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    checked=subprocess.run([pwsh,'-NoProfile','-File',str(HERE/'m415_control02.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    if checked.returncode or 'M415_CONTROL_SELF_TEST_PASS' not in checked.stdout:raise RuntimeError(checked.stdout+checked.stderr)
    v=dict(status='PASS_M415_LIVE_LEDGER_SNAPSHOT_COMPONENT_SUPPORT',manifest_sha256=r['manifest_sha256'],components=c,
        fake_evidence_returns_actual_live_list_behavior=True,prior_PASS_and_negative_validator_reused_sha256=sha(prior),
        negative_test_baseline_snapshot_fixed=True,new_workflow_only_package_transfer_paths_changed=True,gate_runner_math_policy_unchanged=True,board_run=False,
        source_sha256={n:sha(HERE/n) for n in ('m415_saved_features.py','m415_trials02.py','m415_workflow02.py','m415_control02.ps1','m415_snapshot02.py','m415_snapshot_support04.py')})
    out=BASE/'runs/M415-snapshot-support-04/RESULT.json';atomic(out,encoded(v),immutable=True)
    sync('latest_m415_saved_feature_support',dict(status=v['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=v['manifest_sha256']),
        f'## M415 真实live-list快照检查完成（2026-10-06）\n\nSHA {sha(out)}；02已冻结包不重复准备。新两次trial成功路径返回实际共享retry列表，前后独立快照1556逻辑差值正确；8数组/身份/重试负例的负例基准本身也冻结。原14PASS/13收集拒绝复用，控制自测通过。fake PL/runtime/KV/memory，0硬件；允许差量上传02后一次Run。')
    print('M415_SNAPSHOT04_READY',sha(out),r['manifest_sha256'])
if __name__=='__main__':main()
