"""Persist the one actual COM3 authorization check; never retries it."""
import json
import re
from pathlib import Path
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
p=ROOT/'tmp/m357_board/authorization_precheck_01.log'
raw=p.read_text(encoding='utf-8-sig')
assert 'ubuntu@kria:~$' in raw and 'sudo: a password is required' in raw
assert re.findall(r'__M357_AUTH_RC_(\d+)__',raw)==['1']
prep=BASE/'runs/M357-board-package-preparation-01/RESULT.json'
package=json.loads(prep.read_text(encoding='utf-8'))
result=dict(status='BLOCKED_SAME_TERMINAL_SUDO_BEFORE_TRANSFER',build_id='0x4D333537',
    shell_confirmed=True,sudo_return_code=1,attempts=1,password_attempted=False,
    raw_log_path=p.relative_to(ROOT).as_posix(),raw_log_sha256=w.sha(p),
    prerequisite_sha256=w.sha(prep),package_manifest_sha256=package['manifest_sha256'],
    bootstrap_uploaded=False,candidate_uploaded=False,overlay_loads=0,fpga_transactions=0,
    candidate_board_numerical_pass=False,candidate_board_performance_pass=False,promoted=False,
    next_step='Await human COM3 sudo-v and shell confirmation, close PuTTY; then one authorization check and manifest-first bootstrap upload. No retry without confirmation.',
    offline_complete='Stable matched shard RTL audit, CSim/header/full Q/max FIFO/backpressure/timeout, complete shell timing/HWH and clean package all synchronized; stable rollback unchanged.')
ev=BASE/'runs/M357-authorization-precheck-01/RESULT.json'
w.atomic(ev,w.encoded(result),immutable=True);sha=w.sha(ev)
w.sync('M357_authorization_precheck',dict(status=result['status'],sha256=sha,evidence_path=ev.relative_to(ROOT).as_posix(),build_id=result['build_id']),
    'M357 新RTL候选上板包已完成；COM3真实shell确认，但唯一sudo-n检查rc1需要密码，0上传/0Overlay/0FPGA事务。等待人工sudo-v/回shell并关闭PuTTY确认，不反复重试。稳定源及回滚保持，候选尚无板端数值/性能。证据 '+sha)
print(json.dumps(dict(status=result['status'],sha256=sha)))
