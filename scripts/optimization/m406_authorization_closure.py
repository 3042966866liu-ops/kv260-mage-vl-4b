"""Preserve failed authorization and choose a fresh log, without board access."""
import json
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync


def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    support=board['latest_m406_vision_support']
    assert sha(ROOT/support['result'])==support['sha256']
    old=(HERE/'m406_control.ps1').read_text(encoding='utf-8')
    recorded=json.loads((ROOT/support['result']).read_bytes())
    assert sha(HERE/'m406_control.ps1')==recorded['source_sha256']['m406_control.ps1']
    logs=[]
    for name in ('sudo_precheck_01.log','sudo_upload_02.log'):
        p=ROOT/'tmp/m406'/name; text=p.read_text(encoding='utf-8-sig')
        assert '__M406_SUDO_RC_1__' in text and 'ubuntu@kria:' in text and 'password is required' in text
        logs.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),original_rc=1))
    assert not (ROOT/'tmp/m406/run.log').exists()
    assert not (ROOT/'tmp/m406/absence.log').exists()
    new=old.replace("'tmp/m406/sudo_upload_02.log'","'tmp/m406/sudo_upload_03.log'")
    assert new!=old and new.replace("'tmp/m406/sudo_upload_03.log'","'tmp/m406/sudo_upload_02.log'")==old
    atomic(HERE/'m406_control02.ps1',new.encode('utf-8'),immutable=True)
    value=dict(status='BLOCKED_M406_UPLOAD_AUTHORIZATION',original_logs=logs,
        package_manifest_sha256=support['manifest_sha256'],package_or_gate_changed=False,
        support_evidence=support,control_log_only_change=True,uploaded_files=0,
        overlay_loads=0,visual_forwards=0,language_forwards=0,FPGA_transactions=0,
        repeated_without_new_user_confirmation=False,
        next_control='scripts/optimization/m406_control02.ps1',
        fresh_authorization_log='tmp/m406/sudo_upload_03.log',
        source_sha256=sha(HERE/'m406_authorization_closure.py'))
    out=BASE/'runs/M406-authorization-closure-01/RESULT.json';atomic(out,encoded(value),immutable=True)
    h=sha(out)
    sync('latest_m406_authorization',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=h),
        f'## M406 上传前授权阻塞（2026-10-05）\n\nSHA {h}；COM3 shell确认，两次sudo原rc1日志保留，两次之间用户报告续期。'
        '尚未上传/视觉/语言/Overlay/DMA/FPGA。原包及支持检查保持；已再次请用户同COM3 sudo-v，不能无新人工回复反复尝试。'
        'control02只换新授权03日志，避免覆盖原失败；下一步恢复后直接上传一次，不新增准备工作。')
    # The support itself is unchanged; extend the verified source map only after exact diff proof.
    updated=json.loads((ROOT/support['result']).read_bytes())
    updated['status']='PASS_OFFLINE_M406_FRESH_AUTHORIZATION_LOG_ONLY'
    updated['prior_support_sha256']=support['sha256']
    updated['exact_inverse_diff_verified']=True
    updated['source_sha256']['m406_control02.ps1']=sha(HERE/'m406_control02.ps1')
    revised=BASE/'runs/M406-vision-observer-support-02/RESULT.json';atomic(revised,encoded(updated),immutable=True)
    h2=sha(revised)
    sync('latest_m406_vision_support',dict(status=updated['status'],result=revised.relative_to(ROOT).as_posix(),
        sha256=h2,manifest_sha256=support['manifest_sha256']),
        f'## M406 原授权日志保留控制02（2026-10-05）\n\nSHA {h2}；仅授权日志02→03，逆向逐字差分通过。实际producer/collect/19拒绝/全部回执/故意失败支持完整复用，包及数学/计数路径不改。'
        '只用control02等待人工续期后一次上传；当前0上传/视觉/FPGA，无性能。')
    print(json.dumps(dict(status=value['status'],authorization_sha256=h,support_sha256=h2),ensure_ascii=False))


if __name__=='__main__':main()
