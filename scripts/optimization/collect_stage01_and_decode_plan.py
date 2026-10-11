"""Persist bounded probe evidence and the user-revised near-term objective."""
import json
from pathlib import Path
from measurement import exclusive_lock, sha256, write_json

root=Path(__file__).resolve().parents[2]
base=root/'deployment/mage_vl4b/optimization_v1'
log=root/'tmp/op01_stage01/run.log'
text=log.read_text(encoding='utf-8-sig')
assert '__OP01_STAGE_RC_0__' in text
probe=json.loads(text.split('OP01_STAGE_JSON_BEGIN',1)[1].split('OP01_STAGE_JSON_END',1)[0])
assert probe['status']=='MEASURED' and not probe['errors']
assert len(probe['records'])==72 and all(x['byte_exact'] for x in probe['records'])
assert all(probe[k] for k in ('buffer_released','boot_unchanged','cmdline_unchanged'))
assert not any(probe[k] for k in ('overlay_loaded','dma_launched','model_executed'))
manifest=base/'candidates/OP01-stage-01/PACKAGE_MANIFEST.json'
assert probe['package_manifest_sha256']==sha256(manifest)
out=base/'gates/G01-stage-transfer/attempt_01/result.json'
audit=base/'runs/OP01-decode97-audit-v1/result.json'
next_action='Explain/reproduce SYS02 97.141343s incremental Decode. Freeze input; instrument exclusive read/copy/sync/PS/PL/head spans and state checkpoints, validate a real family against same-quant reference, then one evidence-selected change. No immediate speed target or kernel rewrite.'
with exclusive_lock(base/'control.lock'):
    if out.exists():raise RuntimeError('Immutable gate exists')
    write_json(out,dict(status='MEASURED',scope='Warm-cache transfer only; not Decode attribution or speedup',
        uart_log_sha256=sha256(log),board_result=probe))
    path=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    index=json.loads(path.read_text(encoding='utf-8-sig'))
    index['latest_optimization_v1_stage_probe']=dict(status='MEASURED',result=str(out.relative_to(root)),sha256=sha256(out),overlay_loaded=False)
    index['latest_decode97_audit']=dict(status='PARTIAL_ATTRIBUTION',result=str(audit.relative_to(root)),sha256=sha256(audit))
    write_json(path,index)
    path=base/'STATE.json';state=json.loads(path.read_text())
    state['results']['stage_probe']=str(out.relative_to(root))
    state['results']['decode97_audit']=str(audit.relative_to(root))
    state['near_term_objective']=next_action
    state['performance_targets_scope']='Long-term aspirational gates, not imminent first-phase commitments'
    state['next_action']=next_action
    write_json(path,state)
print('Evidence persisted; no numerical/performance promotion')
