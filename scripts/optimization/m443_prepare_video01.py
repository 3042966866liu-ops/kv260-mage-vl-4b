"""Freeze one original M437-policy video request after actual M443 fixed-text PASS."""
import ast
import json
import sys
from pathlib import Path
import m351_workflow as w
from m441_host_io08 import atomic
from m443_prepare_layer01 import once
from m443_transfer import verify_directory

OLD=w.BASE/'candidates/M441-fixed-video-09'
LOWER=w.BASE/'candidates/M443-fixed-text-01'
PKG=w.BASE/'candidates/M443-fixed-video-01'
RUN=w.BASE/'runs/M443-fixed-video-preparation-01'
TEXT=w.BASE/'runs/M443-fixed-text-board-01/BOARD_RESULT.json'
OLD_TEXT_SHA='0562c15fd56f185a98f2ee8c169ab4bd2939abfb0ec482ec7126fbd5bf53abc7'
OLD_CHAIN_SHA='0b416a17669ae1a5690a62650237ce6ced33f922017625f685401ca806e2273d'


def main():
    assert not PKG.exists() and not RUN.exists(),'Fresh immutable preparation required'
    r=json.loads(TEXT.read_bytes());text_sha=w.sha(TEXT)
    assert r['status']=='PASS_M443T_FIXED_TEXT_DIAGNOSTIC' and r['gate_return_code']==0 and r['numerical_pass']
    assert all(r['exact_comparison'].values()) and r['safe_buffers_released'] and not r['unsafe_buffers_retained'] and not r['errors']
    assert r['configuration_application_accepted'] and not r['unknown_configuration_ownership']
    assert all(text_sha in (w.ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
    for directory in (OLD,LOWER):verify_directory(directory,w.sha(directory/'PACKAGE_MANIFEST.json'))
    prep=json.loads((w.BASE/'runs/M443-fixed-text-preparation-01/RESULT.json').read_bytes())
    gate=(OLD/'m441_video_gate.py').read_text(encoding='utf-8')
    gate=gate.replace('m441_video_','m443_video_').replace('M441V','M443V').replace('/home/ubuntu/m441_fixed_video_evidence_09','/home/ubuntu/m443_fixed_video_evidence_01')
    gate=once(gate,"Path('/home/ubuntu/m441_candidate_01')","Path('/home/ubuntu/m443_candidate_01')")
    gate=once(gate,"CAND_SHA = '56253626a550c9c1358e805e6e3ad9b8b03c2fd9c1ff048be87c64c9f04dd5a0'","CAND_SHA = '"+prep['candidate_manifest_sha256']+"'")
    gate=once(gate,"PRIOR_SHA = '"+OLD_CHAIN_SHA+"'","PRIOR_SHA = '"+prep['prior_raw_sha256']+"'\nBUILD_PROOF_SHA = '"+prep['configuration_build_raw_sha256']+"'")
    gate=gate.replace("'0x4D343431' if is_candidate","'0x4D343433' if is_candidate").replace(OLD_TEXT_SHA,text_sha).replace('PASS_M441T_FIXED_TEXT_DIAGNOSTIC','PASS_M443T_FIXED_TEXT_DIAGNOSTIC').replace('Actual M441 text prerequisite differs','Actual M443 text prerequisite differs')
    gate=gate.replace('M441_COMPARE_PREREQUISITE.json','M443_CHAIN_PREREQUISITE.json')
    gate=once(gate,"prerequisite['status'] != 'PASS_M441_COMPARE' or not prerequisite['chain_performance_pass']","prerequisite['status'] != 'PASS_M443_CHAIN' or prerequisite['gate_return_code'] != 0")
    gate=gate.replace('Exact M441 balanced single-chain prerequisite differs','Exact M443 complete real chain prerequisite differs')
    lower_gate=(LOWER/'m443_text_gate.py').read_text(encoding='utf-8')
    a=lower_gate.index("        result['prior_board_sha256'] = PRIOR_SHA");b=lower_gate.index('        if os.geteuid() != 0:',a)
    gate=once(gate,"        result['prior_board_sha256'] = PRIOR_SHA\n",lower_gate[a:b])
    gate=once(gate,'    initialized = unsafe = False','    initialized = unsafe = False\n    configuration = None')
    a=lower_gate.index('        from m443_layer_configuration01 import LayerConfiguration');b=lower_gate.index('        board_cls = ',a)
    gate=once(gate,"        patch(pynq,'Overlay',observe_call(pynq.Overlay,'pynq.Overlay',mark,result['io_events']))\n",lower_gate[a:b])
    gate=once(gate,'            index=len(allocations)','            configuration.require_allocation_eligibility()\n            index=len(allocations)')
    anchor='        # Keep guards installed until all resource cleanup is finished.'
    gate=once(gate,anchor,'        unsafe = unsafe or (configuration is not None and configuration.retain_required)\n'+anchor)
    exclude={'PACKAGE_MANIFEST.json','SHA256SUMS','M441_COMPARE_PREREQUISITE.json','STAGE_PREREQUISITE.json','HARDWARE_CLOSURE.json','m441_video_gate.py','m441_video_entry.py','m441_video_export.py','m441_video_assemble.py','run_m441_video.sh'}
    files={p.name:p.read_bytes() for p in OLD.iterdir() if p.name not in exclude}
    files['m443_video_gate.py']=gate.encode('utf-8')
    for old,new in [('m441_video_entry.py','m443_video_entry.py'),('m441_video_export.py','m443_video_export.py'),('run_m441_video.sh','run_m443_video.sh')]:
        files[new]=(OLD/old).read_text(encoding='utf-8').replace('M441V','M443V').replace('m441_video_','m443_video_').replace('/home/ubuntu/m441_fixed_video_evidence_09','/home/ubuntu/m443_fixed_video_evidence_01').encode('utf-8')
    for name in ('CONFIGURATION_APPLICATION.json','m443_configuration01.py','m443_cma_contract01.py','m443_cma_trace01.py','m443_layer_configuration01.py','HARDWARE_CLOSURE.json','M443_CHAIN_PREREQUISITE.json','M443_BUILD_CONFIGURATION_PROOF.json'):
        files[name]=(LOWER/name).read_bytes()
    files['STAGE_PREREQUISITE.json']=TEXT.read_bytes()
    assembler=(LOWER/'m443_text_assemble.py').read_text(encoding='utf-8')
    a=assembler.index('SOURCES=');b=assembler.index("if __name__=='__main__':",a)
    sources=[('/home/ubuntu/m441_fixed_video_candidate_09',w.sha(OLD/'PACKAGE_MANIFEST.json')),('/home/ubuntu/m443_fixed_text_candidate_01',w.sha(LOWER/'PACKAGE_MANIFEST.json')),('/home/ubuntu/m443_candidate_01',prep['candidate_manifest_sha256'])]
    proofs=[('/home/ubuntu/m443_fixed_text_evidence_01/B1/load-memory.json',text_sha),('/home/ubuntu/m443_board_evidence_01/BuildID/BOARD_RESULT.json',prep['configuration_build_raw_sha256']),('/home/ubuntu/m443_board_evidence_01/Chain/BOARD_RESULT.json',prep['prior_raw_sha256'])]
    assembler=assembler[:a]+'SOURCES='+repr(sources)+'\nPROOFS='+repr(proofs)+'\n'+assembler[b:]
    files['m443_video_assemble.py']=assembler.replace('M443T','M443V').encode('utf-8')
    for name in ('m432_trials.py','m432_request_visual.py','m431_borrowed_visual.py','m369_light_policy.py','PLAN.json','VIDEO_EXPECTED.json','VISUAL_EXPECTED.json'):
        assert files[name]==(OLD/name).read_bytes(),'Original visual/math/policy changed'
    assert gate.index('head_AST_checked_before_overlay')<gate.index("patch(pynq,'Overlay'")<gate.index('engine.load()')
    # Recursive Python dependencies resolve only from the exact pinned reused manifests.
    plan=json.loads(files['PLAN.json']);roots=[w.BASE/'candidates/M368-staged-video-03']
    for row in plan['visual_reused_packages']:
        matches=[p.parent for p in (w.BASE/'candidates').glob('*/PACKAGE_MANIFEST.json') if w.sha(p)==row['manifest_sha256']]
        assert len(matches)==1,'Pinned reused visual manifest absent/ambiguous';roots+=matches
    for root in roots:verify_directory(root,w.sha(root/'PACKAGE_MANIFEST.json'))
    closure=json.loads(files['SOURCE_CLOSURE.json']);release=w.ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    for row in closure['files']:assert w.sha(release/row['path'])==row['sha256']
    trees={Path(n).stem:ast.parse(raw,feature_version=(3,10)) for n,raw in files.items() if n.endswith('.py')}
    allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','torch','pynq','tokenizers','fcntl'}
    for root in roots:allowed|={p.stem for p in root.glob('*.py')}
    missing=[]
    for module,tree in trees.items():
        for node in ast.walk(tree):
            refs=[x.name.split('.')[0] for x in node.names] if isinstance(node,ast.Import) else [(node.module or '').split('.')[0]] if isinstance(node,ast.ImportFrom) else []
            missing.extend((module,ref) for ref in refs if ref and ref not in trees and ref not in allowed)
    assert not missing,missing
    PKG.mkdir(parents=True)
    for name,raw in files.items():atomic(PKG/name,raw,immutable=True)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(x['sha256']+'  '+x['path']+'\n' for x in rows).encode('ascii'),immutable=True)
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=w.sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='m443-independent-fixed-video-v01',files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))),immutable=True)
    digest=w.sha(PKG/'PACKAGE_MANIFEST.json');verify_directory(PKG,digest)
    # Keep the entire original strict accepted-reference checker; add actual new-bit proof.
    collector=(w.HERE/'m441_video_collect09.py').read_text(encoding='utf-8')
    collector=collector.replace('M441-fixed-video-09','M443-fixed-video-01').replace('M441-fixed-video-board-09','M443-fixed-video-board-01').replace('M441V','M443V').replace('0x4D343431','0x4D343433').replace('0x4d343431','0x4d343433').replace(OLD_TEXT_SHA,text_sha).replace(OLD_CHAIN_SHA,prep['prior_raw_sha256']).replace('latest_m441_fixed_video_board','latest_m443_fixed_video_board01').replace('Actual M441 prerequisite','Actual M443 prerequisite').replace('## M441 固定159视频数值闭合09（2026-10-09）','## M443 固定159视频数值闭合01（2026-10-11）')
    extra="""        from m443_configuration01 import validate_record
        prep=json.loads((BASE/'runs/M443-fixed-video-preparation-01/RESULT.json').read_bytes())
        if r.get('configuration_application_build_raw_sha256')!=prep['configuration_build_raw_sha256'] or r.get('configuration_application_accepted') is not True or r.get('unknown_configuration_ownership') is not False or r.get('additional_cma_requests_allowed') is not False:raise ValueError('Actual new-bit configuration incomplete/unknown')
        application_sha=sha(PKG/'CONFIGURATION_APPLICATION.json')
        validate_record(r['configuration_record'],application_sha,prep['candidate_manifest_sha256'])
        for name,key,status in (('M443_BUILD_CONFIGURATION_PROOF.json','configuration_build_raw_sha256','PASS_M443_BUILDID'),('M443_CHAIN_PREREQUISITE.json','prior_raw_sha256','PASS_M443_CHAIN'),('STAGE_PREREQUISITE.json','prior_text_raw_sha256','PASS_M443T_FIXED_TEXT_DIAGNOSTIC')):
            p=PKG/name;proof=json.loads(p.read_bytes())
            if sha(p)!=prep[key] or proof['status']!=status or proof['gate_return_code']!=0:raise ValueError('Frozen actual prerequisite differs')
            validate_record(proof['configuration_record'],application_sha,prep['candidate_manifest_sha256'])
"""
    collector=once(collector,"        if r.get('vision_forward_calls')!=1",extra+"        if r.get('vision_forward_calls')!=1")
    collector=collector.replace('    atomic(OUT,raw,immutable=True)','    import m351_workflow as w\n    from m441_host_io08 import atomic as saved_atomic\n    w.atomic=saved_atomic\n    atomic=saved_atomic\n    atomic(OUT,raw,immutable=True)')
    atomic(w.HERE/'m443_video_collect01.py',collector.encode('utf-8'),immutable=True)
    control=(w.HERE/'m443_text_control01.ps1').read_text(encoding='utf-8').replace('M443-fixed-text','M443-fixed-video').replace('M443_FIXED_TEXT','M443_FIXED_VIDEO').replace('m443_text','m443_video').replace('m443_fixed_text','m443_fixed_video').replace('M443T','M443V').replace('M441-fixed-text-09','M441-fixed-video-09')
    control=control.replace("'candidates/M443-single-layer-01/PACKAGE_MANIFEST.json'","'candidates/M443-fixed-text-01/PACKAGE_MANIFEST.json'").replace("'runs/M443-single-layer-board-01/BOARD_RESULT.json'","'runs/M443-fixed-text-board-01/BOARD_RESULT.json'")
    control=control.replace('-TimeoutSeconds 900 -MarkerPrefix','-TimeoutSeconds 1500 -MarkerPrefix').replace('M443V_ENABLE_STAGED_LAYER=1','M443V_ENABLE_INTEGRATED_VIDEO=1').replace('$taskSHA $Mode B1','$taskSHA $Mode')
    atomic(w.HERE/'m443_video_control01.ps1',control.encode('utf-8'),immutable=True)
    result=dict(status='PREPARED_M443_FIXED159_AFTER_ACTUAL_TEXT01',manifest_sha256=digest,build_id='0x4D343433',prior_text_raw_sha256=text_sha,prior_raw_sha256=prep['prior_raw_sha256'],configuration_build_raw_sha256=prep['configuration_build_raw_sha256'],candidate_manifest_sha256=prep['candidate_manifest_sha256'],recursive_import_missing=missing,
                reused_manifests=[dict(path=root.relative_to(w.ROOT).as_posix(),sha256=w.sha(root/'PACKAGE_MANIFEST.json')) for root in roots],
                original_borrowed_visual_math_policy_unchanged=True,selected_layers=list(range(13,24)),language_logical=778,language_physical=781,visual_physical=286,total_with_minimal=1068,
                original_ps_growth_limit_bytes=1024<<20,original_ps_available_margin_bytes=64<<20,additional_cma_requests_allowed=False,configuration_credits_granted=0,
                files=[dict(path=p.relative_to(w.ROOT).as_posix(),sha256=w.sha(p)) for p in sorted(PKG.iterdir())],board_executed=False,performance_pass=False,promoted=False)
    atomic(RUN/'RESULT.json',w.encoded(result),immutable=True);s=w.sha(RUN/'RESULT.json');w.atomic=atomic
    w.sync('latest_m443_fixed_video_preparation01',dict(status=result['status'],result=(RUN/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=s,manifest_sha256=digest),
           '## M443固定159视频准备01（2026-10-11）\n\nSHA '+s+'；实际新核完整文本原raw '+text_sha+'闭合后，独立同PID配置合同接入原M441/M437后11层视觉及原完整语言/head参考。原七DMA借用/PS1GiB诊断预算及64MiB普通余量/累计计数不改；递归仅精确复用manifest missing=0。准备非新板数值或性能；下一步完整原collector负例/实际exporter/配置保留组件检查和冻结后逐SHA上传。')
    print(result['status'],s,digest,len(rows))


if __name__=='__main__':main()
