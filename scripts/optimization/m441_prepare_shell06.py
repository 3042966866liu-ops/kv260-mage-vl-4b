"""Use proven board topology/export controls after independent M441 gates only."""
from m351_workflow import HERE,BASE,ROOT,sha,atomic,encoded,sync
import json

def main():
    from m441_core_ooc06 import ready
    ready()
    core=BASE/'runs/M441-record-pipeline-core-OOC-closure-01/RESULT.json'
    from m441_boundary_control06 import synchronized
    c=synchronized(core,'PASS_M441_SAME_CONSTRAINT_CORE_ROUTED_TIMING','latest_m441_record_pipeline_core_OOC')
    assert all(c['checks'].values()) and c['original_rc']==0
    source=(HERE/'m439_prepare_shell.py').read_text(encoding='utf-8-sig')
    begin=source.index("s=s[:begin]+");end=source.index("s=s.replace('m357'",begin)
    block="""s=s[:begin]+'''    gates=[('M441-full-numeric-csim-01','PASS_M441_FULL_REAL_WEIGHT_CHAIN_CSIM'),
           ('M441-W4-zero-continuation-05','PASS_M441_W4_MLPDOWN_FULL_ZERO04'),
           ('M441-long-B-gate_up-zero-02','PASS_M441_COMPLETE_CHAIN_RTL_NUMERIC_AND_PROTOCOL'),
           ('M441-boundary-rtl-06','PASS_M441_BOUNDARY_RTL'),
           ('M441-boundary-timeout-06','PASS_M441_BOUNDARY_EXPECTED_TIMEOUT'),
           ('M441-record-pipeline-core-OOC-closure-01','PASS_M441_SAME_CONSTRAINT_CORE_ROUTED_TIMING')]
'''+s[end:]
"""
    source=source[:begin]+block+source[end:]
    source=source.replace('m439','m441').replace('M439','M441').replace('0x4D343339','0x4D343431')
    source=source.replace('m441_prepare_shell.py','m441_prepare_shell06.py')
    # Execute only the exact adapted proven preparer; provenance frozen below.
    ns={'__name__':'__main__','__file__':str(HERE/'m441_prepare_shell06.py')}
    exec(compile(source,'m441_prepare_shell06:strict_template','exec'),ns)
    prep=BASE/'runs/M441-shell-preparation-01/RESULT.json';p=json.loads(prep.read_bytes())
    tcl=HERE/'m441_build_shell.tcl';driver=HERE/'m441_run_shell.ps1'
    r=dict(status='PREPARED_M441_FROZEN_SHELL_CONTROLS',build_id='0x4D343431',shell_preparation_sha256=sha(prep),
        Tcl_sha256=sha(tcl),controller_sha256=sha(driver),preparer_sha256=sha(HERE/'m441_prepare_shell06.py'),
        templates=[dict(path=(HERE/n).relative_to(ROOT).as_posix(),sha256=sha(HERE/n)) for n in ['m439_prepare_shell.py','m357_prepare_shell.py','m357_build_shell.tcl','m357_run_shell.ps1']],
        topology_and_clock_unchanged=True,independent_protocol06=True,old_random_verdict_unchanged=True,separate_bit_HWH_export=True,
        shell_executed=False,board=False,promotion=False)
    ev=BASE/'runs/M441-shell-control-preparation-06/RESULT.json';atomic(ev,encoded(r),immutable=True)
    sync('latest_m441_shell_control_preparation06',dict(status=r['status'],sha256=sha(ev),result=ev.relative_to(ROOT).as_posix(),board=False),
         f'## M441 整壳控制冻结06（2026-10-09）\n\nSHA {sha(ev)}；最大压力/timeout/核心均通过后，干净输入与原板级拓扑/时钟保持，独立Build0x4D343431；复用separate bit/HWH导出避免include-bit旧失败。仅准备，0整壳实现/板端。')
    print(r['status'],sha(ev),flush=True)

if __name__=='__main__':main()
