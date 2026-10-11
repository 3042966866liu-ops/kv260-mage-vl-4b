"""Repair only missing simulator trace metadata; preserve failed attempt and DUT."""
import json
import shutil
from pathlib import Path
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
out=ROOT/'tmp/m357_guarded_max_03'
if out.exists():raise RuntimeError('Existing debug preparation; inspect only')
failure=BASE/'runs/M357-max-fifo-rtl-01/RESULT.json'
assert w.sha(failure)=='b86e7dec6d4bdc1623686f0db04a21a846dfb05628179e4279a49289b1a88c57'
log=ROOT/'tmp/m357_guarded_max_02/verilog/m357_max_xsim.log'
text=log.read_text(encoding='utf-8-sig',errors='replace')
assert 'compiled without trace information' in text and 'TRACE_HEARTBEAT' not in text and 'TRACE_DONE' not in text
prior=BASE/'runs/M357-guarded-rtl-preparation-02/RESULT.json'
assert w.sha(prior)=='5f84b4ac57b137044d44acc79f5fab0dcde0badcd853b4f0869e38dcfb6ef6ce'
rows=json.loads(prior.read_text(encoding='utf-8'))['files']
fixture=BASE/'runs/M357-max-fifo-preparation-01/RESULT.json'
assert w.sha(fixture)=='6d16e74640d763803a886bddd3fc85364f6dac51d49cc9fd3d4f9df92b9d16f1'
out.mkdir();(out/'verilog').mkdir();(out/'tv/rtldatafile').mkdir(parents=True)
for row in rows:
    src=ROOT/row['path'];assert w.sha(src)==row['sha256']
    rel=src.relative_to(ROOT/'tmp/m357_guarded_max_02/verilog')
    dest=out/'verilog'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
fixture_spec=json.loads(fixture.read_text(encoding='utf-8'))
for row in fixture_spec['files']:
    src=ROOT/row['path'];assert w.sha(src)==row['sha256']
    rel=src.relative_to(ROOT/'tmp/m357_maxfifo_trace')
    if rel.parts[0]=='verilog':continue
    dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
result=dict(status='PREPARED_DEBUG_METADATA_ONLY_REPAIR',build_id='0x4D333537',
    rejected_raw_sha256=w.sha(failure),source_preparation_sha256=w.sha(prior),fixture_preparation_sha256=w.sha(fixture),
    change='xelab -debug typical only; every DUT/VIP/observer source byte and maximum fixture unchanged',
    files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=w.sha(p)) for p in sorted(out.rglob('*')) if p.is_file()],
    board=False,rtl_time_advanced_in_failed_attempt=False,executed=False)
ev=BASE/'runs/M357-debug-guard-preparation-01/RESULT.json';w.atomic(ev,w.encoded(result),immutable=True)
print(json.dumps(dict(status=result['status'],sha256=w.sha(ev))))
