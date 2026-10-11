"""Preserve blocked sudo receipt; unchanged packet and new controller log names."""
import copy,json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m421_prepare import once

def main():
    log=ROOT/'tmp/m42301/sudo_upload.log';text=log.read_text(encoding='utf-8-sig')
    assert '__M423_SUDO_RC_1__' in text and 'ubuntu@kria:' in text and 'password is required' in text
    assert not list((ROOT/'tmp/m42301').glob('upload_*')) and not (ROOT/'tmp/m42301/run.log').exists()
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());old=b['latest_m423_integrated_support'];assert sha(ROOT/old['result'])==old['sha256'];support=json.loads((ROOT/old['result']).read_bytes())
    pkg=BASE/'candidates/M423-integrated-video-01';assert sha(pkg/'PACKAGE_MANIFEST.json')==support['manifest_sha256']
    blocked=dict(status='BLOCKED_M423_SUDO_BEFORE_TRANSFER',log_path=log.relative_to(ROOT).as_posix(),log_sha256=sha(log),shell_confirmed=True,sudo_rc=1,upload_started=False,gate_started=False,extra_board_probe=False,stable_or_service_changed=False,next_step='Wait for human sudo-v recovery; do not repeat authorization probe before confirmation.')
    out=BASE/'runs/M423-authorization-precheck-01/RESULT.json';atomic(out,encoded(blocked),immutable=True)
    sync('latest_m423_authorization_precheck',dict(status=blocked['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),gate_started=False),f'## M423 同COM3授权前置阻塞（2026-10-06）\n\nSHA {sha(out)}；原sudo日志SHA {sha(log)}保存，shell确认、sudo rc1，0传输/0硬件执行，包及稳定回滚未改。已要求人工sudo-v，未收到恢复不重复探测；两层M420/M421质量PASS保持。')
    original=(HERE/'m423_control.ps1').read_text(encoding='utf-8')
    control=original.replace('tmp/m42301','tmp/m42302').replace('m423_workflow.py','m423_workflow02.py')
    assert control.replace('tmp/m42302','tmp/m42301').replace('m423_workflow02.py','m423_workflow.py')==original
    atomic(HERE/'m423_control02.ps1',control.encode('utf-8'),immutable=True)
    original=(HERE/'m423_workflow.py').read_text(encoding='utf-8')
    workflow=once(original,"folder=ROOT/'tmp/m42301'","folder=ROOT/'tmp/m42302'")
    assert once(workflow,"folder=ROOT/'tmp/m42302'","folder=ROOT/'tmp/m42301'")==original
    atomic(HERE/'m423_workflow02.py',workflow.encode('utf-8'),immutable=True)
    v=copy.deepcopy(support);v.update(status='PASS_M423_UNCHANGED_COMPONENT_AUTH_RECOVERY_READY',prior_support_sha256=old['sha256'],authorization_precheck_sha256=sha(out),packet_or_algorithm_changed=False,original_component_and30_negative_checks_reused_not_rerun=True,only_controller_log_namespace_changed=True,received_human_recovery=False)
    v['source_sha256'].update({n:sha(HERE/n) for n in ('m423_control02.ps1','m423_workflow02.py','m423_authorization_recovery.py')})
    ready=BASE/'runs/M423-authorization-recovery-01/RESULT.json';atomic(ready,encoded(v),immutable=True)
    note=f'## M423 人工续期后直接上传准备（2026-10-06）\n\nSHA {sha(ready)}；原支持{old["sha256"]}及阻塞{sha(out)}不改，组件/30负例不重跑，候选19载荷540783B和manifest {v["manifest_sha256"]}全保持。新control02/workflow02只切换tmp/m42302 COM3日志，逐字逆变换验证其他控制/数值/回收不变；前结果不可覆盖。等待人工回到shell并续期，收到后直接一次Upload/Run，已有结果仅Collect；不复查相同阻塞。'
    sync('latest_m423_integrated_support',dict(status=v['status'],result=ready.relative_to(ROOT).as_posix(),sha256=sha(ready),manifest_sha256=v['manifest_sha256']),note)
    sync('latest_m423_integrated_authorization_recovery',dict(status=v['status'],result=ready.relative_to(ROOT).as_posix(),sha256=sha(ready),manifest_sha256=v['manifest_sha256']),note)
    print('M423_AUTHORIZATION_RECOVERY_READY',sha(ready))
if __name__=='__main__':main()
