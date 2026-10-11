"""Close metadata-only elaboration repair at the failed maximum-FIFO level."""
import json
from pathlib import Path
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
prep=BASE/'runs/M357-debug-guard-preparation-01/RESULT.json'
assert w.sha(prep)=='f3fcdbacfc4a946acdb48a73d7c02dc9e20e61d9e600529762fa061b8dff6e28'
spec=json.loads(prep.read_text(encoding='utf-8'))
for row in spec['files']:assert w.sha(ROOT/row['path'])==row['sha256']
directory=ROOT/'tmp/m357_guarded_max_03/verilog'
receipt=directory/'m357_guarded_compile_exit.json';log=directory/'m357_guarded_xelab.log'
assert json.loads(receipt.read_text(encoding='utf-8'))['compile_rc']==0
assert 'Built simulation snapshot m357_guarded_debug' in log.read_text(encoding='utf-8-sig',errors='replace')
result=dict(status='PASS_DEBUG_METADATA_ONLY_ELABORATION',build_id='0x4D333537',
    rejected_max_raw_sha256=spec['rejected_raw_sha256'],preparation_sha256=w.sha(prep),
    all_source_fixture_bytes_unchanged=True,transactions_started=0,board=False,promoted=False,
    evidence=[dict(path=p.relative_to(ROOT).as_posix(),sha256=w.sha(p)) for p in (prep,receipt,log)])
ev=BASE/'runs/M357-debug-guard-compile-01/RESULT.json';w.atomic(ev,w.encoded(result),immutable=True);sha=w.sha(ev)
w.sync('M357_debug_guard_compile',dict(status=result['status'],sha256=sha,evidence_path=ev.relative_to(ROOT).as_posix(),build_id=result['build_id']),
    'M357 最大背压用例第一次在0虚拟时间被xsim拒绝（无trace信息且工具rc0），FAIL原字节保存。只在独立03目录以-debug typical重新编译完全相同DUT/VIP/fixture；编译PASS，0新RTL事务/0板端事务，下一步仍在最大FIFO背压级。证据 '+sha)
print(json.dumps(dict(status=result['status'],sha256=sha)))
