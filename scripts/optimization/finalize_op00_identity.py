"""Join scoped completed evidence; never relabel earlier failed attempts."""
import json
from pathlib import Path
from measurement import exclusive_lock, sha256, write_json

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
paths=dict(host=BASE/'baselines/identity.json',wsl=BASE/'baselines/OP00_WSL_IDENTITY.json',
    environment=BASE/'gates/G00-audit/attempt_01/result.json',
    restore=BASE/'gates/G00.2/attempt_01/result.json',
    kernel=BASE/'gates/G00-stable-probe/attempt_03/result.json',
    files=BASE/'gates/G00-model-inventory/attempt_01/result.json',
    imports=BASE/'gates/G00-decoder-dependency/attempt_01/result.json')
data={k:json.loads(p.read_text()) for k,p in paths.items()}
host=data['host']; files=data['files']['board_result']; kernel=data['kernel']['board_result']
install=data['imports']['board_result']; imports=install['probe']
checks={
    'host_reference_paths':all((ROOT/x['path']).is_file() for x in host['references']),
    'unchanged_stable_artifacts':host['stable_manifest_match'] and all(x['match'] for x in host['stable_files']),
    'wsl_full_weight_identity':data['wsl']['status']=='PASS',
    'board_environment':data['environment']['status']=='PASS',
    'actual_kernel_identity':data['kernel']['status']=='PASS' and kernel['build_id']=='0x4D395832',
    'verified_recovery':data['restore']['status']=='PASS',
    'completed_file_checks_from_retained_failed_audit':len(files['packages'])==6 and len(files['layouts'])==2,
    'runtime_imports':imports['status']=='PASS' and imports['runtime_imports_pass'] and len(imports['imports'])==8,
    'isolated_decoder':install['status']=='PASS' and imports['raw_video_decode_pass'],
    'network_restored':install['temporary_address_cleanup_exit']==0 and install['route_before']==install['route_after'],
}
if not all(checks.values()):raise RuntimeError('Identity prerequisites incomplete: '+repr(checks))
with exclusive_lock(BASE/'control.lock'):
    output=BASE/'gates/G00.1/attempt_01/result.json'
    if output.exists():raise RuntimeError('Immutable G00.1 exists')
    refs=[dict(path=str(p),sha256=sha256(p)) for p in paths.values()]
    env_path=BASE/'contracts/environment_verified_v1.json'
    write_json(env_path,dict(status='PASS_G00.1',build_id=kernel['build_id'],
        board_python=imports['python'],board_platform=imports['platform'],runtime_imports=imports['imports'],
        isolated_decoder=install['isolated_site'],decoder_manifest_sha256=install['installed_manifest_sha256'],
        python_paths=imports['python_path'],wsl=data['wsl'],evidence=refs,
        transport='COM3 control/results; user-authorized bounded temporary Ethernet artifacts; no SSH'))
    identity_path=BASE/'baselines/verified_identity_v1.json'
    write_json(identity_path,dict(status='PASS_G00.1',build_id=kernel['build_id'],git_commit=None,
        git_directory_present=False,board_packages=files['packages'],board_layouts=files['layouts'],
        stable_files=host['stable_files'],source_contract_sha256=host['source_contract_sha256'],
        evidence=refs,note='Prior snapshots/FAIL retained; file audit PASS portions reused without rerunning large hashes'))
    result=dict(schema_version=1,gate_id='G00.1',attempt_id='attempt_01',candidate_id='OP00-stable-T32',status='PASS',
        input_manifest_sha256=sha256(identity_path),environment_manifest_sha256=sha256(env_path),
        prerequisite_results=[str(p) for p in paths.values()],
        criteria=[dict(name=k,threshold=True,observed=v,passed=v) for k,v in checks.items()],
        metrics={},evidence_files=refs+[dict(path=str(env_path),sha256=sha256(env_path)),
                                      dict(path=str(identity_path),sha256=sha256(identity_path))],
        failure_reason=None,rollback_result=dict(status='PASS_G00.2',stable_preserved=True),
        next_action='OP01 same-board-RGB software reference and real causal SYS baseline',
        model_inference=False,achieved_level=None)
    write_json(output,result)
    state_path=BASE/'STATE.json';state=json.loads(state_path.read_text())
    state['steps']['OP00']['status']='PASS'
    state['results']['G00.1']=str(output)
    state['next_action']=result['next_action']
    state['board_mutation_scope']='Stable T32 restored; isolated decoder added; temporary network removed; boot/DTB/CMA/old runtime unchanged'
    write_json(state_path,state)
    index_path=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    index=json.loads(index_path.read_text(encoding='utf-8-sig'))
    index['latest_optimization_v1_identity_gate']=dict(status='PASS',gate_id='G00.1',
        result=str(output.relative_to(ROOT)),sha256=sha256(output),build_id=kernel['build_id'],model_inference=False)
    write_json(index_path,index)
print(json.dumps(dict(status='PASS',gate_id='G00.1',OP00='PASS',model_inference=False,result=str(output))))
