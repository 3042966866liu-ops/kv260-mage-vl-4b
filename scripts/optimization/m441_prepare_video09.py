"""One actual M437 late11 fixed159 request; reuse the accepted numerical baseline."""
import ast,json,shutil,sys
from pathlib import Path
import m351_workflow as w
from m441_host_io08 import atomic
from m441_prepare_layer09 import once,verify_package

OLD=w.BASE/'candidates/M432-late11-integrated-video-02'
PKG=w.BASE/'candidates/M441-fixed-video-09'
REMOTE='/home/ubuntu/m441_fixed_video_candidate_09'
EVIDENCE='/home/ubuntu/m441_fixed_video_evidence_09'

def main():
    if PKG.exists():raise RuntimeError('Immutable package exists')
    text_raw=w.BASE/'runs/M441-fixed-text-board-09/BOARD_RESULT.json';td=w.sha(text_raw);r=json.loads(text_raw.read_bytes())
    assert r['status']=='PASS_M441T_FIXED_TEXT_DIAGNOSTIC' and all(r['exact_comparison'].values()) and r['safe_buffers_released'] and not r['unsafe_buffers_retained']
    assert all(td in (w.ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'))
    verify_package(OLD);base=w.BASE/'candidates/M441-fixed-text-09';verify_package(base)
    stage=w.ROOT/'tmp/m441_video09/package_staging02';stage.mkdir(parents=True,exist_ok=False)
    exclude={'PACKAGE_MANIFEST.json','SHA256SUMS','m432_gate.py','m432_entry.py','m432_export.py','m432_assemble.py','run_m432.sh','STAGE_PREREQUISITE.json','M357_COMPARE_PREREQUISITE.json','HARDWARE_CLOSURE.json','m432_trials.py','m432_request_visual.py'}
    for p in OLD.iterdir():
        if p.name not in exclude:shutil.copyfile(p,stage/p.name)
    shutil.copyfile(text_raw,stage/'STAGE_PREREQUISITE.json')
    for name in ('M441_COMPARE_PREREQUISITE.json','HARDWARE_CLOSURE.json'):shutil.copyfile(base/name,stage/name)
    t=(OLD/'m432_gate.py').read_text(encoding='utf-8')
    t=once(t,"Path('/home/ubuntu/m357_candidate_01')","Path('/home/ubuntu/m441_candidate_01')")
    t=once(t,"CAND_SHA = '2e9cbd00d0d01edf05e171674f71f86a94ce389a0658ce6c5466cebb77220d18'","CAND_SHA = '56253626a550c9c1358e805e6e3ad9b8b03c2fd9c1ff048be87c64c9f04dd5a0'")
    t=once(t,"PRIOR_SHA = 'ca35750d1b7043b76a16c75b97341616823137a58d91545576de0361a6ba3bde'","PRIOR_SHA = '0b416a17669ae1a5690a62650237ce6ced33f922017625f685401ca806e2273d'")
    guard="        if prior['status']!='PASS_INDEPENDENT_FIXED_TEXT_CAPACITY_AND_NUMERICS' or prior['raw_sha256']!='b7c2532715f6b90201c9c092e83bcf5245ad7e6ad0b3e5d9bdace60618406ebb':raise RuntimeError('Independent text prerequisite differs')"
    t=once(t,guard,"        if sha256(HERE/'STAGE_PREREQUISITE.json')!='"+td+"' or prior['status']!='PASS_M441T_FIXED_TEXT_DIAGNOSTIC' or not prior['numerical_pass'] or not prior['safe_buffers_released'] or prior['unsafe_buffers_retained']:raise RuntimeError('Actual M441 text prerequisite differs')\n        result['prior_fixed_text_raw_sha256']='"+td+"'")
    t=t.replace('M357_COMPARE_PREREQUISITE.json','M441_COMPARE_PREREQUISITE.json').replace('PASS_M357_COMPARE','PASS_M441_COMPARE').replace('Exact M357','Exact M441')
    t=t.replace("'0x4D333537' if is_candidate","'0x4D343431' if is_candidate").replace('/home/ubuntu/m432_late11_integrated_video_01',EVIDENCE).replace('M432','M441V').replace('m432_export','m441_video_export')
    t=t.replace('two real original/late11 candidate visual calls','one real late11 candidate visual call').replace('saved-feature-language-original-then-layers13-23','actual-late11-visual-and-full159-language')
    t=once(t,"        result['head_AST_checked_before_overlay']=True","        result['head_AST_checked_before_overlay']=True\n        result['source_compatibility_checked_before_overlay']=True")
    t=once(t,"        result['next_step'] = 'Close saved-feature decision consistency; no automatic expansion or performance'","        result['next_step'] = 'Close full M437-policy fixed159 numerical proof before freezing new complete-request comparison; no production change'")
    atomic(stage/'m441_video_gate.py',t.encode('utf-8'))
    trials=(OLD/'m432_trials.py').read_text(encoding='utf-8')
    trials=once(trials,'    for i,visual in enumerate(features):','    for i,visual in ((1,features[1]),):')
    a=trials.index('        if i==0:\n            numeric=');b=trials.index("        print('M432_PREFILL_COMPLETE",a)
    trials=trials[:a]+"        result['original_exact_comparison']=dict(exact_integrated,decision=decision==saved['decision'])\n        if not all(result['original_exact_comparison'].values()):raise ValueError('Accepted M437-policy decision differs')\n        result['original_reference_pass']=True\n        result['candidate_finite_complete']=True\n        result['saved_reference_variant']='late13_23_candidate'\n"+trials[b:]
    trials=trials.replace('M432','M441V')
    atomic(stage/'m432_trials.py',trials.encode('utf-8'))
    provider=(OLD/'m432_request_visual.py').read_text(encoding='utf-8')
    provider=once(provider,"if index not in (0, 1) or len(self.result['integrated_visual']) != index","if index != 1 or len(self.result['integrated_visual']) != 0")
    provider=provider.replace('Two sequential fixed requests only','One accepted late11 fixed request only').replace('M432','M441V')
    atomic(stage/'m432_request_visual.py',provider.encode('utf-8'))
    for old,new in [('m432_entry.py','m441_video_entry.py'),('m432_export.py','m441_video_export.py'),('run_m432.sh','run_m441_video.sh')]:
        src=(OLD/old).read_text(encoding='utf-8').replace('m432_gate.py','m441_video_gate.py').replace('m432_entry.py','m441_video_entry.py').replace('m432_export.py','m441_video_export.py').replace('/home/ubuntu/m432_late11_integrated_video_01',EVIDENCE).replace('M432','M441V')
        atomic(stage/new,src.encode('utf-8'))
    # Copy only exact proven remote payloads or exact saved raw; verify every resulting file.
    assemble=(base/'m441_text_assemble.py').read_text(encoding='utf-8')
    anchor=' source[sha(saved_layer)]=saved_layer'
    extra="\n old3=Path('/home/ubuntu/m432_late11_integrated_candidate_02')\n if sha(old3/'PACKAGE_MANIFEST.json')!='"+w.sha(OLD/'PACKAGE_MANIFEST.json')+"':raise RuntimeError('Actual integrated source package differs')\n source.update({r['sha256']:old3/r['path'] for r in json.loads((old3/'PACKAGE_MANIFEST.json').read_bytes())['files']})\n saved_text=Path('/home/ubuntu/m441_fixed_text_evidence_09/B1/load-memory.json')\n if sha(saved_text)!='"+td+"':raise RuntimeError('Actual saved text differs')\n source[sha(saved_text)]=saved_text\n"
    assemble=once(assemble,anchor,anchor+extra).replace('M441T','M441V')
    atomic(stage/'m441_video_assemble.py',assemble.encode('utf-8'))
    # Verify the remote source from the actual prior upload controller, not a inferred version suffix.
    oldcontrol=(w.HERE/'m432_control02.ps1')
    if not oldcontrol.exists():oldcontrol=w.HERE/'m432_control.ps1'
    cs=oldcontrol.read_text(encoding='utf-8-sig')
    assert '/home/ubuntu/m432_late11_integrated_candidate_02' in cs,'Actual M432 remote path differs'
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(stage.iterdir())]
    atomic(stage/'SHA256SUMS',''.join(x['sha256']+'  '+x['path']+'\n' for x in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(stage/'SHA256SUMS').stat().st_size,sha256=w.sha(stage/'SHA256SUMS')))
    atomic(stage/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='m441-fixed-video-v09',files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))))
    verify_package(stage)
    assert t.index('head_AST_checked_before_overlay')<t.index("patch(pynq,'Overlay'")<t.index('engine.load()')
    assert (stage/'m431_borrowed_visual.py').read_bytes()==(OLD/'m431_borrowed_visual.py').read_bytes()
    assert (stage/'m369_light_policy.py').read_bytes()==(OLD/'m369_light_policy.py').read_bytes()
    trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in stage.glob('*.py')}
    closure=json.loads((stage/'SOURCE_CLOSURE.json').read_bytes());allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','torch','pynq','tokenizers','ps_slot_capacity','measurement','m363_package_identity','m363_observers','m341_build_id_gate','frozen_video_identity','m368_video_contract','memory_lifecycle','m368_stage_policy','m368_head_observer','m363_tokenizer_once'}
    # External imports are original pinned reused manifests; inspect their local payload names too.
    oldreuse=w.BASE/'candidates/M368-staged-video-03';allowed|={p.stem for p in oldreuse.glob('*.py')}
    for candidate in w.BASE.joinpath('candidates').glob('M4*'):
        for p in candidate.glob('*.py'):allowed.add(p.stem)
    missing=[]
    for name,tree in trees.items():
        for node in ast.walk(tree):
            names=[x.name.split('.')[0] for x in node.names] if isinstance(node,ast.Import) else [(node.module or '').split('.')[0]] if isinstance(node,ast.ImportFrom) else []
            missing.extend((name,x) for x in names if x and x not in trees and x not in allowed)
    assert not missing,missing
    stage.rename(PKG)
    # Derive the original strict numerical collector, selecting exactly the accepted B reference.
    c=(w.HERE/'m432_workflow02.py').read_text(encoding='utf-8');c=c[:c.index('\ndef collect(')]
    c=c.replace('M432-late11-integrated-video-02','M441-fixed-video-09').replace('M432-integrated-video-board-01','M441-fixed-video-board-09').replace('M432','M441V').replace('0x4D333537','0x4D343431').replace('0x4d333537','0x4d343431')
    c=c.replace('<=2','<=1').replace("r.get('vision_forward_calls')!=2","r.get('vision_forward_calls')!=1").replace("r['model_forward_calls']!=2","r['model_forward_calls']!=1")
    c=once(c,"len(samples)!=2 or [s['variant'] for s in samples]!=plan['variants']","len(samples)!=1 or [s['variant'] for s in samples]!=plan['variants'][1:]")
    c=once(c,'for i,s in enumerate(samples):','for i,s in enumerate(samples,1):')
    a=c.index('            if i==0:\n');b=c.index("        if r['fpga_transactions']",a);c=c[:a]+c[b:]
    c=c.replace("r['logical_calls']!=1556","r['logical_calls']!=778").replace("zip(samples,language['samples'])","zip(samples,language['samples'][1:])").replace("r['transactions']!=language['transactions']","r['transactions']!=language['transactions'][language['samples'][0]['counts']['host_calls']:]")
    c=c.replace("r.get('integrated_visual')!=[x['tensor'] for x in plan['features']]","r.get('integrated_visual')!=[plan['features'][1]['tensor']]").replace("len(r.get('integrated_exact_comparisons',[]))!=2","len(r.get('integrated_exact_comparisons',[]))!=1")
    a=c.index("        q=r['logit_comparison']");b=c.index("        if r['head_observer_proof']",a)
    c=c[:a]+"        if r.get('saved_reference_variant')!='late13_23_candidate' or samples[0]['decision']!=language['samples'][1]['decision']:raise ValueError('Complete accepted baseline decision differs')\n        files=r['logit_files']\n        if len(files)!=1 or files[0]['path']!='late13_23_candidate_logits.npy' or files[0]['tensor']!=samples[0]['logits'] or files[0]['file_bytes']!=607872 or not re.fullmatch('[0-9a-f]{64}',files[0]['file_sha256']):raise ValueError('Saved complete logits identity differs')\n        if r.get('prior_fixed_text_raw_sha256')!='"+td+"' or r.get('source_compatibility_checked_before_overlay') is not True or r.get('prior_board_sha256')!='0b416a17669ae1a5690a62650237ce6ced33f922017625f685401ca806e2273d':raise ValueError('Actual M441 prerequisite differs')\n"+c[b:]
    c+= '''
def collect(path):
    digest,raw,r,count=decode(Path(path).read_text(encoding='utf-8-sig'))
    atomic(OUT,raw,immutable=True)
    atomic(OUT.with_name('COLLECTION.json'),encoded(dict(raw_sha256=digest,chunks=count,source_log=str(path),source_log_sha256=sha(Path(path)),reexecuted=False)),immutable=True)
    sync('latest_m441_fixed_video_board',dict(status=r['status'],result=OUT.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256'],build_id=r['build_id'],numerical_pass=r['numerical_pass'],performance_pass=False),f'## M441 固定159视频数值闭合09（2026-10-09）\\n\\nraw {digest}，{count}个900B原字节块；{r["status"]}，原rc{r["gate_return_code"]}。M437后11层视觉、原单parser/无预读，同末帧两视图/159提示，完整视觉边界/语言/KV/logits/重试逐位已接受参考，七DMA借用生命周期。仅数值，非请求性能或晋级；失败只本级。')
    print(json.dumps(dict(status=r['status'],sha256=digest,errors=r['errors'],host_calls=r.get('host_calls'),logical_calls=r.get('logical_calls'),transactions=r['fpga_transactions'])))
    return r['gate_return_code']
if __name__=='__main__':
    import sys
    raise SystemExit(collect(sys.argv[1]))
'''
    atomic(w.HERE/'m441_video_collect09.py',c.encode('utf-8'),immutable=True)
    # Frozen controller retains failure collection and same-TTY shellguard.
    ctl=(w.HERE/'m441_text_control09.ps1').read_text(encoding='utf-8').replace('fixed-text','fixed-video').replace('FIXED_TEXT','FIXED_VIDEO').replace('m441_text','m441_video').replace('m441_fixed_text','m441_fixed_video').replace('M441T','M441V').replace('latest_m441_single_layer','latest_m441_fixed_video')
    ctl=once(ctl," $taskOldText=Get-Content (Join-Path $taskBase 'candidates/M366-staged-text-03/PACKAGE_MANIFEST.json')", " $taskOldText=Get-Content (Join-Path $taskBase 'candidates/M432-late11-integrated-video-02/PACKAGE_MANIFEST.json')")
    ctl=once(ctl,"'16b7aeb84dad97dbfbbdff06311becff9cf7866261316cc18dc296a97f0132e4'","'"+td+"'")
    ctl=ctl.replace('-TimeoutSeconds 900 -MarkerPrefix','-TimeoutSeconds 1500 -MarkerPrefix').replace('M441V_ENABLE_STAGED_LAYER=1','M441V_ENABLE_INTEGRATED_VIDEO=1').replace('$taskSHA $Mode B1','$taskSHA $Mode')
    atomic(w.HERE/'m441_video_control09.ps1',ctl.encode('utf-8'),immutable=True)
    out=w.BASE/'runs/M441-fixed-video-preparation-09'
    budget=dict(full36layer_KV_bytes=36*2*159*8*128*4,gate_up_arrays_bytes=2*159*9728*4,full_logits_bytes=151936*4,attention_two_score_arrays_bytes=2*(32//8)*159*159*4,visual_saved_feature_bytes=98*2560*4,ordinary_growth_limit_bytes=1024<<20,ordinary_remaining_margin_bytes=64<<20,extra_DMA_after_seal=0,vision_unpack_and_lazy_native_peak_certified=False,policy_reused_from='M43202/M437')
    result=dict(status='PREPARED_M441_FIXED159_SAME_M437_POLICY',manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),prior_text_raw_sha256=td,reference_sample=1,original_M432_manifest_sha256=w.sha(OLD/'PACKAGE_MANIFEST.json'),one_actual_visual_language_request=True,selected_layers=list(range(13,24)),expected_language_logical=778,expected_language_physical=781,expected_visual_physical=286,total_with_minimal=1068,budget=budget,recursive_import_missing=missing,head_compatibility_before_overlay=True,borrowed_buffer_module_unchanged=True,board_executed=False,performance_pass=False)
    atomic(out/'RESULT.json',w.encoded(result),immutable=True);d=w.sha(out/'RESULT.json')
    w.sync('latest_m441_fixed_video_preparation',dict(status=result['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=d,manifest_sha256=result['manifest_sha256']),f'## M441 固定159视频准备09（2026-10-09）\n\n固定文本raw {td}闭合后，仅新核身份及一个既有M437后11层视觉请求，直接逐位参考旧M428接受的B样本，不重复原视觉A。778语言逻辑/781物理、286视觉物理+1最小，PS1GiB诊断预算+其外64MiB普通可用余量，七DMA借用无新bank/slot，无固定CMA64拒绝/温度。准备SHA {d}，0执行/性能。')
    print(result['status'],d,result['manifest_sha256'])

if __name__=='__main__':main()
