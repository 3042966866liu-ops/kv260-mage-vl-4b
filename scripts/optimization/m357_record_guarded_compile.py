"""Record compile-only proof; max-FIFO/timeout transactions remain locked."""
import json
from pathlib import Path
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
prep=BASE/'runs/M357-guarded-rtl-preparation-02/RESULT.json'
assert w.sha(prep)=='5f84b4ac57b137044d44acc79f5fab0dcde0badcd853b4f0869e38dcfb6ef6ce'
spec=json.loads(prep.read_text(encoding='utf-8'))
for row in spec['files']:assert w.sha(ROOT/row['path'])==row['sha256']
directory=ROOT/'tmp/m357_guarded_max_02/verilog'
receipt=directory/'m357_guarded_compile_exit.json';log=directory/'m357_guarded_xelab.log'
assert json.loads(receipt.read_text(encoding='utf-8'))['compile_rc']==0
assert 'Built simulation snapshot m357_guarded' in log.read_text(encoding='utf-8-sig',errors='replace')
assert not (directory/'m357_max_xsim.log').exists()
result=dict(status='PASS_GUARDED_TESTBENCH_COMPILE_ONLY',build_id='0x4D333537',transactions_started=0,board=False,promoted=False,
    prepared_sha256=w.sha(prep),source_checks=len(spec['files']),scope='Compile only; maximum FIFO/descriptor and timeout simulation not run',
    rejected_attempt=spec['rejected_attempt'],first_compile_failure_sha256=spec['compile_failure_log_sha256'],
    evidence=[dict(path=p.relative_to(ROOT).as_posix(),sha256=w.sha(p)) for p in (prep,receipt,log)],
    pending='Wait for candidate full frozen Q RTL adjudication; then one maximum descriptor/FIFO/backpressure simulation, followed by independent timeout negative')
ev=BASE/'runs/M357-guarded-rtl-compile-01/RESULT.json';w.atomic(ev,w.encoded(result),immutable=True);sha=w.sha(ev)
w.sync('M357_guarded_rtl_compile',dict(status=result['status'],sha256=sha,evidence_path=ev.relative_to(ROOT).as_posix(),build_id=result['build_id']),
    'M357 最大descriptor/FIFO/timeout观察器仅编译PASS，0新增RTL事务/板端事务。首次TB声明顺序语法失败保留，修正在新目录；没有改核心或在失败级之外重跑。当前两份完整0:q随机背压仿真与核心OOC仍运行；后级等待完整输出裁决。证据 '+sha)
print(json.dumps(dict(status=result['status'],sha256=sha),ensure_ascii=True))
