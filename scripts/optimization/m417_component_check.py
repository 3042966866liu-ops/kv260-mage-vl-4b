"""Exercise the actual isolated oracle child; no model forward or board access."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PKG=ROOT/'deployment/mage_vl4b/optimization_v1/candidates/M417-layer13-saved-reference-01'
sys.path.insert(0,str(PKG))
import torch
from m414_entry import run_component
folder=ROOT/'tmp/m41701/component';folder.mkdir(parents=True,exist_ok=True)
answer,isolation=run_component(ROOT,folder,PKG/'m417_component_entry.py')
assert isolation['parent_state_unchanged'] and isolation['return_code']==0
assert answer['independent_int32_full_output_equal'] and answer['bindings_restored'] and answer['invalid_native_inputs_rejected']==4
result=dict(status='PASS_M417_ACTUAL_ISOLATED_ORACLE_COMPONENT',component=answer,isolation=isolation,
            actual_packaged_entry=True,filesystem_root_argument_only=True,model_forward_calls=0,
            explicit_small_weights_fixture=True,board_run=False)
with (folder/'RESULT.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print('M417_ISOLATED_COMPONENT_PASS',flush=True)
