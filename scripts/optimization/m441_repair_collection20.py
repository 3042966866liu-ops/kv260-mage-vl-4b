"""Preserve preflight failure; derive only collector/control, no new fixtures."""
from m351_workflow import ROOT,BASE,HERE,encoded,sha,sync
from m441_host_io08 import atomic
RUN=BASE/'runs/M441-W2-W4-simulation-coverage-19'
r=dict(status='FAIL_M441_SUPPLEMENTAL_COLLECTOR_PREFLIGHT19',cause='Historical vendor max.log contains non-UTF8 bytes; strict log decoder failed before any new tool start',
       RTL_started=False,tools_started=False,board=False)
ev=RUN/'COLLECTOR_PREFLIGHT_FAILURE.json';atomic(ev,encoded(r),immutable=True)
sync('latest_m441_simulation_collector_failure19',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),board=False),
     '## M441补充收集器19前置停止（2026-10-10）\n\nSHA '+sha(ev)+'；原vendor日志有非UTF8字节，前置严格解码失败，0新工具。新20仅容错诊断文本解码，原字节SHA/完整输出核对不降；冻结19输入不改。')
s=(HERE/'m441_sim_evidence19.py').read_text(encoding='utf-8-sig')
s=s.replace("(sim/'max.log').read_text(encoding='utf-8-sig')", "(sim/'max.log').read_text(encoding='utf-8-sig',errors='replace')")
atomic(HERE/'m441_sim_evidence20.py',s.encode('utf-8'),immutable=True)
c=(HERE/'m441_sim_control19.py').read_text(encoding='utf-8-sig').replace('from m441_sim_evidence19 import','from m441_sim_evidence20 import')
anchor="    for field in ('controller','collector','generator'):assert sha(ROOT/p[field]['path'])==p[field]['sha256']"
assert anchor in c
c=c.replace(anchor,anchor+"\n    policy=json.loads((RUN/'CONTROL_POLICY20.json').read_bytes())\n    assert policy['preparation_sha256']==sha(PREP)\n    for row in policy['files']:assert sha(ROOT/row['path'])==row['sha256']")
atomic(HERE/'m441_sim_control20.py',c.encode('utf-8'),immutable=True)
print('Derived collector/control20 without changing frozen19 inputs')
