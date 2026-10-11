"""Preserve pre-launch denial; create new same-source HLS attempt, no deletion."""
import json
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync


def main():
    old=ROOT/'tmp/m441_record_pipeline_01';new=ROOT/'tmp/m441_record_pipeline_02'
    assert not new.exists() and not (ROOT/'tmp/m441_hls_project_01').exists()
    log=old/'m441_hls_console.log';rc=old/'m441_hls_exit.json'
    assert json.loads(rc.read_bytes())['hls_rc']==1
    text=log.read_text(encoding='utf-8-sig')
    assert 'Access is denied.' in text and 'loader.bat' in text
    assert 'Starting C simulation' not in text
    prep=BASE/'runs/M441-record-pipeline-preparation-01/RESULT.json';p=json.loads(prep.read_bytes())
    for row in p['files']: assert sha(ROOT/row['path'])==row['sha256']
    fail=dict(status='BLOCKED_M441_TOOL_LAUNCH_SANDBOX_DENIAL',build_id=p['build_id'],
              preparation_sha256=sha(prep),log_path=log.relative_to(ROOT).as_posix(),log_sha256=sha(log),
              exit_path=rc.relative_to(ROOT).as_posix(),exit_sha256=sha(rc),hls_rc=1,
              csim_started=False,synthesis_started=False,project_created=False,board=False,
              root_cause_scope='Launcher denied under default sandbox; HLS compiler and candidate never ran.')
    ev=BASE/'runs/M441-tool-launch-failure-01/RESULT.json';atomic(ev,encoded(fail),immutable=True)
    sync('latest_m441_tool_launch_failure',dict(status=fail['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=p['build_id'],board=False),
         f'## M441 工具启动权限阻塞（2026-10-07）\n\nSHA {sha(ev)}；固定D盘Vitis launcher默认沙箱Access denied，rc1且无project/CSim/综合，非数值或架构失败，0板端。原日志保持；下一步同SHA源码独立02在正常工具权限下执行，不覆盖01或放宽门禁。')
    for row in p['files']:
        src=ROOT/row['path'];raw=src.read_bytes()
        if src.name=='run_m441_hls.tcl':
            raw=raw.decode('utf-8').replace('tmp/m441_record_pipeline_01','tmp/m441_record_pipeline_02').replace('tmp/m441_hls_project_01','tmp/m441_hls_project_02').encode('utf-8')
        atomic(new/src.relative_to(old),raw,immutable=True)
    control=ROOT/'scripts/optimization/m441_run_hls.ps1'
    raw=control.read_text(encoding='utf-8').replace('tmp/m441_record_pipeline_01','tmp/m441_record_pipeline_02').replace('tmp/m441_hls_project_01','tmp/m441_hls_project_02')
    atomic(control.with_name('m441_run_hls02.ps1'),raw.encode('utf-8'),immutable=True)
    r=dict(p,status='PREPARED_M441_SAME_SOURCE_TOOL_ATTEMPT02',prior_preparation_sha256=sha(prep),launch_failure_sha256=sha(ev),
           source_exact=sha(new/'hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp')==p['source_sha256'],
           files=[dict(path=q.relative_to(ROOT).as_posix(),bytes=q.stat().st_size,sha256=sha(q)) for q in sorted(new.rglob('*')) if q.is_file()])
    assert r['source_exact']
    ev=BASE/'runs/M441-record-pipeline-preparation-02/RESULT.json';atomic(ev,encoded(r),immutable=True)
    sync('latest_m441_record_pipeline_preparation02',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=r['build_id'],board=False),
         f'## M441 同源码工具运行02准备（2026-10-07）\n\nSHA {sha(ev)}；原13依赖/候选源码及实验协议同SHA，只隔离工具路径，原01启动失败保留；未编译/仿真或板端。下一步正常权限运行固定版本控制器，原M439不重测。')
    print(r['status'],sha(ev))


if __name__=='__main__': main()
