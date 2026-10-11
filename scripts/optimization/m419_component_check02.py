"""Actual staged binding child; no developer directory or model/FPGA execution."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
assert sys.flags.isolated and all(Path(p).resolve()!=HERE for p in sys.path if p)
pkg=ROOT/'deployment/mage_vl4b/optimization_v1/candidates/M419-layer13-complete-MLP-02'
ref=ROOT/'deployment/mage_vl4b/optimization_v1/candidates/M417-layer13-saved-reference-02'
lower=ROOT/'deployment/mage_vl4b/optimization_v1/candidates/M418-visual-linear-01'
sys.path[:0]=[str(pkg),str(ref),str(lower)]
import torch
from m414_entry import run_component
folder=ROOT/'tmp/m41902/component';folder.mkdir(parents=True,exist_ok=True)
answer,isolation=run_component(ROOT,folder,pkg/'m419_component_entry.py')
assert isolation['parent_state_unchanged'] and isolation['return_code']==0
result=dict(status='PASS_M419_CLEAN_STAGED_BINDING_COMPONENT',component=answer,isolation=isolation,
            no_developer_directory_on_child_path=True,actual_packaged_entry=True,model_forward_calls=0,board_run=False)
with (folder/'RESULT.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print('M419_CLEAN_STAGED_BINDING_COMPONENT_PASS',flush=True)
