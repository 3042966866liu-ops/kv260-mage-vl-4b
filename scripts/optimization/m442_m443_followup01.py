"""Record the actual started board comparison; never launch or infer a PASS."""
import json
from m351_workflow import ROOT, BASE, encoded, sha, sync
from m441_host_io08 import atomic

def main():
    out=BASE/'runs/M442-M443-board-benefit-followup-01'
    prereq={}
    for name in ('preparation','support','artifact-transfer'):
        file='BOARD_RESULT.json' if name=='artifact-transfer' else 'RESULT.json'
        p=BASE/('runs/M442-complete-request-parser-'+name+'-01')/file
        obj=json.loads(p.read_bytes())
        assert obj['status'].startswith(('PASS_','PREPARED_'))
        for document in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
            assert sha(p) in (ROOT/document).read_text(encoding='utf-8-sig')
        prereq[name]=dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p))
    log=ROOT/'tmp/m442_performance01/Run_component_uart.log'
    data=log.read_bytes()
    assert b'__M442C_GATE_RC_' in data and b'M442P_MEMORY' in data
    for name in ('Run_component_sudo01.log','Run_component_syntax.log'):
        assert b'RC_0__' in (log.parent/name).read_bytes()
    snapshot=out/'Run_component_uart_start_snapshot.log'
    atomic(snapshot,data,immutable=True)
    p=out/'M442_STARTED.json'
    result=dict(status='STARTED_M442_INDEPENDENT_COMPLETE_REQUEST_COMPARISON01',
                build_id='0x4D343431',manifest_sha256='ad65985da6a8dd393b25df0569034684f7c6d1a5ea1643ff581bd1d0cc4eb41d',
                board_run_started=True,numerical_pass=False,performance_pass=False,
                exec_session=16601,automation_id='m442-m443',
                prerequisites=prereq,initial_uart_snapshot=dict(path=snapshot.relative_to(ROOT).as_posix(),sha256=sha(snapshot)),
                original_log=log.relative_to(ROOT).as_posix(),
                observation_only_after_start=True,
                next_step='Observe the existing controller; collect original bytes and fixed 12-request adjudication. Continue independent M443 RTL gates before implementation or board work.')
    atomic(p,encoded(result),immutable=True)
    sync('latest_m442_independent_complete_request_started01',dict(status=result['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),build_id=result['build_id'],numerical_pass=False,performance_pass=False),
         '## M442独立完整请求实测启动01（2026-10-10）\n\nSHA '+sha(p)+'；同COM3 TTY sudo-n/runner语法和实际包传输三同步通过，原Run已启动，exec16601。固定原4预热+8正式/12805物理，同M441硬件只更换解析，自动Collect原字节及严格关闭；原日志存在后禁止Run重跑。当前尚无性能裁决，原稳定保持。M443独立新电路继续实际RTL，本提醒m442-m443持续到两项原字节裁决交付。')
    atomic(out/'NOTIFIED.json',encoded(dict(automation_id='m442-m443',notifications=[dict(stage='m442_complete_request_started01',sha256=sha(p)),dict(stage='m443_W2_max_and_timeout_PASS',sha256='56eb78fe23b568085bc98ba3983803bdea3af424e7aa22d3570c3b08cd70764d')])) ,immutable=True)
    print(result['status'],sha(p))

if __name__=='__main__':main()
