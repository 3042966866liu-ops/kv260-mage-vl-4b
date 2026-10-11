"""Atomic narrow CSim evidence; does not certify RTL or board readiness."""
import json
import re
from pathlib import Path
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
log=ROOT/'tmp/m357_hls_project_02/hls/csim/report/m89x_runtime_kernel_csim.log'
text=log.read_text(encoding='utf-8-sig')
assert 'CSim done with 0 errors' in text and 'M128_M120_REAL_RECORD_NUMERICAL_CSIM_PASS' in text
cases=re.findall(r'M128_CHAIN_PASS[^\r\n]+',text)
assert len(cases)==7 and 'M128_OUTPUT_WORDS=16384' in text
source=ROOT/'tmp/m357_activation_banks/hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp'
prep=BASE/'runs/M357-activation-bank-preparation-01/RESULT.json'
assert w.sha(prep)=='a5aee2704632a03e7760be8474d5f75d92598b03b5e923109caf03ff51d82ac1'
p=json.loads(prep.read_text(encoding='utf-8'));assert w.sha(source)==p['candidate_sha256']
result=dict(status='PASS_CANDIDATE_REAL_RECORD_NUMERICAL_CSIM',build_id='0x4D333537',case_count=7,output_words=16384,
    cases=cases,scope='Original M128 real-record numerical fixture, seven reduced-row cases, not full M355 0:q output or RTL',
    csim_log=dict(path=log.relative_to(ROOT).as_posix(),sha256=w.sha(log)),source_sha256=w.sha(source),missing_headers=0,
    rejected_attempt='First driver cwd caused missing design object at link; no numerical execution; new isolated project fixes cwd',
    pending=['HLS actual parallel scheduling/resource report','full representative RTL output/FIFO/backpressure','implementation timing','board gates'],board_run=False,promoted=False)
ev=BASE/'runs/M357-activation-bank-csim-01/RESULT.json';w.atomic(ev,w.encoded(result),immutable=True);sha=w.sha(ev)
w.sync('M357_activation_bank_csim',dict(status=result['status'],build_id=result['build_id'],sha256=sha,evidence_path=ev.relative_to(ROOT).as_posix()),
    'M357 候选 0x4D333537 新真实权重 CSim 七个原 M128 小行数用例/16384输出 words PASS、header missing=0；不是完整 0:q/RTL/板端 PASS。首次驱动 cwd 链接失败已隔离修复，稳定源码不变。综合仍运行，下一步实际 shard 调度/资源后继续 RTL。证据 '+sha)
print(json.dumps(dict(status=result['status'],sha256=sha),ensure_ascii=True))
