import json
from pathlib import Path
from measurement import sha256,write_json,exclusive_lock
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
source=base/'runs/OP01-lifecycle-attribution/result.json';result=json.loads(source.read_text())
assert result['status']=='MEASURED_VALIDATED_DIAGNOSTIC_ONLY'
entry=dict(result=str(source.relative_to(root)),sha256=sha256(source),performance_pass=False,
    conclusion='No substantial Decode benefit established by vision release; warm-read preparation cost cannot be excluded from serving claims')
with exclusive_lock(base/'evidence.lock'):
    p=base/'STATE.json';state=json.loads(p.read_text());state['results']['lifecycle_analysis']=entry
    state['next_action']='Inspect actual T=1 work in stable T32 kernel and device-wait boundaries; plan bounded true sequential Decode without extra weight scans. Do not promote vision release/trim or warmed single-step as formal throughput.'
    write_json(p,state)
    p=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';index=json.loads(p.read_text(encoding='utf-8-sig'))
    index['latest_lifecycle_analysis']=entry;write_json(p,index)
print('LIFECYCLE_ANALYSIS_RECORDED_NO_PROMOTION')
