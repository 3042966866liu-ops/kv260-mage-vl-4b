"""Record an observed authorized dispatch, never claim completion or rerun."""
import json
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
def main():
    path=ROOT/'tmp/m388/component_uart.log';log=path.read_text(encoding='utf-8-sig');before=ROOT/'tmp/m388/sudo_before_component_uart.log'
    assert 'M388_MEMORY ' in log and '__M388_GATE_SUDO_RC_0__' in before.read_text(encoding='utf-8-sig')
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));transfer=b['latest_m388_ps_performance_transfer'];assert sha(ROOT/transfer['result'])==transfer['sha256']
    pkg=BASE/'candidates/M388-ps-performance-01'
    r=dict(status='AUTHORIZED_DISPATCH_OBSERVED_NOT_FINAL_RESULT',manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),transfer_sha256=transfer['sha256'],controller_sha256=sha(HERE/'m388_control.ps1'),sudo_log_sha256=sha(before),log_path=path.relative_to(ROOT).as_posix(),order='ABBABAAB',build_id='0x4D333537',numerical_pass=False,performance_pass=False,no_rerun_original_log_exists=True,next_step='Wait for original once-only gate and strict saved-byte collection. If interrupted, collect only; no new Run.')
    p=BASE/'runs/M388-dispatch-observation-01/RESULT.json';atomic(p,encoded(r),immutable=True);d=sha(p)
    sync('latest_m388_dispatch_observation',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=d,performance_pass=False),f'## M388 交错性能对照已授权启动，尚无最终裁决\n\n同COM3 shell/sudo rc0、传输SHA {transfer["sha256"]}后原Run仅启动一次，Build0x4D333537、A原暂存/B普通PS预读、ABBABAAB。观察SHA {d}；不是数值/性能PASS。保留tmp/m388/component_uart.log；等待完成及原字节回收，任何恢复只能Collect，不重Run。')
    print('M388_DISPATCH_RECORDED',d)
if __name__=='__main__':main()
