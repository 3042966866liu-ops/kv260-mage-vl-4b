"""Preserve actual sudo failure; fresh logs only, unchanged board payload."""
import json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
import m425_workflow as w
def main():
    log=ROOT/'tmp/m42501/sudo_upload.log';text=log.read_text(encoding='utf-8-sig')
    assert '__M425_SUDO_RC_1__' in text and 'ubuntu@kria:' in text
    assert not (ROOT/'tmp/m42501/absence.log').exists() and not (ROOT/'tmp/m42501/run.log').exists()
    manifest=sha(w.PKG/'PACKAGE_MANIFEST.json')
    failure=dict(status='BLOCKED_M425_SUDO_BEFORE_UPLOAD',sudo_return_code=1,sudo_log=log.relative_to(ROOT).as_posix(),sudo_log_sha256=sha(log),manifest_sha256=manifest,uploaded=False,board_run=False,temperature_measurement_enabled=False)
    out=BASE/'runs/M425-authorization-precheck-01/RESULT.json';atomic(out,encoded(failure),immutable=True)
    sync('latest_m425_authorization_precheck',dict(status=failure['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=manifest,board_run=False),f'## M425 完整暖请求上传前授权阻塞（2026-10-06）\n\nSHA {sha(out)}；同COM3 shell确认，sudo原rc1，日志{sha(log)}；0传输/Overlay/请求，未测温。包及组件/27回收拒绝检查已完成；已要求人工sudo-v，不重复检查相同阻塞，原日志保留。收到回复后直接上传。')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());entry=board['latest_m425_performance_support'];assert sha(ROOT/entry['result'])==entry['sha256']
    support=json.loads((ROOT/entry['result']).read_bytes());assert support['manifest_sha256']==manifest
    sources={}
    for original,new in [('m425_workflow.py','m425_workflow02.py'),('m425_control.ps1','m425_control02.ps1')]:
        text=(HERE/original).read_text(encoding='utf-8');changed=text.replace('tmp/m42501','tmp/m42502')
        if new.endswith('.ps1'):changed=changed.replace('m425_workflow.py','m425_workflow02.py')
        back=changed.replace('tmp/m42502','tmp/m42501').replace('m425_workflow02.py','m425_workflow.py')
        assert back==text
        atomic(HERE/new,changed.encode('utf-8'),immutable=True);sources[new]=sha(HERE/new)
    support.update(status='PASS_M425_UNCHANGED_COMPONENT_FRESH_AUTHORIZATION_LOGS',source_sha256={**support['source_sha256'],**sources},prior_support_sha256=entry['sha256'],authorization_failure_sha256=sha(out),components_repeated=False,hardware_repeated=False,only_fresh_host_logs=True)
    newout=BASE/'runs/M425-authorization-recovery-01/RESULT.json';atomic(newout,encoded(support),immutable=True)
    sync('latest_m425_performance_support',dict(status=support['status'],result=newout.relative_to(ROOT).as_posix(),sha256=sha(newout),manifest_sha256=manifest),f'## M425 原包人工续期后直接上传准备（2026-10-06）\n\nSHA {sha(newout)}；复用同manifest {manifest}及原组件/27拒绝检查，不重跑；02控制/回收仅新tmp/m42502日志，逆变换逐字验证其他逻辑不变。原sudo失败日志保留。等待人工续期后直接Upload/Run，已有原运行仅Collect；不测温、不扩层或晋级。')
    print('M425_AUTHORIZATION_SYNC',sha(out),sha(newout))
if __name__=='__main__':main()
