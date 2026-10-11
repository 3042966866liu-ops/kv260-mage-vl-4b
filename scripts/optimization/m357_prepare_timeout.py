"""Copy the already compiled DUT to a separate timeout-negative working directory."""
import json
import shutil
from pathlib import Path
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
src=ROOT/'tmp/m357_guarded_max_02';out=ROOT/'tmp/m357_timeout_negative_01'
if out.exists():raise RuntimeError('Existing timeout preparation; inspect only')
compile_ev=BASE/'runs/M357-guarded-rtl-compile-01/RESULT.json'
assert w.sha(compile_ev)=='782a2ba2a125168a99c70302cf61a89ab21cbd8f50d4b8a560d52b2821501e78'
out.mkdir();shutil.copytree(src/'tv',out/'tv');(out/'verilog').mkdir()
shutil.copytree(src/'verilog/xsim.dir',out/'verilog/xsim.dir')
(out/'verilog/run_timeout.tcl').write_text('run all\nquit\n',encoding='utf-8')
result=dict(status='PREPARED_INDEPENDENT_RTL_TIMEOUT_NEGATIVE',build_id='0x4D333537',
    same_compiled_snapshot=True,compile_sha256=w.sha(compile_ev),executed=False,
    condition='Actual kernel ap_start followed by 200 cycles without ap_done -> fatal; separate cwd and original simulator rc saved',
    files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=w.sha(p)) for p in sorted(out.rglob('*')) if p.is_file()])
ev=BASE/'runs/M357-timeout-preparation-01/RESULT.json';w.atomic(ev,w.encoded(result),immutable=True)
print(json.dumps(dict(status=result['status'],sha256=w.sha(ev),files=len(result['files']))))
