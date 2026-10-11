"""Require an observed RTL timeout, preserving both simulator and gate return codes."""
import csv
import json
from pathlib import Path
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
directory=ROOT/'tmp/m357_timeout_negative_01/verilog'
receipt=directory/'m357_timeout_exit.json'
if not receipt.exists():raise RuntimeError('Timeout process not finished')
saved=json.loads(receipt.read_text(encoding='utf-8'))
logpath=directory/'m357_timeout_xsim.log'
log=logpath.read_text(encoding='utf-8-sig',errors='replace')
trace=directory/'m357_trace.csv'
rows=list(csv.DictReader(trace.open(encoding='utf-8',newline='')))
checks=dict(expected_timeout_marker='M357_RTL_TIMEOUT_TRIGGERED ap_done=0 budget_cycles=200' in log,
    actual_fatal='M357 bounded timeout expired before ap_done' in log,
    fail_closed_gate_rc=saved['gate_rc']==1 and saved['timeout_observed'],
    no_ap_done=not any(r['event']=='ap_done' for r in rows),
    no_complete_transaction='RTL Simulation : 1 / 1' not in log,
    engine_initialized='necessary license' not in log and 'simulation failed to initialize' not in log.lower())
result=dict(status='PASS_EXPECTED_RTL_TIMEOUT_NEGATIVE' if all(checks.values()) else 'FAIL_RTL_TIMEOUT_NEGATIVE',
    build_id='0x4D333537',checks=checks,original_simulator_rc=saved['simulation_rc'],
    fail_closed_gate_rc=saved['gate_rc'],budget_cycles_after_actual_kernel_start=200,
    scope='Expected negative test. No completed computation or output PASS; preserves original simulator return code even if wrapper returns zero for fatal.',
    prior_max_sha256=saved['prior_max_sha256'],board=False,promoted=False,
    evidence=[dict(path=p.relative_to(ROOT).as_posix(),sha256=w.sha(p)) for p in (receipt,logpath,trace)])
ev=BASE/'runs/M357-timeout-rtl-01/RESULT.json'
w.atomic(ev,w.encoded(result),immutable=True);sha=w.sha(ev)
w.sync('M357_timeout_rtl',dict(status=result['status'],sha256=sha,evidence_path=ev.relative_to(ROOT).as_posix(),build_id=result['build_id']),
    'M357 独立超时负例 '+result['status']+'；实际kernel启动后200周期未ap_done触发fatal，保留原simulator rc='+str(saved['simulation_rc'])+'、fail-closed gate rc='+str(saved['gate_rc'])+'，不覆盖正例输出。0板端事务。证据 '+sha)
print(json.dumps(dict(status=result['status'],sha256=sha,checks=checks)))
if not all(checks.values()):raise SystemExit(1)
