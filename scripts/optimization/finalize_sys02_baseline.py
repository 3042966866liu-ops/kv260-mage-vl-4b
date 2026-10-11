"""Register collected single-request evidence without granting G01.2 or any tier."""
import json
from pathlib import Path
from measurement import exclusive_lock,sha256,write_json

root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
source=base/'gates/G01-SYS-development/attempt_02/board_result.json'
summary=base/'runs/OP01-SYS-02-summary/result.json'
board=json.loads(source.read_text());measured=json.loads(summary.read_text())
assert measured['board_result_sha256']==sha256(source)
assert measured['status']=='MEASURED_DEVELOPMENT'
evidence=board['board_evidence']
record=dict(status='PROVISIONAL',scope='One actual raw4s SYS request with two valid tokens',
    records=[dict(source=str(source.relative_to(root)),sha256=sha256(source),summary=str(summary.relative_to(root)))],
    metrics=measured['metrics'],formal_sample_count=0,numerical_acceptance=False,quality_acceptance=False,
    achieved_level=None,remaining=['3-task development baseline','same-quant2/8/32 numerical gate','128 valid generation','formalG08'])
with exclusive_lock(base/'control.lock'):
    target=base/'baselines/SYS_BASELINE.json'
    if target.exists():raise RuntimeError('Do not replace baseline without explicit versioning')
    write_json(target,record)
    state_path=base/'STATE.json';state=json.loads(state_path.read_text())
    state['results']['SYS_BASELINE']=str(target.relative_to(root))
    state['results']['group_reference']=str((base/'runs/OP01-group-reference-v1/result.json').relative_to(root))
    state['next_action']='SYS02 complete. Diagnose staged read/copy/sync separately and prepare same-quant numerical capture; no repeated identical SYS2 or G01.2 promotion.'
    write_json(state_path,state)
print(json.dumps(dict(status='PROVISIONAL',metrics=measured['metrics'],
    stage_bytes=evidence['stage_bytes'],stage_s=evidence['stage_ms']/1000,
    asynchronous_phase_ms=evidence['phase_ms'])))
