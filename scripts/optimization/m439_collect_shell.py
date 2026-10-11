"""Saved-only full-shell closure; inherit strict checks, verify separate-bit XSA."""
from m351_workflow import ROOT,BASE,HERE,sha
import json
# Keep the original proven classifier and all resource/timing/DRC checks.
# Only this attempt's readback evidence can classify its retained startup errors.
for name,status in [('M439-auxiliary-checkpoint-readback-01','PASS_M439_AUXILIARY_CHECKPOINT_READBACK_ONLY'),
                    ('M439-hwh-abi-01','PASS_M439_MATCHING_HWH_ABI_TOPOLOGY_ONLY')]:
    p=BASE/'runs'/name/'RESULT.json'
    assert json.loads(p.read_bytes())['status']==status
s=(HERE/'m357_collect_shell.py').read_text(encoding='utf-8').replace('m357','m439').replace('M357','M439').replace('0x4D333537','0x4D343339')
anchor="        result['status']='PASS_FULL_SHELL_ROUTED_TIMING'"
assert s.count(anchor)==1
extra='''        with zipfile.ZipFile(OUT/'m439_t32.xsa') as archive:
            assert not any(name.endswith('.bit') for name in archive.namelist())
            assert archive.read('qwen25_mixed_gs.hwh')==(ROOT/hwh['candidate_path']).read_bytes()
        result['xsa_full_hwh_exact']=True;result['xsa_embeds_bit']=False
        controls=json.loads((BASE/'runs/M439-shell-control-preparation-01/RESULT.json').read_bytes())
        assert w.sha(ROOT/'scripts/optimization/m439_build_shell.tcl')==controls['Tcl_sha256']
        assert w.sha(ROOT/'scripts/optimization/m439_run_shell.ps1')==controls['controller_sha256']
        result['shell_controls_sha256']=w.sha(BASE/'runs/M439-shell-control-preparation-01/RESULT.json')
        result['collector_template_sha256']=w.sha(ROOT/'scripts/optimization/m357_collect_shell.py')
        result['actual_collector_sha256']=w.sha(ROOT/'scripts/optimization/m439_collect_shell.py')
'''
s=s.replace(anchor,extra+anchor)
ns={'__name__':'m439_collect_shell','__file__':str(HERE/'m439_collect_shell.py')}
exec(compile(s,str(HERE/'m439_collect_shell.py')+':same-strict-shell','exec'),ns)
if __name__=='__main__':raise SystemExit(ns['main'](False))
