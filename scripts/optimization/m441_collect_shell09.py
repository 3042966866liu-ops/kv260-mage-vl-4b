"""Saved-only full-shell closure; inherit strict checks, verify separate-bit XSA."""
import m351_workflow as workflow
from m441_host_io08 import atomic
workflow.atomic=atomic
from m351_workflow import ROOT,BASE,HERE,sha
import json
# Keep the original proven classifier and all resource/timing/DRC checks.
# Only this attempt's readback evidence can classify its retained startup errors.
for name,status in [('M441-auxiliary-checkpoint-readback-02','PASS_M441_AUXILIARY_CHECKPOINT_READBACK_ONLY'),
                    ('M441-hwh-abi-01','PASS_M441_MATCHING_HWH_ABI_TOPOLOGY_ONLY')]:
    p=BASE/'runs'/name/'RESULT.json'
    assert json.loads(p.read_bytes())['status']==status
s=(HERE/'m357_collect_shell.py').read_text(encoding='utf-8').replace('m357','m441').replace('M357','M441').replace('0x4D333537','0x4D343431')
anchor="        result['status']='PASS_FULL_SHELL_ROUTED_TIMING'"
assert s.count(anchor)==1
extra='''        with zipfile.ZipFile(OUT/'m441_t32.xsa') as archive:
            assert not any(name.endswith('.bit') for name in archive.namelist())
            assert archive.read('qwen25_mixed_gs.hwh')==(ROOT/hwh['candidate_path']).read_bytes()
        result['xsa_full_hwh_exact']=True;result['xsa_embeds_bit']=False
        controls=json.loads((BASE/'runs/M441-shell-control-preparation-07/RESULT.json').read_bytes())
        assert w.sha(ROOT/'scripts/optimization/m441_build_shell.tcl')==controls['Tcl_sha256']
        assert w.sha(ROOT/'scripts/optimization/m441_run_shell.ps1')==controls['controller_sha256']
        result['shell_controls_sha256']=w.sha(BASE/'runs/M441-shell-control-preparation-07/RESULT.json')
        result['collector_template_sha256']=w.sha(ROOT/'scripts/optimization/m357_collect_shell.py')
        result['actual_collector_sha256']=w.sha(ROOT/'scripts/optimization/m441_collect_shell09.py')
'''
s=s.replace('M441-auxiliary-checkpoint-readback-01','M441-auxiliary-checkpoint-readback-02')
s=s.replace(anchor,extra+anchor)
ns={'__name__':'m441_collect_shell','__file__':str(HERE/'m441_collect_shell07.py')}
exec(compile(s,str(HERE/'m441_collect_shell07.py')+':same-strict-shell','exec'),ns)
if __name__=='__main__':raise SystemExit(ns['main'](False))
