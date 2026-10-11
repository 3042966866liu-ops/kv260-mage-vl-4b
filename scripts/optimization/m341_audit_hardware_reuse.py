"""Revalidate unchanged stable numerical/header/RTL/artifact evidence by hash."""
import hashlib
import json
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DEPLOY=ROOT/'deployment/mage_vl4b'
REVISION=sys.argv[1] if len(sys.argv)>1 else '01'
if REVISION not in ('01','02'):raise ValueError('Known revision required')
RUN=DEPLOY/f'optimization_v1/runs/M341-stable-hardware-reuse-audit-{REVISION}'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4<<20),b''): h.update(block)
    return h.hexdigest()


def main():
    if RUN.exists():raise RuntimeError('Immutable audit exists')
    result=dict(status='FAIL_HARDWARE_REUSE_CLOSURE',hardware_changed=False,overlay_loaded=False,
                hardware_gate_run=False,performance_pass=False,checked=[],errors=[],build_id='0x4D395832')
    recovery={}
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        (ROOT/name).read_text(encoding='utf-8-sig');recovery[name]=sha(ROOT/name)
    result['recovery_sources']=recovery
    def verify(row,scope):
        path=ROOT/row['path'].replace('\\','/')
        observed=dict(path=path.relative_to(ROOT).as_posix(),scope=scope,exists=path.is_file(),expected_sha256=row['sha256'])
        if observed['exists']:
            observed.update(bytes=path.stat().st_size,sha256=sha(path))
            observed['match']=observed['sha256']==row['sha256'] and ('bytes' not in row or row['bytes']==observed['bytes'])
        else: observed['match']=False
        if not observed['match'] and REVISION=='02' and observed['path']=='m132_m120_fifo_backpressure_hls/hls/hls.log':
            recovered=DEPLOY/'optimization_v1/runs/M341-stable-hardware-reuse-audit-01/recovered_m132_hls.log'
            if recovered.is_file() and recovered.stat().st_size==row['bytes'] and sha(recovered)==row['sha256']:
                observed.update(original_file_match=False,match=True,recovered_exact_snapshot=recovered.relative_to(ROOT).as_posix(),
                                recovered_sha256=sha(recovered),historical_bytes=row['bytes'],reason='Later export_design appended1458 bytes; exact recorded prefix recovered, original unchanged')
        result['checked'].append(observed)
        if not observed['match']:result['errors'].append(observed['path']+' '+('missing' if not observed['exists'] else 'identity mismatch'))
    names=('M130_M120_NUMERICAL_CSIM_RESULT.json','M129_HEADER_DEPENDENCY_AUDIT_RESULT.json',
           'M134_M120_RTL_COSIM_GATE_RESULT.json','M134_M120_RTL_TIMEOUT_GATE_RESULT.json','M134_M120_M89X2_IMPLEMENTATION_GATE_RESULT.json')
    docs={name:json.loads((DEPLOY/name).read_text(encoding='utf-8')) for name in names}
    result['evidence_documents']={name:dict(sha256=sha(DEPLOY/name),status=docs[name]['status']) for name in names}
    for name,doc in docs.items():
        if not doc['status'].startswith('PASS'):result['errors'].append(name+' not PASS')
    csim=docs[names[0]];headers=docs[names[1]];rtl=docs[names[2]];timeout=docs[names[3]];impl=docs[names[4]]
    if headers.get('missing')!=[] or csim['header_closure']['missing_count']!=0:result['errors'].append('Header missing!=0')
    for row in headers['files']:verify(row,'recursive_header_closure')
    for row in csim['sources']:verify(row,'numerical_csim_source')
    for key in ('fixture_result','csim_log','hls_log','header_closure'):verify(csim[key],'numerical_csim_evidence')
    for row in rtl['evidence']:verify(row,'rtl_positive_evidence')
    for path,row in timeout['evidence'].items():verify(dict(path=path,**row),'rtl_timeout_negative_evidence')
    required=dict(maximum_descriptor_count=10,maximum_fifo_pairs_per_shard=8192,random_axi_stall_backpressure=True,
        only_final_tlast=True,ap_done_completion=True,return_build_id='0x4D395832',bounded_timeout_expected_failure=True,recursive_header_closure_missing=0)
    if any(rtl['coverage'].get(k)!=v for k,v in required.items()):result['errors'].append('RTL required coverage missing')
    artifact=DEPLOY/'m120_m89x2_board_candidate/ARTIFACT_MANIFEST.json'
    if sha(artifact)!=impl['artifact_manifest_sha256']:result['errors'].append('Artifact manifest drift')
    for row in json.loads(artifact.read_text(encoding='utf-8')):
        verify(dict(row,path='deployment/mage_vl4b/m120_m89x2_board_candidate/'+row['path']),'stable_full_shell_artifact')
    stable=DEPLOY/'m175_m120_fixed_text_candidate'
    source=json.loads((stable/'SOURCE_MANIFEST.json').read_text(encoding='utf-8'))
    for row in source['files']:
        if row['path'].startswith('overlay/'):
            verify(dict(row,path='deployment/mage_vl4b/m175_m120_fixed_text_candidate/'+row['path']),'installed_stable_overlay')
    if not result['errors']:result['status']='PASS_UNCHANGED_STABLE_HARDWARE_EVIDENCE_REVALIDATED'
    result['next_step']='Only PASS permits packaging Build-ID-only hardware gate; missing evidence must be recovered exactly, no gate bypass or fresh shell synthesis'
    RUN.mkdir(parents=True)
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        (RUN/(Path(name).name+'.before')).write_bytes((ROOT/name).read_bytes())
    path=RUN/'RESULT.json';data=(json.dumps(result,indent=2)+'\n').encode();part=path.with_suffix('.part');part.write_bytes(data);os.replace(part,path)
    print(json.dumps(dict(status=result['status'],checked=len(result['checked']),errors=result['errors'],evidence=str(path))))


if __name__=='__main__':main()
