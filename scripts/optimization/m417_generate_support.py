"""Adapt proven actual oracle producer/collector tests to the layer13 packet."""
from m351_workflow import HERE,atomic
source=(HERE/'m409_support.py').read_text(encoding='utf-8')
source=source.replace('M409','M417').replace('m409_workflow','m417_workflow').replace('m409_gate.py','m417_gate.py').replace('m409_control.ps1','m417_control.ps1').replace('m409_support.py','m417_support.py').replace('latest_m409_reference_','latest_m417_reference_')
source=source.replace('tmp/m40901','tmp/m41701').replace('M417-reference-support-01','M417-layer13-reference-support-01').replace('selected_layer=12','selected_layer=13').replace('encoder.layers.12.mlp.','encoder.layers.13.mlp.').replace('M408_CAPTURE_EXPECTED.json','M416_CAPTURE_EXPECTED.json')
source=source.replace("good=dict(bad,status='PASS_M417_SAVED_MLP_EXACT_SOFTWARE_REFERENCE',", "good=dict(bad,component_isolation=dict(separate_process=True,parent_state_unchanged=True,return_code=0),status='PASS_M417_SAVED_MLP_EXACT_SOFTWARE_REFERENCE',")
anchor='        mutations += [complete+complete,'
assert source.count(anchor)==1
source=source.replace(anchor,"        for k,v in [('separate_process',False),('parent_state_unchanged',False),('return_code',1)]:\n            obj=copy.deepcopy(good);obj['component_isolation'][k]=v;mutations.append(export(obj))\n"+anchor)
anchor="    v=dict(status='PASS_M417_ACTUAL_REFERENCE_CONTROL_AND_RECOVERY',"
assert source.count(anchor)==1
extra="""    from m417_prepare import PKG
    component_path=ROOT/'tmp/m41701/component/RESULT.json'
    checked=json.loads(component_path.read_bytes())
    assert checked['isolation']['parent_state_unchanged'] and checked['isolation']['return_code']==0
    assert checked['actual_packaged_entry'] and checked['component']['independent_int32_full_output_equal']
    import ast
    for p in PKG.glob('*.py'):ast.parse(p.read_bytes(),feature_version=(3,10))
    syntax=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','bash','-n','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/deployment/mage_vl4b/optimization_v1/candidates/M417-layer13-saved-reference-01/run_m417_reference.sh'],capture_output=True)
    assert syntax.returncode==0
"""
source=source.replace(anchor,extra+anchor)
source=source.replace('actual_default_off_export_save_capture_load=True,','actual_isolated_component=checked,actual_isolated_component_sha256=sha(component_path),python310_syntax=True,bash_n=True,actual_default_off_export_save_capture_load=True,')
atomic(HERE/'m417_support.py',source.encode('utf-8'),immutable=True)
print('M417_SUPPORT_READY')
