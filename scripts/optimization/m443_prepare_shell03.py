"""Prepare unchanged board topology only after new M443 RTL and routed core."""
import json
from m351_workflow import ROOT, BASE, HERE, sha, encoded, sync
from m441_host_io08 import atomic

def main():
    from m443_core_ooc03 import ready
    ready()
    p=BASE/'runs/M443-pair-pipeline-core-OOC-closure-03/RESULT.json'
    core=json.loads(p.read_bytes())
    assert core['status']=='PASS_M443_SAME_CONSTRAINT_CORE_ROUTED_TIMING'
    assert core['build_id']=='0x4D343433' and core['original_rc']==0 and all(core['checks'].values())
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        assert sha(p) in (ROOT/name).read_text(encoding='utf-8-sig')
    for item in core['evidence']:assert sha(ROOT/item['path'])==item['sha256']
    source=(HERE/'m439_prepare_shell.py').read_text(encoding='utf-8-sig')
    begin=source.index('s=s[:begin]+');end=source.index("s=s.replace('m357'",begin)
    gates=[('M443-full-numeric-csim-03','PASS_M443_FULL_REAL_WEIGHT_CHAIN_CSIM03'),
           ('M443-W2-W4-pair-pipeline-RTL-04','PASS_M441_W2_W4_SUPPLEMENTAL_SIMULATION_CLOSED19'),
           ('M443-pair-pipeline-core-OOC-closure-03','PASS_M443_SAME_CONSTRAINT_CORE_ROUTED_TIMING')]
    block="s=s[:begin]+"+repr('    gates='+repr(gates)+'\n')+"+s[end:]\n"
    source=source[:begin]+block+source[end:]
    source=source.replace('m439','m443').replace('M439','M443').replace('0x4D343339','0x4D343433')
    source=source.replace("s=s.replace('assert len(same)","s=s.replace('tmp/m443_hls_project_02','tmp/m443_hls_project_03')\ns=s.replace('assert len(same)")
    source=source.replace('m443_prepare_shell.py','m443_prepare_shell03.py')
    # All mutations occur only after ready(), exact evidence and raw SHA checks.
    ns={'__name__':'__main__','__file__':str(HERE/'m443_prepare_shell03.py')}
    exec(compile(source,'m443_prepare_shell03:checked_template','exec'),ns)
    prep=BASE/'runs/M443-shell-preparation-01/RESULT.json'
    value=dict(status='PREPARED_M443_FROZEN_SHELL_CONTROLS03',build_id='0x4D343433',
               shell_preparation_sha256=sha(prep),
               files=[dict(path=(HERE/name).relative_to(ROOT).as_posix(),sha256=sha(HERE/name))
                      for name in ('m443_build_shell.tcl','m443_run_shell.ps1','m443_prepare_shell03.py',
                                   'm439_prepare_shell.py','m357_prepare_shell.py','m357_build_shell.tcl','m357_run_shell.ps1')],
               topology_and_clocks_unchanged=True,separate_bit_HWH_export=True,
               shell_executed=False,board=False,promotion=False)
    out=BASE/'runs/M443-shell-control-preparation-03/RESULT.json'
    atomic(out,encoded(value),immutable=True)
    sync('latest_m443_shell_control_preparation03',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),board=False),
         '## M443整壳控制冻结03（2026-10-10）\n\nSHA '+sha(out)+'；新完整真实CSim、六项实际RTL及同4.8ns核心布线通过后，严格复用原板级拓扑/200与100MHz、干净输入和独立bit/HWH导出。此级仅准备，尚未整壳实现或上板；稳定M441及回滚保持。')
    print(value['status'],sha(out))

if __name__=='__main__':main()
