"""Isolate the proven completion observer; only parameterize expected Build ID."""
import hashlib
import json
from pathlib import Path
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
src=ROOT/'scripts/optimization/completion_observer.py'
out=ROOT/'tmp/m357_board_support_01'
if out.exists():raise RuntimeError('Existing board support preparation; inspect only')
text=src.read_text(encoding='utf-8')
old='clock=time.monotonic_ns, sleeper=time.sleep, initial_busy=None):'
new='clock=time.monotonic_ns, sleeper=time.sleep, initial_busy=None, expected_build_id=BUILD_ID):'
assert text.count(old)==1 and text.count("latest['ap_return']!=BUILD_ID")==1
candidate=text.replace(old,new).replace("latest['ap_return']!=BUILD_ID","latest['ap_return']!=expected_build_id")
assert candidate.replace(new,old).replace("latest['ap_return']!=expected_build_id","latest['ap_return']!=BUILD_ID")==text
out.mkdir();w.atomic(out/'m357_completion_observer.py',candidate.encode('utf-8'),immutable=True)
result=dict(status='PREPARED_BUILD_PARAMETER_ONLY_OBSERVER',original_sha256=w.sha(src),
    source_sha256=w.sha(out/'m357_completion_observer.py'),path=(out/'m357_completion_observer.py').relative_to(ROOT).as_posix(),
    change='Only explicit expected Build ID parameter; all polling, AP_DONE latching, DMA/error/timeout semantics unchanged',
    board_run=False,hardware_implementation_change=False)
w.atomic(out/'SOURCE_RECEIPT.json',w.encoded(result),immutable=True)
print(json.dumps(result))
