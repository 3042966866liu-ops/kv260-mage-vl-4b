"""Prepare the original balanced full-request experiment after actual M443 video PASS."""
import ast
import hashlib
import json
import sys
from pathlib import Path
import m351_workflow as w
from m441_host_io08 import atomic
from m443_prepare_layer01 import once
from m443_transfer import verify_directory

OLD=w.BASE/'candidates/M441-complete-request-performance-17'
LOWER=w.BASE/'candidates/M443-fixed-video-01'
PKG=w.BASE/'candidates/M443-complete-request-performance-01'
RUN=w.BASE/'runs/M443-complete-request-performance-preparation-01'
VIDEO=w.BASE/'runs/M443-fixed-video-board-01/BOARD_RESULT.json'
A_MANIFEST='56253626a550c9c1358e805e6e3ad9b8b03c2fd9c1ff048be87c64c9f04dd5a0'
OLD_CHAIN='0b416a17669ae1a5690a62650237ce6ced33f922017625f685401ca806e2273d'
OLD_TEXT='0562c15fd56f185a98f2ee8c169ab4bd2939abfb0ec482ec7126fbd5bf53abc7'


def builds(source):
    return source.replace('0x4D333537','__A_BUILD_UPPER__').replace('0x4d333537','__A_BUILD_LOWER__').replace('0x4D343431','0x4D343433').replace('0x4d343431','0x4d343433').replace('__A_BUILD_UPPER__','0x4D343431').replace('__A_BUILD_LOWER__','0x4d343431')


def main():
    assert not PKG.exists() and not RUN.exists(),'Fresh immutable preparation only'
    vr=json.loads(VIDEO.read_bytes());video_sha=w.sha(VIDEO)
    assert vr['status']=='PASS_M443V_INTEGRATED_VIDEO_NUMERICAL' and vr['gate_return_code']==0 and vr['numerical_pass']
    assert vr['safe_buffers_released'] and not vr['unsafe_buffers_retained'] and not vr['errors']
    assert vr['configuration_application_accepted'] and not vr['unknown_configuration_ownership']
    assert all(video_sha in (w.ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
    for directory in (OLD,LOWER):verify_directory(directory,w.sha(directory/'PACKAGE_MANIFEST.json'))
    prep=json.loads((w.BASE/'runs/M443-fixed-video-preparation-01/RESULT.json').read_bytes())
    ledger_support=w.BASE/'runs/M443-performance-ledger-support-01/RESULT.json'
    for row in json.loads(ledger_support.read_bytes())['files']:assert w.sha(w.ROOT/row['path'])==row['sha256']
    gate=(OLD/'m441_performance_gate.py').read_text(encoding='utf-8')
    gate=builds(gate).replace('M441P','M443P').replace('m441_performance_', 'm443_performance_').replace('m441_kernel_switch15','m443_kernel_switch01').replace('/home/ubuntu/m441_complete_request_evidence_17','/home/ubuntu/m443_complete_request_evidence_01')
    gate=once(gate,"Path('/home/ubuntu/m441_candidate_01')","Path('/home/ubuntu/m443_candidate_01')")
    gate=once(gate,"CAND_SHA = '"+A_MANIFEST+"'","CAND_SHA = '"+prep['candidate_manifest_sha256']+"'")
    gate=gate.replace('m441_cma_ledger15 import StagePolicy,prerequisite as verify_configuration_cma15','m443_performance_ledger01 import StagePolicy,prerequisite as verify_configuration_cma01')
    gate=once(gate,"result['CMA14_prerequisite']=verify_configuration_cma15(HERE)","result['M443_configuration_prerequisite']=verify_configuration_cma01(HERE,CAND_SHA)\n        result['configuration_application_build_raw_sha256']=result['M443_configuration_prerequisite']['sha256']\n        for driver_row in json.loads((HERE/'SOURCE_IDENTITIES.json').read_bytes()):\n            if sha256(Path(driver_row['path']))!=driver_row['sha256']:raise RuntimeError('Original configuration driver source drift')\n        result['configuration_driver_sources_checked_before_overlay']=True")
    gate=once(gate,"PRIOR_SHA = '"+OLD_CHAIN+"'","PRIOR_SHA = '"+prep['prior_raw_sha256']+"'")
    gate=gate.replace('M441_VIDEO_PREREQUISITE.json','M443_VIDEO_PREREQUISITE.json').replace('PASS_M441V_INTEGRATED_VIDEO_NUMERICAL','PASS_M443V_INTEGRATED_VIDEO_NUMERICAL').replace('m441_video_sha256','m443_video_sha256').replace('m441_video_numerical_source_sha256','m443_video_numerical_source_sha256').replace('Actual M441 full video prerequisite differs','Actual M443 full video prerequisite differs')
    gate=gate.replace(OLD_TEXT,prep['prior_text_raw_sha256']).replace('PASS_M441T_FIXED_TEXT_DIAGNOSTIC','PASS_M443T_FIXED_TEXT_DIAGNOSTIC')
    gate=gate.replace('M441_COMPARE_PREREQUISITE.json','M443_CHAIN_PREREQUISITE.json')
    gate=once(gate,"prerequisite['status'] != 'PASS_M441_COMPARE' or not prerequisite['chain_performance_pass'] or not prerequisite['stable_restored']","prerequisite['status'] != 'PASS_M443_CHAIN' or prerequisite['gate_return_code'] != 0 or not prerequisite['stable_restored']")
    gate=once(gate,'    initialized = unsafe = False','    initialized = unsafe = False\n    configuration = None')
    gate=once(gate,"policy=StagePolicy(result,lambda:runtime,base,evidence=EVIDENCE)","result['source_compatibility_checked_before_overlay']=True\n        policy=StagePolicy(result,lambda:runtime,base,evidence=EVIDENCE,application_sha=sha256(HERE/'CONFIGURATION_APPLICATION.json'),manifest_sha=CAND_SHA)")
    gate=once(gate,'            index=len(allocations)','            configuration.require_allocation_eligibility()\n            index=len(allocations)')
    gate=once(gate,"        patch(pynq,'Overlay',observe_call(policy.wrap_overlay(pynq.Overlay),'pynq.Overlay',mark,result['io_events']))", """        from m443_layer_configuration01 import LayerConfiguration
        configuration=LayerConfiguration(result,TARGET,TARGET_SHA,HERE/'CONFIGURATION_APPLICATION.json',EVIDENCE)
        original_overlay=pynq.Overlay
        resident_overlay=policy.wrap_overlay(original_overlay)
        def configuration_overlay(bit,*a,**kw):
            if not policy.sealed:return configuration.load(bit,original_overlay,*a,**kw)
            return resident_overlay(bit,*a,**kw)
        patch(pynq,'Overlay',observe_call(configuration_overlay,'pynq.Overlay',mark,result['io_events']))"""
    )
    gate=gate.replace("Path('/home/ubuntu/m357_candidate_01') if variant=='A'","Path('/home/ubuntu/m441_candidate_01') if variant=='A'").replace("'2e9cbd00d0d01edf05e171674f71f86a94ce389a0658ce6c5466cebb77220d18' if variant=='A'","'"+A_MANIFEST+"' if variant=='A'")
    gate=once(gate,'        # Keep guards installed until all resource cleanup is finished.','        unsafe = unsafe or (configuration is not None and configuration.retain_required)\n        # Keep guards installed until all resource cleanup is finished.')
    excluded={'PACKAGE_MANIFEST.json','SHA256SUMS','CMA_PREREQUISITE.json','m441_performance_gate.py','m441_performance_entry.py','m441_performance_export.py','m441_performance_assemble.py','m441_performance_trials.py','m441_kernel_switch15.py','run_m441_performance.sh','M441_VIDEO_PREREQUISITE.json','M441_COMPARE_PREREQUISITE.json','STAGE_PREREQUISITE.json','HARDWARE_CLOSURE.json','PERFORMANCE_PLAN.json'}
    files={p.name:p.read_bytes() for p in OLD.iterdir() if p.name not in excluded}
    files['m443_performance_gate.py']=gate.encode('utf-8')
    for old,new in (('m441_performance_entry.py','m443_performance_entry.py'),('m441_performance_export.py','m443_performance_export.py'),('run_m441_performance.sh','run_m443_performance.sh')):
        files[new]=(OLD/old).read_text(encoding='utf-8').replace('M441P','M443P').replace('m441_performance_','m443_performance_').replace('/home/ubuntu/m441_complete_request_evidence_17','/home/ubuntu/m443_complete_request_evidence_01').encode('utf-8')
    files['m443_performance_trials.py']=builds((OLD/'m441_performance_trials.py').read_text(encoding='utf-8')).replace('M441P','M443P').encode('utf-8')
    switch=builds((OLD/'m441_kernel_switch15.py').read_text(encoding='utf-8'))
    switch=once(switch,'overlay=self.load_overlay(path)','overlay=self.load_overlay(path,download=True)')
    files['m443_kernel_switch01.py']=switch.encode('utf-8')
    for name in ('m443_performance_ledger01.py','m443_performance_trace01.py'):files[name]=(w.HERE/name).read_bytes()
    for name in ('CONFIGURATION_APPLICATION.json','m443_configuration01.py','m443_cma_contract01.py','m443_cma_trace01.py','m443_layer_configuration01.py','HARDWARE_CLOSURE.json','M443_CHAIN_PREREQUISITE.json','M443_BUILD_CONFIGURATION_PROOF.json','STAGE_PREREQUISITE.json'):files[name]=(LOWER/name).read_bytes()
    files['M443_VIDEO_PREREQUISITE.json']=VIDEO.read_bytes()
    perf=json.loads((OLD/'PERFORMANCE_PLAN.json').read_bytes());perf['m443_video_sha256']=video_sha;del perf['m441_video_sha256'];files['PERFORMANCE_PLAN.json']=w.encoded(perf)
    assembler=(LOWER/'m443_video_assemble.py').read_text(encoding='utf-8');a=assembler.index('SOURCES=');b=assembler.index("if __name__=='__main__':",a)
    sources=[('/home/ubuntu/m441_complete_request_candidate_17',w.sha(OLD/'PACKAGE_MANIFEST.json')),('/home/ubuntu/m443_fixed_video_candidate_01',w.sha(LOWER/'PACKAGE_MANIFEST.json'))]
    proofs=[('/home/ubuntu/m443_fixed_video_evidence_01/BOARD_RESULT.json',video_sha)]
    files['m443_performance_assemble.py']=(assembler[:a]+'SOURCES='+repr(sources)+'\nPROOFS='+repr(proofs)+'\n'+assembler[b:]).replace('M443V','M443P').encode('utf-8')
    for name in ('m433_timed_visual.py','m437_sequence.py','WARM_PROTOCOL.json','PLAN.json','m441_cma_ledger15.py','m441_cma_trace15.py'):
        assert files[name]==(OLD/name).read_bytes(),'Original mathematical/protocol/CMA whitelist bytes changed'
    assert gate.index('head_AST_checked_before_overlay')<gate.index("patch(pynq,'Overlay'")<gate.index('engine.load()')
    closure=json.loads(files['SOURCE_CLOSURE.json']);release=w.ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    for row in closure['files']:assert w.sha(release/row['path'])==row['sha256']
    roots=[w.ROOT/row['path'] for row in prep['reused_manifests']]
    for root in roots:verify_directory(root,w.sha(root/'PACKAGE_MANIFEST.json'))
    trees={Path(n).stem:ast.parse(raw,feature_version=(3,10)) for n,raw in files.items() if n.endswith('.py')}
    allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','torch','pynq','tokenizers','fcntl'}
    for root in roots:allowed|={p.stem for p in root.glob('*.py')}
    missing=[]
    for module,tree in trees.items():
        for node in ast.walk(tree):
            refs=[x.name.split('.')[0] for x in node.names] if isinstance(node,ast.Import) else [(node.module or '').split('.')[0]] if isinstance(node,ast.ImportFrom) else []
            missing.extend((module,x) for x in refs if x and x not in trees and x not in allowed)
    assert not missing,missing
    rows=[dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()) for name,raw in sorted(files.items())]
    files['SHA256SUMS']=''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii')
    rows.append(dict(path='SHA256SUMS',bytes=len(files['SHA256SUMS']),sha256=hashlib.sha256(files['SHA256SUMS']).hexdigest()))
    files['PACKAGE_MANIFEST.json']=w.encoded(dict(schema='m443-independent-original-request-performance01',files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows)))
    digest=hashlib.sha256(files['PACKAGE_MANIFEST.json']).hexdigest()
    collector=builds((w.HERE/'m441_performance_collect17.py').read_text(encoding='utf-8')).replace('M441-complete-request-performance-17','M443-complete-request-performance-01').replace('M441-complete-request-performance-board-17','M443-complete-request-performance-board-01').replace('M441P','M443P').replace('latest_m441_complete_request_board','latest_m443_complete_request_board01').replace('m441_video_sha256','m443_video_sha256').replace('m441_video_numerical_source_sha256','m443_video_numerical_source_sha256')
    collector=once(collector,'from m441_cma_ledger15 import validate as validate_configuration',"from m443_performance_ledger01 import validate as validate_configuration01\nfrom m443_configuration01 import validate_record\nAPPLICATION_SHA=sha(PKG/'CONFIGURATION_APPLICATION.json')\nCANDIDATE_SHA='"+prep['candidate_manifest_sha256']+"'\ndef validate_configuration(record):return validate_configuration01(record,APPLICATION_SHA,CANDIDATE_SHA)")
    collector=once(collector,"    assert r['CMA14_prerequisite']['sha256']=='c31df037d60466230dbe58148ef7e663a0da76059a9e784364791ef058ac38b4'","    assert r['M443_configuration_prerequisite']['sha256']=='"+prep['configuration_build_raw_sha256']+"'\n    assert r['M443_configuration_prerequisite']['application_sha256']==APPLICATION_SHA and r['M443_configuration_prerequisite']['manifest_sha256']==CANDIDATE_SHA\n    assert r['M443_configuration_prerequisite']['actual_new_bit_application'] is True and r['M443_configuration_prerequisite']['configuration_credits_granted']==0")
    collector=once(collector,"'8bac3588a5d8f008a651fe25d35e0a11a32ef6615c5675add25b60e2a2e9711f' if variant=='A' else '73350f615a5bc98d1d8aa2b5c69c4d6fd399aa1ef651f37411cbed21c0daed2e'","'73350f615a5bc98d1d8aa2b5c69c4d6fd399aa1ef651f37411cbed21c0daed2e' if variant=='A' else '555ae52842ae901c863152a5a02b2dd4583ed95691255d98889a25ae579c27ae'")
    collector=once(collector,"'2e9cbd00d0d01edf05e171674f71f86a94ce389a0658ce6c5466cebb77220d18' if variant=='A' else '"+A_MANIFEST+"'","'"+A_MANIFEST+"' if variant=='A' else '"+prep['candidate_manifest_sha256']+"'")
    collector=once(collector,'        verify_ledger(r)',"""        verify_ledger(r)
        if r.get('configuration_application_accepted') is not True or r.get('unknown_configuration_ownership') is not False or r.get('source_compatibility_checked_before_overlay') is not True or r.get('configuration_driver_sources_checked_before_overlay') is not True:raise ValueError('Initial actual configuration admission differs')
        if r.get('configuration_application_build_raw_sha256')!=r['M443_configuration_prerequisite']['sha256']:raise ValueError('Configuration origin differs')
        validate_record(r['configuration_record'],APPLICATION_SHA,CANDIDATE_SHA)
        if any(x['pid']!=r['configuration_record']['pid'] for x in r['configuration_CMA_ledger']):raise ValueError('Resident switch trace must share initial process identity')
        for name,status in (('M443_BUILD_CONFIGURATION_PROOF.json','PASS_M443_BUILDID'),('M443_CHAIN_PREREQUISITE.json','PASS_M443_CHAIN'),('M443_VIDEO_PREREQUISITE.json','PASS_M443V_INTEGRATED_VIDEO_NUMERICAL')):
            proof=json.loads((PKG/name).read_bytes())
            if proof['status']!=status or proof['gate_return_code']!=0:raise ValueError('Original actual prerequisite differs')
            validate_record(proof['configuration_record'],APPLICATION_SHA,CANDIDATE_SHA)"""
    )
    collector=once(collector,'    atomic(OUT,raw,immutable=True)','    import m351_workflow as w\n    from m441_host_io08 import atomic as saved_atomic\n    w.atomic=saved_atomic\n    atomic=saved_atomic\n    atomic(OUT,raw,immutable=True)')
    collector=collector.replace('同视觉A原M357/B新M441','同视觉A原M441/B新M443').replace('## M441 同视觉完整请求测量回收17（2026-10-09）','## M443 同视觉完整请求測量回收01（2026-10-11）')
    control=(w.HERE/'m443_video_control01.ps1').read_text(encoding='utf-8').replace('M443-fixed-video','M443-complete-request-performance').replace('M443_FIXED_VIDEO','M443_PERFORMANCE').replace('m443_video','m443_performance').replace('m443_fixed_video_candidate','m443_complete_request_candidate').replace('M443V','M443P').replace('tmp/m443_performance01','tmp/m443_performance01')
    control=control.replace("'candidates/M441-fixed-video-09/PACKAGE_MANIFEST.json'","'candidates/M441-complete-request-performance-17/PACKAGE_MANIFEST.json'").replace("'candidates/M443-fixed-text-01/PACKAGE_MANIFEST.json'","'candidates/M443-fixed-video-01/PACKAGE_MANIFEST.json'").replace("'runs/M443-fixed-text-board-01/BOARD_RESULT.json'","'runs/M443-fixed-video-board-01/BOARD_RESULT.json'")
    control=control.replace('PASS_M443_PERFORMANCE_SUPPORT_FIXTURES01','PASS_M443_PERFORMANCE_SUPPORT_FIXTURES01').replace('-TimeoutSeconds 1500 -MarkerPrefix','-TimeoutSeconds 5100 -MarkerPrefix')
    ast.parse(collector,feature_version=(3,10));ast.parse(gate,feature_version=(3,10))
    # All derivations and Python closure checks finish before any candidate bytes are frozen.
    PKG.mkdir(parents=True)
    for name,raw in files.items():atomic(PKG/name,raw,immutable=True)
    verify_directory(PKG,digest)
    atomic(w.HERE/'m443_performance_collect01.py',collector.encode('utf-8'),immutable=True)
    atomic(w.HERE/'m443_performance_control01.ps1',control.encode('utf-8'),immutable=True)
    result=dict(status='PREPARED_M443_ORIGINAL_FULL_REQUEST01',manifest_sha256=digest,prior_video_raw_sha256=video_sha,prior_text_raw_sha256=prep['prior_text_raw_sha256'],prior_raw_sha256=prep['prior_raw_sha256'],configuration_build_raw_sha256=prep['configuration_build_raw_sha256'],candidate_manifest_sha256=prep['candidate_manifest_sha256'],baseline_manifest_sha256=A_MANIFEST,recursive_import_missing=missing,ledger_support_sha256=w.sha(ledger_support),original_parser_and_math_and_protocol_unchanged=True,balanced_sequence='ABBAABBABAAB',request_physical=12804,total_physical_with_initial_and_eight_untimed_switches=12813,seven_original_owners=True,original_ps_growth_limit_bytes=1024<<20,original_ps_available_margin_bytes=64<<20,files=[dict(path=p.relative_to(w.ROOT).as_posix(),sha256=w.sha(p)) for p in sorted(PKG.iterdir())],board_executed=False,performance_pass=False,promoted=False)
    atomic(RUN/'RESULT.json',w.encoded(result),immutable=True);s=w.sha(RUN/'RESULT.json');w.atomic=atomic
    w.sync('latest_m443_complete_request_preparation01',dict(status=result['status'],result=(RUN/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=s,manifest_sha256=digest),'## M443原完整请求独立准备01（2026-10-11）\n\nSHA '+s+'；真实视频raw '+video_sha+' 后独立A=M441/B=M443，新配置合同和原baseline累计计数、七owner及8非计时切换门禁。原parser/math/视觉/protocol和自然I/O完整4+8保持，不叠加M442解析收益。准备非实际完整请求或性能裁决；下一步严格组件/全collector负例/冻结/逐SHA传输后唯一Run。')
    print(result['status'],s,digest,len(rows))


if __name__=='__main__':main()
