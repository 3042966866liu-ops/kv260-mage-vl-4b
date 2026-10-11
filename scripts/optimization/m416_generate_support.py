"""Generate actual new producer/collector checks, retaining explicit synthetic scope."""
from m351_workflow import HERE, atomic

source=(HERE/'m408_support04.py').read_text(encoding='utf-8')
source=source.replace('M408','M416').replace('latest_m408_','latest_m416_')
source=source.replace('m408_workflow04','m416_workflow').replace('m408_control06.ps1','m416_control.ps1')
source=source.replace('m408_support04.py','m416_support.py').replace('m408_gate.py','m416_gate.py')
source=source.replace('tmp/m40804','tmp/m41601').replace('m408_mlp_capture_04','m416_layer13_capture_01')
source=source.replace('M416-local-MLP-support-04','M416-layer13-PS-support-01')
source=source.replace('selected_layer=12','selected_layer=13').replace('encoder.layers.12.layer.layer','encoder.layers.13.layer.layer')
source=source.replace('2026-10-05','2026-10-06')
source=source.replace("        producer.time = SimpleNamespace(sleep=lambda seconds:None)\n",'')
needle="        producer.OUTPUT.parent.mkdir()"
assert source.count(needle)==1
source=source.replace(needle,"        producer.time = SimpleNamespace(sleep=lambda seconds:None)  # Export pacing stub only, explicit synthetic Windows fixture\n"+needle)
needle="capture_manifest=capture,elapsed_s_diagnostic_not_performance=1,"
assert source.count(needle)==1
source=source.replace(needle,"component_isolation=dict(separate_process=True,parent_state_unchanged=True,return_code=0,explicit_synthetic_fixture=True),\n            "+needle)
needle="        mutations += [complete+complete"
assert source.count(needle)==1
source=source.replace(needle,"        for key,value in [('separate_process',False),('parent_state_unchanged',False),('return_code',1)]:\n            obj=copy.deepcopy(good);obj['component_isolation'][key]=value;mutations.append(export(obj))\n"+needle)
needle="    r = dict(status='PASS_M416_ACTUAL_CONTROL_COLLECTION_SUPPORT'"
assert source.count(needle)==1
source=source.replace(needle,"    component_path=ROOT/'tmp/m41601/component/RESULT.json'\n    component=json.loads(component_path.read_bytes());assert component['isolation']['parent_state_unchanged']\n    import ast\n    for row in manifest['files']:\n        if row['path'].endswith('.py'):ast.parse((pkg/row['path']).read_text(encoding='utf-8-sig'),feature_version=(3,10))\n    bash=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/usr/bin/bash','-n','/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/deployment/mage_vl4b/optimization_v1/candidates/M416-layer13-PS-capture-01/run_m416_capture.sh'],capture_output=True)\n    assert bash.returncode==0,bash.stderr\n"+needle)
needle="actual_NPY_save_file_tensor_SHA=True,"
source=source.replace(needle,"actual_isolated_layer13_component=component,component_sha256=sha(component_path),python310_syntax=True,bash_n=True,\n        "+needle)
atomic(HERE/'m416_support.py',source.encode('utf-8'),immutable=True)
print('M416_SUPPORT_SOURCE_READY')
