"""Preserve the auth failure and prepare fresh logs for the same sensor packet."""
import json
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync


def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    e=b['latest_m404_sensor_support'];old_path=ROOT/e['result']
    assert sha(old_path)==e['sha256']
    old=json.loads(old_path.read_bytes())
    for name,h in old['source_sha256'].items():assert sha(HERE/name)==h
    receipt=ROOT/'tmp/m404sensor/sudo_upload.log'
    text=receipt.read_text(encoding='utf-8-sig')
    assert '__M404_SENSOR_SUDO_RC_1__' in text and 'password is required' in text
    assert not (ROOT/'tmp/m404sensor/absence.log').exists()
    failure=dict(status='M424_WARM_ENVIRONMENT_UPLOAD_BLOCKED_SUDO',
                 shell_confirmed=True,sudo_return_code=1,
                 receipt=receipt.relative_to(ROOT).as_posix(),receipt_sha256=sha(receipt),
                 package_manifest_sha256=old['manifest_sha256'],
                 uploaded=False,overlay_loaded=False,model_forward_calls=0,
                 M423_numerical_pass_preserved=True,password_attempts=0,
                 next='Human sudo-v recovery, then upload the identical sensor packet using fresh logs.')
    out=BASE/'runs/M424-environment-authorization-01/RESULT.json'
    atomic(out,encoded(failure),immutable=True)
    sync('latest_m424_environment_authorization',dict(
        status=failure['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),
        sudo_return_code=1,uploaded=False,board_run=False),
        f'## M424 暖态环境目录授权阻塞（2026-10-06）\n\nSHA {sha(out)}，原sudo回执{sha(receipt)}；'
        '同COM3 shell确认、sudo rc1，0上传/Overlay/推理。M423完整接入PASS不变；'
        '已要求人工sudo-v，不重复探测。下一步保留原包和组件证据，仅新日志一次传输只读目录。')
    control=(HERE/'m404_sensor_control.ps1').read_text(encoding='utf-8-sig')
    substitutions=[('tmp/m404sensor','tmp/m424sensor01'),
                   ('m404_sensor_workflow.py','m424_sensor_workflow.py'),
                   ('latest_m404_sensor_support','latest_m424_environment_sensor_recovery')]
    new=control
    for a,c in substitutions:new=new.replace(a,c)
    guard="    if (Test-Path (Join-Path $workspace 'tmp/m424sensor01/sudo_upload.log')) { throw 'Original authorization log exists' }\n"
    new=new.replace("if ($Mode -eq 'Upload') {\n", "if ($Mode -eq 'Upload') {\n"+guard)
    reverse=new.replace(guard,'')
    for a,c in reversed(substitutions):reverse=reverse.replace(c,a)
    assert reverse==control
    workflow=(HERE/'m404_sensor_workflow.py').read_text(encoding='utf-8-sig')
    w=workflow.replace('tmp/m404sensor','tmp/m424sensor01').replace('2026-10-05','2026-10-06')
    assert w.replace('tmp/m424sensor01','tmp/m404sensor').replace('2026-10-06','2026-10-05')==workflow
    atomic(HERE/'m424_sensor_control.ps1',new.encode('utf-8'),immutable=True)
    atomic(HERE/'m424_sensor_workflow.py',w.encode('utf-8'),immutable=True)
    r=dict(old,status='PASS_SAME_SENSOR_PACKAGE_NEW_AUTHORIZATION_LOGS',
           prior_support_sha256=e['sha256'],authorization_raw_sha256=sha(out),
           unchanged_package=True,original_component_checks_reused_not_rerun=True,
           inverse_literal_control_and_collector_equality=True,
           awaiting_human_sudo_recovery=True)
    r['source_sha256']={n:sha(HERE/n) for n in
                        ('m424_sensor_control.ps1','m424_sensor_workflow.py','m424_sensor_resume.py')}
    recovery=BASE/'runs/M424-environment-sensor-recovery-01/RESULT.json'
    atomic(recovery,encoded(r),immutable=True)
    sync('latest_m424_environment_sensor_recovery',dict(
        status=r['status'],result=recovery.relative_to(ROOT).as_posix(),sha256=sha(recovery),
        manifest_sha256=r['manifest_sha256'],board_run=False),
        f'## M424 原只读温度目录新授权日志准备（2026-10-06）\n\nSHA {sha(recovery)}；'
        f'复用原支持{e["sha256"]}和同manifest {r["manifest_sha256"]}，组件/12回收负例不重跑。'
        '控制器/收集器逆变换逐字相同，仅新tmp/m424sensor01日志、guard及证据日期；'
        '原sudo失败日志不覆盖。收到人工恢复后直接一次Upload/Run，已有结果仅Collect。'
        '0新板端执行/性能。')
    print('M424_SENSOR_RECOVERY_SYNC',sha(recovery))


if __name__=='__main__':main()
