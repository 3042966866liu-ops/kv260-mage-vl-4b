"""Prepare an isolated export ONLY after terminal capacity evidence is verified.

No tool launch, synthesis, board operation or mutation of the original HLS project.
"""
import json
import shutil
from pathlib import Path
from check_decode_one_occupancy_v2 import audit, ROOT
from measurement import sha256, write_json

def main():
    base=ROOT/'deployment/mage_vl4b/optimization_v1'
    result_path=base/'gates/G02-decode-one-occupancy/attempt_03/result.json'
    if not result_path.exists():
        raise RuntimeError('Capacity gate has no terminal result; export preparation forbidden')
    result=json.loads(result_path.read_text())
    if result['status']!='PASS_CAPACITY_BACKPRESSURE_RTL_ONLY' or result['terminal_exit_code']!=0:
        raise RuntimeError('Capacity gate not passed')
    verified=audit()
    for key in ['peaks','modes','expected_outputs','evidence']:
        if verified[key]!=result[key]: raise RuntimeError('Capacity evidence changed: '+key)
    # Revalidate prior numerical, header, normal/shape RTL and timeout identities.
    prior_path=base/'runs/OP01-decode-one-prerequisite-audit/result.json'
    prior=json.loads(prior_path.read_text())
    if prior['status']!='PASS_SAVED_IDENTITY_AUDIT_ONLY': raise RuntimeError('Missing identity audit')
    for relative,digest in prior['evidence'].items():
        p=(ROOT/relative).resolve(); p.relative_to(ROOT)
        if sha256(p)!=digest: raise RuntimeError('Prior evidence changed: '+relative)
    source=ROOT/'tmp/op01_decode_one_rtl'
    target=ROOT/'tmp/op01_decode_one_export'
    if target.exists(): raise RuntimeError('Refuse existing export staging')
    # Keep identical project-relative layout; omit only reproducible simulation outputs.
    shutil.copytree(source,target,ignore=shutil.ignore_patterns('csim','sim','impl','*.log','*.jou'))
    app=target/'hls.app'
    app_text=app.read_text()
    if app_text.count('name="op01_decode_one_rtl"')!=1:
        raise RuntimeError('Unexpected source project identity')
    app.write_text(app_text.replace('name="op01_decode_one_rtl"','name="op01_decode_one_export"'))
    inputs={p.relative_to(target).as_posix():sha256(p) for p in target.rglob('*') if p.is_file()}
    write_json(target/'EXPORT_PREREQUISITES.json',dict(status='PREPARED_NOT_EXPORTED',
        build_id='0x4F503131',capacity_result_sha256=sha256(result_path),
        prior_identity_audit_sha256=sha256(prior_path),copied_inputs=inputs,
        board_deployed=False,performance_pass=False))
    print('ISOLATED_IP_EXPORT_PREPARED_NOT_EXECUTED')

if __name__=='__main__': main()
