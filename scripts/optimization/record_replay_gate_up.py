"""Record narrowly scoped offline comparison of existing board captures."""
import json
from pathlib import Path
from measurement import sha256, write_json, exclusive_lock
root=Path(__file__).resolve().parents[2]
base=root/'deployment/mage_vl4b/optimization_v1'
path=base/'runs/OP01-replay01-gate-up-reference/result.json'
data=json.loads(path.read_text())
assert len(data['metrics'])==2
assert all(v['elements']==9728 and v['exact_count']==9728 and v['max_abs']==0 for v in data['metrics'].values())
entry=dict(status='PASS_REAL_LAYER0_GATE_UP_BIT_EXACT_ONLY',result=str(path.relative_to(root)),sha256=sha256(path),
    full_model_pass=False,performance_pass=False,new_board_execution=False)
with exclusive_lock(base/'evidence.lock'):
    p=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    index=json.loads(p.read_text(encoding='utf-8-sig'))
    index['latest_replay_gate_up_same_quant']=entry
    write_json(p,index)
    p=base/'STATE.json'; state=json.loads(p.read_text())
    state['results']['replay_gate_up_same_quant']=entry
    state['next_action']='Controlled memory-lifecycle comparison from the same KV checkpoint, with matched cache preparation and runtime; preserve stable kernel. Gate/Up exact only, not full-model acceptance.'
    write_json(p,state)
print(entry['status'])
