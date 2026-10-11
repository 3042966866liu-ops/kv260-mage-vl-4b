"""Prepare isolated original fixed-text gate only after the actual M443 layer PASS."""
import ast
import json
import sys
from pathlib import Path
import m351_workflow as w
from m441_host_io08 import atomic
from m443_prepare_layer01 import once
from m443_transfer import verify_directory

OLD=w.BASE/'candidates/M441-fixed-text-09'
LOWER=w.BASE/'candidates/M443-single-layer-01'
PKG=w.BASE/'candidates/M443-fixed-text-01'
RUN=w.BASE/'runs/M443-fixed-text-preparation-01'
LAYER=w.BASE/'runs/M443-single-layer-board-01/BOARD_RESULT.json'


def main():
    assert not PKG.exists() and not RUN.exists(),'Fresh immutable preparation required'
    r=json.loads(LAYER.read_bytes());layer_sha=w.sha(LAYER)
    assert r['status']=='PASS_M443L_SINGLE_LAYER_DIAGNOSTIC' and r['gate_return_code']==0 and r['numerical_pass']
    assert r['safe_buffers_released'] and not r['unsafe_buffers_retained'] and not r['errors'] and r['configuration_application_accepted']
    assert all(layer_sha in (w.ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
    for directory in (OLD,LOWER):verify_directory(directory,w.sha(directory/'PACKAGE_MANIFEST.json'))
    prep=json.loads((w.BASE/'runs/M443-single-layer-preparation-01/RESULT.json').read_bytes())
    old_text=(OLD/'m441_text_gate.py').read_text(encoding='utf-8')
    text=old_text.replace('m441_text_', 'm443_text_').replace('M441T','M443T').replace('_m441t_','_m443t_').replace('/home/ubuntu/m441_fixed_text_evidence_09','/home/ubuntu/m443_fixed_text_evidence_01')
    text=once(text,"Path('/home/ubuntu/m441_candidate_01')","Path('/home/ubuntu/m443_candidate_01')")
    text=once(text,"CAND_SHA = '56253626a550c9c1358e805e6e3ad9b8b03c2fd9c1ff048be87c64c9f04dd5a0'","CAND_SHA = '"+prep['candidate_manifest_sha256']+"'")
    text=once(text,"PRIOR_SHA = '0b416a17669ae1a5690a62650237ce6ced33f922017625f685401ca806e2273d'","PRIOR_SHA = '"+prep['prior_raw_sha256']+"'\nBUILD_PROOF_SHA = '"+prep['configuration_build_raw_sha256']+"'")
    text=text.replace("'0x4D343431' if is_candidate","'0x4D343433' if is_candidate")
    text=text.replace('16b7aeb84dad97dbfbbdff06311becff9cf7866261316cc18dc296a97f0132e4',layer_sha).replace('PASS_M441L_SINGLE_LAYER_DIAGNOSTIC','PASS_M443L_SINGLE_LAYER_DIAGNOSTIC').replace('Actual M441 single-layer prerequisite differs','Actual M443 single-layer prerequisite differs')
    text=text.replace('M441_COMPARE_PREREQUISITE.json','M443_CHAIN_PREREQUISITE.json')
    text=once(text,"prerequisite['status'] != 'PASS_M441_COMPARE' or not prerequisite['chain_performance_pass']","prerequisite['status'] != 'PASS_M443_CHAIN' or prerequisite['gate_return_code'] != 0")
    text=text.replace('Exact M441 balanced single-chain prerequisite differs','Exact M443 complete real chain prerequisite differs')
    lower_gate=(LOWER/'m443_layer_gate.py').read_text(encoding='utf-8')
    start=lower_gate.index("        result['prior_board_sha256'] = PRIOR_SHA")
    end=lower_gate.index("        if os.geteuid() != 0:",start)
    text=once(text,"        result['prior_board_sha256'] = PRIOR_SHA\n",lower_gate[start:end])
    text=once(text,'    initialized = unsafe = False','    initialized = unsafe = False\n    configuration = None')
    start=lower_gate.index('        from m443_layer_configuration01 import LayerConfiguration')
    end=lower_gate.index('        board_cls = ',start)
    text=once(text,"        patch(pynq,'Overlay',observe_call(pynq.Overlay,'pynq.Overlay',mark,result['io_events']))\n",lower_gate[start:end])
    text=once(text,'            index=len(allocations)','            configuration.require_allocation_eligibility()\n            index=len(allocations)')
    text=once(text,'        # Keep guards installed until all resource cleanup is finished.','        unsafe = unsafe or (configuration is not None and configuration.retain_required)\n        # Keep guards installed until all resource cleanup is finished.')
    exclude={'PACKAGE_MANIFEST.json','SHA256SUMS','M441_COMPARE_PREREQUISITE.json','STAGE_PREREQUISITE.json','HARDWARE_CLOSURE.json','m441_text_gate.py','m441_text_export.py','m441_text_assemble.py','run_m441_text.sh'}
    files={p.name:p.read_bytes() for p in OLD.iterdir() if p.name not in exclude}
    files['m443_text_gate.py']=text.encode('utf-8')
    for old,new in [('m441_text_export.py','m443_text_export.py'),('run_m441_text.sh','run_m443_text.sh')]:
        files[new]=(OLD/old).read_text(encoding='utf-8').replace('M441T','M443T').replace('m441_text_','m443_text_').replace('/home/ubuntu/m441_fixed_text_evidence_09','/home/ubuntu/m443_fixed_text_evidence_01').encode('utf-8')
    for name in ('CONFIGURATION_APPLICATION.json','m443_configuration01.py','m443_cma_contract01.py','m443_cma_trace01.py','m443_layer_configuration01.py','HARDWARE_CLOSURE.json','M443_CHAIN_PREREQUISITE.json','M443_BUILD_CONFIGURATION_PROOF.json'):
        files[name]=(LOWER/name).read_bytes()
    files['STAGE_PREREQUISITE.json']=LAYER.read_bytes()
    assembler=(LOWER/'m443_layer_assemble.py').read_text(encoding='utf-8')
    a=assembler.index('SOURCES=');b=assembler.index("if __name__=='__main__':",a)
    source=[('/home/ubuntu/m441_fixed_text_candidate_09',w.sha(OLD/'PACKAGE_MANIFEST.json')),('/home/ubuntu/m443_single_layer_candidate_01',w.sha(LOWER/'PACKAGE_MANIFEST.json')),('/home/ubuntu/m443_candidate_01',prep['candidate_manifest_sha256'])]
    proofs=[('/home/ubuntu/m443_single_layer_evidence_01/B1/load-memory.json',layer_sha),('/home/ubuntu/m443_board_evidence_01/BuildID/BOARD_RESULT.json',prep['configuration_build_raw_sha256']),('/home/ubuntu/m443_board_evidence_01/Chain/BOARD_RESULT.json',prep['prior_raw_sha256'])]
    assembler=assembler[:a]+'SOURCES='+repr(source)+'\nPROOFS='+repr(proofs)+'\n'+assembler[b:]
    files['m443_text_assemble.py']=assembler.replace('M443L','M443T').encode('utf-8')
    for name in ('m366_stage_policy.py','m366_head_observer.py','owned_buffer_release.py','LAYER_EXPECTED.json'):
        assert files[name]==(OLD/name).read_bytes()
    closure=json.loads(files['SOURCE_CLOSURE.json']);release=w.ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    for row in closure['files']:assert w.sha(release/row['path'])==row['sha256']
    # Head observation AST remains the exact proven transformation; original compute loop is unchanged.
    assert text.index('instrument_source(inspect.getsource(')<text.index("patch(pynq,'Overlay'")<text.index('engine.load()')
    trees={Path(n).stem:ast.parse(raw,feature_version=(3,10)) for n,raw in files.items() if n.endswith('.py')}
    allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers','fcntl'};missing=[]
    for module,tree in trees.items():
        for n in ast.walk(tree):
            names=[x.name.split('.')[0] for x in n.names] if isinstance(n,ast.Import) else [(n.module or '').split('.')[0]] if isinstance(n,ast.ImportFrom) else []
            missing.extend((module,name) for name in names if name and name not in trees and name not in allowed)
    assert not missing,missing
    PKG.mkdir(parents=True)
    for name,raw in files.items():atomic(PKG/name,raw,immutable=True)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(x['sha256']+'  '+x['path']+'\n' for x in rows).encode('ascii'),immutable=True)
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=w.sha(PKG/'SHA256SUMS')))
    manifest=dict(schema='m443-independent-fixed-text-v01',files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))
    atomic(PKG/'PACKAGE_MANIFEST.json',w.encoded(manifest),immutable=True);digest=w.sha(PKG/'PACKAGE_MANIFEST.json');verify_directory(PKG,digest)
    collector=(w.HERE/'m443_layer_collect01.py').read_text(encoding='utf-8').replace('M443-single-layer','M443-fixed-text').replace("'m365_collect.py'","'m36603_collect.py'").replace('M365-staged-layer-03','M366-staged-text-03').replace("replace('M365','M443L')","replace('M366','M443T')").replace('M443L_SINGLE_LAYER_DIAGNOSTIC','M443T_FIXED_TEXT_DIAGNOSTIC').replace('m443_single_layer','m443_fixed_text')
    collector=once(collector,"        application_sha = w.sha(PKG/'CONFIGURATION_APPLICATION.json')","        if r.get('prior_single_layer_raw_sha256') != prep['prior_single_layer_raw_sha256'] or r.get('head_AST_checked_before_overlay') is not True:\n            raise ValueError('Actual layer/head AST admission differs')\n        application_sha = w.sha(PKG/'CONFIGURATION_APPLICATION.json')")
    collector=collector.replace('单层','固定文本').replace('159重复embedding五family/hidden/KV/retry','原30token/36层/154family/151936logits/72KV/retry')
    atomic(w.HERE/'m443_text_collect01.py',collector.encode('utf-8'),immutable=True)
    control=(w.HERE/'m443_layer_control01.ps1').read_text(encoding='utf-8').replace('M443-single-layer','M443-fixed-text').replace('M443_SINGLE_LAYER','M443_FIXED_TEXT').replace('m443_layer','m443_text').replace('m443_single_layer','m443_fixed_text').replace('M443L','M443T').replace('M441-single-layer-09','M441-fixed-text-09')
    control=control.replace("'candidates/M441-fixed-text-09/PACKAGE_MANIFEST.json','candidates/M443-pair-pipeline-01/PACKAGE_MANIFEST.json'","'candidates/M441-fixed-text-09/PACKAGE_MANIFEST.json','candidates/M443-single-layer-01/PACKAGE_MANIFEST.json','candidates/M443-pair-pipeline-01/PACKAGE_MANIFEST.json'")
    control=control.replace("'runs/M443-chain-board-01/BOARD_RESULT.json'","'runs/M443-chain-board-01/BOARD_RESULT.json','runs/M443-single-layer-board-01/BOARD_RESULT.json'")
    atomic(w.HERE/'m443_text_control01.ps1',control.encode('utf-8'),immutable=True)
    support=(w.HERE/'m443_layer_support01.py').read_text(encoding='utf-8').replace('m443_layer_collect01','m443_text_collect01').replace('M443-single-layer','M443-fixed-text').replace('M443_SINGLE_LAYER','M443_FIXED_TEXT').replace('M443L','M443T').replace('M441-single-layer-board-09','M441-fixed-text-board-09').replace('PASS_M441L_SINGLE_LAYER_DIAGNOSTIC','PASS_M441T_FIXED_TEXT_DIAGNOSTIC').replace('PASS_M443L_SINGLE_LAYER_DIAGNOSTIC','PASS_M443T_FIXED_TEXT_DIAGNOSTIC')
    support=support.replace("control=w.HERE/'m443_layer_control01.ps1'","control=w.HERE/'m443_text_control01.ps1'").replace("w.HERE/'m443_layer_collect01.py'","w.HERE/'m443_text_collect01.py'").replace("w.HERE/'m365_collect.py'","w.HERE/'m36603_collect.py'").replace("logs=w.ROOT/'tmp/m443_layer01'","logs=w.ROOT/'tmp/m443_text01'")
    support=once(support,"    r['final_snapshot']['ap_return']=0x4d343433","    r['prior_single_layer_raw_sha256']=prep['prior_single_layer_raw_sha256']\n    r['head_AST_checked_before_overlay']=True\n    r['final_snapshot']['ap_return']=0x4d343433")
    support=support.replace("('source_compatibility_checked_before_overlay',False)","('source_compatibility_checked_before_overlay',False),('prior_single_layer_raw_sha256','0'*64),('head_AST_checked_before_overlay',False),('head_observer_proof',{'removed_observation_calls_ast_equals_original':False})")
    support=support.replace('PASS_M443T_SINGLE_LAYER_DIAGNOSTIC','PASS_M443T_FIXED_TEXT_DIAGNOSTIC').replace('单层','固定文本')
    atomic(w.HERE/'m443_text_support01.py',support.encode('utf-8'),immutable=True)
    result=dict(status='PREPARED_M443_FIXED_TEXT_AFTER_ACTUAL_LAYER01',build_id='0x4D343433',manifest_sha256=digest,
                prior_single_layer_raw_sha256=layer_sha,prior_raw_sha256=prep['prior_raw_sha256'],configuration_build_raw_sha256=prep['configuration_build_raw_sha256'],
                candidate_manifest_sha256=prep['candidate_manifest_sha256'],recursive_import_missing=missing,
                unchanged_original_math_head_policy_owner=True,additional_cma_requests_allowed=False,configuration_credits_granted=0,
                actual_configuration_before_runtime_buffers=True,unknown_configuration_retains_process=True,
                ps_growth_limit_bytes=256<<20,ps_available_margin_bytes=64<<20,
                files=[dict(path=p.relative_to(w.ROOT).as_posix(),sha256=w.sha(p)) for p in sorted(PKG.iterdir())],board_executed=False,performance_pass=False,promoted=False)
    atomic(RUN/'RESULT.json',w.encoded(result),immutable=True);s=w.sha(RUN/'RESULT.json');w.atomic=atomic
    w.sync('latest_m443_fixed_text_preparation01',dict(status=result['status'],result=(RUN/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=s,manifest_sha256=digest),
           '## M443固定文本准备01（2026-10-11）\n\nSHA '+s+'；实际M443单层原raw '+layer_sha+'闭合后，仅新核身份及独立配置合同接入原M441 30token/36层/LMhead全参考；原数学/owner/PS预算和累计计数保持，递归missing=0。尚未执行固定文本/视频/收益；下一步组件及collector破坏fixture检查后逐SHA上传一次文本。')
    print(result['status'],s,digest,len(rows))


if __name__=='__main__':main()
