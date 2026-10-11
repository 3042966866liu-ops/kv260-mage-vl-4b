"""Append interpretation caveat without replacing any raw measurements."""
import json
from pathlib import Path
from measurement import sha256,write_json,exclusive_lock
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
ownership=root/'tmp/op01_full_file_scan01/ownership.log'
if '__SCAN_OWNER_RC_0__' not in ownership.read_text(encoding='utf-8-sig'):raise RuntimeError('Ownership probe incomplete')
out=base/'gates/G01-full-file-scan/attempt_01/interpretation.json'
with exclusive_lock(base/'control.lock'):
    if out.exists():raise RuntimeError('Immutable qualification')
    write_json(out,dict(status='MEASURED_WITH_RESIDENCY_CAVEAT',
        source_sha256=sha256(out.parent/'board_result.json'),ownership_log_sha256=sha256(ownership),
        mincore_usable_as_residency_proof=False,
        reason='Non-root probe, root-owned mode0644 weights; Linux can mask mincore with all-ones for non-owner/non-writer. Do not interpret all-resident observations as proof.',
        retained_evidence=['read timings','read_bytes and rchar process counters with scope caveats','exact plan/order/byte accounting','two-scan hash equality'],
        not_proven=['inference-memory cache behavior','same-quant numerical correctness','model speedup'],
        kernel_source='https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/+/refs/tags/v5.14-rc5/mm/mincore.c'))
    path=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';index=json.loads(path.read_text(encoding='utf-8-sig'))
    index['latest_full_file_scan']['interpretation']=str(out.relative_to(root))
    index['latest_full_file_scan']['mincore_usable_as_residency_proof']=False
    index['latest_file_cache_probe']['mincore_usable_as_residency_proof']=False
    write_json(path,index)
    path=base/'STATE.json';state=json.loads(path.read_text())
    state['next_action']='Idle complete scan measured8.2458s then1.7739s, second read_bytes0, no repeated intervals. mincore unusable under non-owner permissions. Next actual SYS05 checkpoint/runtime-memory replay with read I/O counters and privilege-aware residency; same-quant family check before optimization.'
    write_json(path,state)
print('SCAN_INTERPRETATION_QUALIFIED')
