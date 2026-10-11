"""Preserve sandbox compiler failure19; same input recovery21, no launch."""
import json
from m351_workflow import ROOT,BASE,HERE,encoded,sha,sync
from m441_host_io08 import atomic
OLD=ROOT/'tmp/m441_sim_coverage_19';OUT=ROOT/'tmp/m441_sim_coverage_21'
PRIOR=BASE/'runs/M441-W2-W4-simulation-coverage-19'
RUN=BASE/'runs/M441-W2-W4-simulation-coverage-21'
assert not OUT.exists() and not (RUN/'PREPARATION.json').exists()
p=json.loads((PRIOR/'PREPARATION.json').read_bytes())
failure=json.loads((PRIOR/'COMPILE.json').read_bytes())
assert failure['receipt']['original_rc']==1 and failure['status']=='FAIL_M441_SUPPLEMENTAL_COMPILE19'
assert not failure['snapshot']
log=OLD/'W2_max/verilog/compile_console.log'
assert 'Failed to compile generated C file' in log.read_text(encoding='utf-8-sig',errors='replace')
for c in p['cases']:
    for row in c['files']:
        src=ROOT/row['path'];assert sha(src)==row['sha256']
        dst=OUT/src.relative_to(OLD);atomic(dst,src.read_bytes(),immutable=True);assert sha(dst)==row['sha256']
for c in p['cases']:
    c['path']=c['path'].replace('m441_sim_coverage_19','m441_sim_coverage_21')
    for row in c['files']:row['path']=row['path'].replace('m441_sim_coverage_19','m441_sim_coverage_21')
    (ROOT/c['path']/'tv/rtldatafile').mkdir(parents=True)
s=(HERE/'m441_sim_evidence20.py').read_text(encoding='utf-8-sig')
s=s.replace('M441-W2-W4-simulation-coverage-19','M441-W2-W4-simulation-coverage-21').replace('m441_sim_coverage_19','m441_sim_coverage_21')
atomic(HERE/'m441_sim_evidence21.py',s.encode('utf-8'),immutable=True)
c=(HERE/'m441_sim_control20.py').read_text(encoding='utf-8-sig')
c=c.replace('M441-W2-W4-simulation-coverage-19','M441-W2-W4-simulation-coverage-21').replace('m441_sim_coverage_19','m441_sim_coverage_21')
c=c.replace('from m441_sim_evidence20 import','from m441_sim_evidence21 import').replace('CONTROL_POLICY20.json','CONTROL_POLICY21.json')
c=c.replace('m441_coverage19','m441_coverage21')
atomic(HERE/'m441_sim_control21.py',c.encode('utf-8'),immutable=True)
def ref(path):return dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path))
p.update(status='PREPARED_M441_SAME_INPUT_COMPILER_RECOVERY21',original_preparation_sha256=sha(PRIOR/'PREPARATION.json'),
         original_compile_FAIL_sha256=sha(PRIOR/'COMPILE.json'),original_STOP_sha256=sha(PRIOR/'STOP.json'),
         normal_tool_permission_probe='Same Vivado MinGW GCC --version fails under sandbox DLL relocation, succeeds in require_escalated execution',
         arithmetic_RTL_fixture_monitor_VIP_all_SHA_unchanged=True,collector_component_rejection_count=19,
         controller=ref(HERE/'m441_sim_control21.py'),collector=ref(HERE/'m441_sim_evidence21.py'),generator=ref(HERE/'m441_sim_recovery21.py'))
ev=RUN/'PREPARATION.json';atomic(ev,encoded(p),immutable=True)
policy=dict(status='PREPARED_M441_NORMAL_PERMISSION_SAME_INPUT_CONTROL21',preparation_sha256=sha(ev),
            files=[ref(HERE/'m441_sim_control21.py'),ref(HERE/'m441_sim_evidence21.py')],board=False)
atomic(RUN/'CONTROL_POLICY21.json',encoded(policy),immutable=True)
sync('latest_m441_simulation_preparation21',dict(status=p['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),board=False),
     '## M441补充仿真编译恢复21（2026-10-10）\n\nSHA '+sha(ev)+'；原19compile rc1/STOP保留，新21四夹具/DUT/观察器/VIP逐文件同SHA，只隔离目录/控制路径/新snapshot名。在正常工具权限下执行；相同GCC --version沙箱DLL重定位失败、正常权限成功。未仿真不能当数值/硬件失败，收集器实际拒绝19项（此前文字21项纠正）。固定预算/完整判据不改，0板端/生产。')
print(p['status'],sha(ev),flush=True)
