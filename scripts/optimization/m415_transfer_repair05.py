"""Recover completed02 transfer receipts under a new immutable host result."""
import importlib.util,json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
def main():
    assert not (ROOT/'tmp/m41502/run.log').exists()
    source=(HERE/'m415_workflow02.py').read_text(encoding='utf-8')
    anchor="runs/M415-saved-feature-transfer-01/RESULT.json";assert source.count(anchor)==1
    source=source.replace(anchor,'runs/M415-saved-feature-transfer-02/RESULT.json')
    atomic(HERE/'m415_workflow03.py',source.encode('utf-8'),immutable=True)
    control=(HERE/'m415_control02.ps1').read_text(encoding='utf-8').replace('m415_workflow02.py','m415_workflow03.py')
    atomic(HERE/'m415_control03.ps1',control.encode('utf-8'),immutable=True)
    prior=BASE/'runs/M415-snapshot-support-04/RESULT.json';old=json.loads(prior.read_bytes())
    assert sha(prior)=='e33acef68c7d15c9ce4b8ea27bf2269b790e1e228074375d10092ed32e9f71a6'
    pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    c=subprocess.run([pwsh,'-NoProfile','-File',str(HERE/'m415_control03.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    if c.returncode or 'M415_CONTROL_SELF_TEST_PASS' not in c.stdout:raise RuntimeError(c.stdout+c.stderr)
    r=dict(old,status='PASS_M415_HOST_TRANSFER_PATH_CLOSURE',prior_support_sha256=sha(prior),
        transfer02_failed_only_host_immutable_path=True,original01_immutable_receipt_preserved=True,no_new_transfer_or_gate=True,
        source_sha256={n:sha(HERE/n) for n in ('m415_saved_features.py','m415_trials02.py','m415_workflow03.py','m415_control03.ps1','m415_transfer_repair05.py')})
    out=BASE/'runs/M415-host-recovery-support-05/RESULT.json';atomic(out,encoded(r),immutable=True)
    sync('latest_m415_saved_feature_support',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=r['manifest_sha256']),
        f'## M415 已完成02传输回执路径回收（2026-10-06）\n\nSHA {sha(out)}；02全部SHA组装/bash-n已通过，主机收集器仍指01不可变传输记录而拒绝，未启动gate。保留01和02上传日志，仅新host03将回执保存为transfer-02；组件和板端包不改/不重跑/不重传。控制自测通过，收集原回执同步后Run。')
    spec=importlib.util.spec_from_file_location('m415_host_transfer03',HERE/'m415_workflow03.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.transfer()
    print('M415_HOST_TRANSFER_RECOVERED',sha(out))
if __name__=='__main__':main()
