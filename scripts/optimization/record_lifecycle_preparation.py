import json
from pathlib import Path
from measurement import sha256,write_json,exclusive_lock
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
with exclusive_lock(base/'evidence.lock'):
    path=base/'STATE.json';state=json.loads(path.read_text())
    state['results']['lifecycle_preparation']=dict(status='OFFLINE_PREPARATION_ONLY',
        read_plan='runs/OP01-lifecycle-read-plan/plan.json',
        read_plan_sha256=sha256(base/'runs/OP01-lifecycle-read-plan/plan.json'),
        board_executed=False,performance_pass=False)
    state['next_action']='Integrate lifecycle_trial and lifecycle_reads into isolated authorized runner, verify frozen vision close resolution and import gate, then actual visual-forward A/B/C checkpoint experiment; no stable package changes.'
    write_json(path,state)
print('LIFECYCLE_PREPARATION_STATE_RECORDED')
