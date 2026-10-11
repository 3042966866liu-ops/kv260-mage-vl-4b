"""Run the actual packaged isolated fixture with WSL filesystem-root adaptation."""
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PKG=ROOT/'deployment/mage_vl4b/optimization_v1/candidates/M416-layer13-PS-capture-01'
sys.path.insert(0,str(PKG))
import torch
from m414_entry import run_component
folder=ROOT/'tmp/m41601/component';folder.mkdir(parents=True,exist_ok=True)
wrapper=folder/'wsl_entry.py'
wrapper.write_text("import runpy,sys\nfrom pathlib import Path\nimport frozen_video_identity as identity\nidentity.RELEASE=Path(sys.argv[1])\nrunpy.run_path(str(Path(__file__).resolve().parents[3]/'deployment/mage_vl4b/optimization_v1/candidates/M416-layer13-PS-capture-01/m416_component_entry.py'),run_name='__main__')\n",encoding='utf-8')
answer,isolation=run_component(ROOT,folder,wrapper)
assert isolation['parent_state_unchanged'] and isolation['return_code']==0
assert answer['target_component']['topology']['selected_layer']==13
assert answer['target_component']['topology_rejects']==4
assert answer['target_component']['bad_shapes_rejected']==4
assert answer['component']['rejects']==5
result=dict(status='PASS_M416_ACTUAL_ISOLATED_LAYER13_COMPONENT',component=answer,
            isolation=isolation,actual_packaged_entry=True,
            WSL_filesystem_root_substitution_only=True,model_forward_calls=0,
            explicit_small_weights_attention_fixture=True,board_run=False)
with (folder/'RESULT.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print('M416_COMPONENT_CHECK='+json.dumps(result),flush=True)
