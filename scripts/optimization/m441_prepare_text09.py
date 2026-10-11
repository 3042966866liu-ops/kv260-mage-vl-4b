"""Prepare one fixed-text attempt after the new M441 single-layer closure."""
import ast
import json
import shutil
import sys
from pathlib import Path
import m351_workflow as w
from m441_host_io08 import atomic
from m441_prepare_layer09 import once,verify_package
from m366_head_observer import instrument_source

OLD=w.BASE/'candidates/M366-staged-text-03'
PKG=w.BASE/'candidates/M441-fixed-text-09'
LAYER=w.BASE/'runs/M441-single-layer-board-09/BOARD_RESULT.json'
REMOTE='/home/ubuntu/m441_fixed_text_candidate_09'
EVIDENCE='/home/ubuntu/m441_fixed_text_evidence_09'

def main():
    if PKG.exists():raise RuntimeError('Immutable package exists')
    r=json.loads(LAYER.read_bytes());ld=w.sha(LAYER)
    assert r['status']=='PASS_M441L_SINGLE_LAYER_DIAGNOSTIC' and r['numerical_pass'] and r['safe_buffers_released'] and not r['unsafe_buffers_retained']
    assert all(ld in (w.ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
    verify_package(OLD);base=w.BASE/'candidates/M441-single-layer-09';verify_package(base)
    PKG.mkdir(parents=True)
    exclude={'PACKAGE_MANIFEST.json','SHA256SUMS','m366_assemble.py','m366_staged_text_gate.py','m366_export_result.py','run_m366_staged_text.sh','STAGE_PREREQUISITE.json','HARDWARE_CLOSURE.json','M357_COMPARE_PREREQUISITE.json'}
    for p in OLD.iterdir():
        if p.name not in exclude:shutil.copyfile(p,PKG/p.name)
    shutil.copyfile(LAYER,PKG/'STAGE_PREREQUISITE.json')
    for name in ('HARDWARE_CLOSURE.json','M441_COMPARE_PREREQUISITE.json'):shutil.copyfile(base/name,PKG/name)
    text=(OLD/'m366_staged_text_gate.py').read_text(encoding='utf-8')
    text=once(text,"Path('/home/ubuntu/m357_candidate_01')","Path('/home/ubuntu/m441_candidate_01')")
    target=w.BASE/'candidates/M441-record-load-01'
    text=once(text,"CAND_SHA = '2e9cbd00d0d01edf05e171674f71f86a94ce389a0658ce6c5466cebb77220d18'","CAND_SHA = '"+w.sha(target/'PACKAGE_MANIFEST.json')+"'")
    compare='0b416a17669ae1a5690a62650237ce6ced33f922017625f685401ca806e2273d'
    text=once(text,"PRIOR_SHA = 'ca35750d1b7043b76a16c75b97341616823137a58d91545576de0361a6ba3bde'","PRIOR_SHA = '"+compare+"'")
    guard="        if prior['status']!='PASS_ONE_LAYER_UNDER_INDEPENDENT_POLICY' or prior['raw_sha256']!='54261095541d69f53179f410df76640302e1f146714c52dc8e4ed52274c2771a':raise RuntimeError('Independent layer prerequisite differs')"
    text=once(text,guard,"        if sha256(HERE/'STAGE_PREREQUISITE.json')!='"+ld+"' or prior['status']!='PASS_M441L_SINGLE_LAYER_DIAGNOSTIC' or not prior['numerical_pass'] or not prior['safe_buffers_released'] or prior['unsafe_buffers_retained']:raise RuntimeError('Actual M441 single-layer prerequisite differs')\n        result['prior_single_layer_raw_sha256']='"+ld+"'")
    text=text.replace('M357_COMPARE_PREREQUISITE.json','M441_COMPARE_PREREQUISITE.json').replace('PASS_M357_COMPARE','PASS_M441_COMPARE').replace('Exact M357','Exact M441')
    text=text.replace("'0x4D333537' if is_candidate","'0x4D343431' if is_candidate")
    text=text.replace('/home/ubuntu/m366_staged_text_02',EVIDENCE)
    text=once(text,"        policy=StagePolicy(result,lambda:runtime,base)","        import inspect\n        from m366_head_observer import instrument_source\n        instrument_source(inspect.getsource(m243_video_server.M238PrefillRuntime._execute))\n        result['source_compatibility_checked_before_overlay']=True\n        result['head_AST_checked_before_overlay']=True\n        policy=StagePolicy(result,lambda:runtime,base)")
    text=text.replace('M366','M441T').replace('m366_staged_text_gate','m441_text_gate').replace('m366_export_result','m441_text_export').replace('_m366_closed','_m441t_closed')
    atomic(PKG/'m441_text_gate.py',text.encode('utf-8'))
    export=(OLD/'m366_export_result.py').read_text(encoding='utf-8').replace('/home/ubuntu/m366_staged_text_02',EVIDENCE).replace('M366','M441T')
    atomic(PKG/'m441_text_export.py',export.encode('utf-8'))
    runner=(OLD/'run_m366_staged_text.sh').read_text(encoding='utf-8').replace('/home/ubuntu/m366_staged_text_02',EVIDENCE).replace('m366_staged_text_gate.py','m441_text_gate.py').replace('m366_export_result.py','m441_text_export.py').replace('M366','M441T')
    atomic(PKG/'run_m441_text.sh',runner.encode('utf-8'))
    assemble=(base/'m441_layer_assemble.py').read_text(encoding='utf-8')
    anchor=" source[sha(saved)]=saved"
    extra="""
 old2=Path('/home/ubuntu/m366_staged_text_candidate_03')
 if sha(old2/'PACKAGE_MANIFEST.json')!='OLD_MANIFEST':raise RuntimeError('Pinned proven text package differs')
 source.update({r['sha256']:old2/r['path'] for r in json.loads((old2/'PACKAGE_MANIFEST.json').read_bytes())['files']})
 saved_layer=Path('/home/ubuntu/m441_single_layer_evidence_09/B1/load-memory.json')
 if sha(saved_layer)!='LAYER_DIGEST':raise RuntimeError('Saved actual layer differs')
 source[sha(saved_layer)]=saved_layer
""".replace('OLD_MANIFEST',w.sha(OLD/'PACKAGE_MANIFEST.json')).replace('LAYER_DIGEST',ld)
    assemble=once(assemble,anchor,anchor+extra).replace('M441L','M441T')
    atomic(PKG/'m441_text_assemble.py',assemble.encode('utf-8'))
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(x['sha256']+'  '+x['path']+'\n' for x in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=w.sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='m441-independent-fixed-text-v09',files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))))
    verify_package(PKG)
    closure=json.loads((PKG/'SOURCE_CLOSURE.json').read_bytes());release=w.ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    for row in closure['files']:assert w.sha(release/row['path'])==row['sha256']
    source=(release/closure['modules']['m230_prefill_runtime']).read_text(encoding='utf-8')
    cls=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='M230PrefillRuntime')
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_execute')
    instrument_source(''.join(source.splitlines(keepends=True)[method.lineno-1:method.end_lineno]))
    trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')}
    allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers'};missing=[]
    for module,t in trees.items():
        for n in ast.walk(t):
            names=[a.name.split('.')[0] for a in n.names] if isinstance(n,ast.Import) else [(n.module or '').split('.')[0]] if isinstance(n,ast.ImportFrom) else []
            missing.extend((module,name) for name in names if name and name not in trees and name not in allowed)
    assert not missing,missing
    assert text.index('instrument_source(inspect.getsource(')<text.index("patch(pynq,'Overlay'")<text.index('engine.load()')
    assert (PKG/'m366_stage_policy.py').read_bytes()==(OLD/'m366_stage_policy.py').read_bytes()
    assert (PKG/'owned_buffer_release.py').read_bytes()==(OLD/'owned_buffer_release.py').read_bytes()
    collector=(w.HERE/'m441_layer_collect09.py').read_text(encoding='utf-8')
    collector=collector.replace('M441-single-layer-09','M441-fixed-text-09').replace("'m365_collect.py'","'m36603_collect.py'").replace('M365-staged-layer-03','M366-staged-text-03').replace("replace('M365','M441L')","replace('M366','M441T')").replace('M441L_SINGLE_LAYER_DIAGNOSTIC','M441T_FIXED_TEXT_DIAGNOSTIC').replace('m441_single_layer','m441_fixed_text').replace('M441-single-layer-board-09','M441-fixed-text-board-09')
    collector=once(collector,"        if r.get('additional_cma_requests_allowed') is not False:raise ValueError('Allocation seal absent')","        if r.get('additional_cma_requests_allowed') is not False:raise ValueError('Allocation seal absent')\n        if r.get('prior_single_layer_raw_sha256')!='"+ld+"' or r.get('head_AST_checked_before_overlay') is not True:raise ValueError('Single layer/head admission differs')")
    collector=collector.replace('单层板端闭合09','固定文本板端闭合09').replace('单层159重复文本embedding，五family/hidden/KV/重试逐位参考','原30token/36层/完整LM head，154family/151936logits/72KV/重试逐位参考').replace('下一步PASS后独立固定文本预算和数值包','下一步PASS后独立固定159视频预算和数值包')
    atomic(w.HERE/'m441_text_collect09.py',collector.encode('utf-8'),immutable=True)
    control=(w.HERE/'m441_layer_control09.ps1').read_text(encoding='utf-8').replace('M441-single-layer','M441-fixed-text').replace('M441_SINGLE_LAYER','M441_FIXED_TEXT').replace('m441_layer','m441_text').replace('m441_single_layer','m441_fixed_text').replace('M441L','M441T')
    oldhash=" $taskOldHashes=@($taskOld.files|ForEach-Object sha256)+@('"+compare+"')"
    newhash=" $taskOldText=Get-Content (Join-Path $taskBase 'candidates/M366-staged-text-03/PACKAGE_MANIFEST.json') -Raw -Encoding UTF8|ConvertFrom-Json\n $taskOldHashes=@($taskOld.files|ForEach-Object sha256)+@($taskOldText.files|ForEach-Object sha256)+@('"+compare+"','"+ld+"')"
    control=once(control,oldhash,newhash)
    atomic(w.HERE/'m441_text_control09.ps1',control.encode('utf-8'),immutable=True)
    support=(w.HERE/'m441_layer_support09.py').read_text(encoding='utf-8').replace('m441_layer_collect09','m441_text_collect09').replace('M365-staged-layer-board-01','M366-staged-text-board-02').replace('PASS_M365_SINGLE_LAYER_DIAGNOSTIC','PASS_M366_FIXED_TEXT_DIAGNOSTIC').replace('PASS_M441L_SINGLE_LAYER_DIAGNOSTIC','PASS_M441T_FIXED_TEXT_DIAGNOSTIC').replace('M441L','M441T').replace('m441_layer','m441_text').replace('M441-single-layer','M441-fixed-text').replace('M441_SINGLE_LAYER','M441_FIXED_TEXT').replace('original_m365_reference','original_m366_reference').replace('单层','固定文本')
    support=once(support,"    r['final_snapshot']['ap_return']=0x4d343431","    r['prior_single_layer_raw_sha256']='"+ld+"'\n    r['head_AST_checked_before_overlay']=True\n    r['final_snapshot']['ap_return']=0x4d343431")
    support=once(support,"('source_compatibility_checked_before_overlay',False)","('source_compatibility_checked_before_overlay',False),('prior_single_layer_raw_sha256','0'*64),('head_AST_checked_before_overlay',False),('head_observer_proof',{'removed_observation_calls_ast_equals_original':False})")
    atomic(w.HERE/'m441_text_support09.py',support.encode('utf-8'),immutable=True)
    budget=dict(full36layer_KV=36*2*30*8*128*4,gate_up_two_arrays=2*30*9728*4,full_last_row_logits=151936*4,attention_two_score_matrices=2*(32//8)*30*30*4,diagnostic_ps_growth_limit=256<<20,ordinary_available_margin=64<<20,extra_explicit_cma_after_seal=0,native_peak_certified=False)
    out=w.BASE/'runs/M441-fixed-text-preparation-09'
    result=dict(status='PREPARED_M441_FIXED_TEXT_AFTER_ACTUAL_LAYER',build_id='0x4D343431',manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),prior_single_layer_raw_sha256=ld,unchanged_M366_head_observer_sha256=w.sha(PKG/'m366_head_observer.py'),recursive_import_missing=missing,head_source_AST_checked_before_overlay=True,budget=budget,seven_buffers_sealed=True,fixed_cma_reserve_enforced=False,board_executed=False,performance_pass=False,promotion=False)
    atomic(out/'RESULT.json',w.encoded(result),immutable=True);d=w.sha(out/'RESULT.json')
    w.sync('latest_m441_fixed_text_preparation',dict(status=result['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=d,manifest_sha256=result['manifest_sha256']),f'## M441 固定文本入口准备09（2026-10-09）\n\n单层raw {ld} 完整闭合后复用M36603原30token/36层/151936logits/72KV参考和8次head物理观察，AST兼容提前Overlay前；七DMA后封锁新增，PS256MiB观察预算+普通可用64MiB余量，非CMA固定拒绝。0执行/视频/性能。准备SHA {d}。')
    print(result['status'],d,result['manifest_sha256'])

if __name__=='__main__':main()
