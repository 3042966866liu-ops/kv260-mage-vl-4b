"""Prove W4 A uses the already-observed exact M357 DUT before compilation."""
import json
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
prior=BASE/'runs/M438-weight-wait-preparation-01/RESULT.json'
pr=json.loads(prior.read_bytes());support=ROOT/'tmp/m438_weight_wait_03/verilog'
expected={ (ROOT/f['path']).name:f['sha256'] for f in pr['files'] if (ROOT/f['path']).parent==support and (ROOT/f['path']).suffix=='.v'}
target=ROOT/'tmp/m439_baseline_w4_01/verilog'
rows=[]
for p in (ROOT/'tmp/m357_hls_project_02/hls/syn/verilog').glob('*.v'):
    assert p.name in expected and sha(p)==expected[p.name] and sha(target/p.name)==expected[p.name],p
    rows.append(dict(path=p.relative_to(ROOT).as_posix(),copy=(target/p.name).relative_to(ROOT).as_posix(),sha256=sha(p)))
assert len(rows)>30
ev=BASE/'runs/M439-W4-baseline-source-guard-01/RESULT.json'
r=dict(status='PASS_M439_W4_A_EXACT_M357_DUT',build_id='0x4D333537',prior_sha256=sha(prior),files=rows,board=False)
atomic(ev,encoded(r),immutable=True)
sync('latest_m439_W4_baseline_source_guard',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=r['build_id'],board=False),
     f'## M439 W4原核来源核对（2026-10-07）\n\nSHA {sha(ev)}；{len(rows)}份实际A设计RTL与已冻结M438/M357 DUT逐文件同SHA，非重新综合的替代核。仅W4新代表输入/观察器，未模拟或上板；下一步编译及W4两模型A对照。')
print('M439_W4_BASELINE_SOURCE_PASS',sha(ev),len(rows))
