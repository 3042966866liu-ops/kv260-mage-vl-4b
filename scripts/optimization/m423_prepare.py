"""Prepare exactly two integrated fixed159 requests, before any timing study."""
import ast,json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m421_prepare import once
OLD=BASE/'candidates/M421-combination-saved-language-01'
PKG=BASE/'candidates/M423-integrated-video-01'

def main():
    if PKG.exists():raise RuntimeError('Immutable integrated staging exists')
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());prior={}
    for key in ('latest_m420_combination_board','latest_m420_combination_closure','latest_m421_saved_language_board','latest_m421_saved_language_closure','latest_m422_shared_DMA_integration_audit','latest_m422_borrowed_DMA_component'):
        e=b[key];assert sha(ROOT/e['result'])==e['sha256'] and all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'));prior[key]=e
    component=json.loads((ROOT/prior['latest_m422_borrowed_DMA_component']['result']).read_bytes())
    assert component['source_sha256']['m422_borrowed_visual.py']==sha(HERE/'m422_borrowed_visual.py')
    for key,status in [('latest_m420_combination_board','PASS_M420_LAYERS12_13_FULL_VISUAL_FEATURE_QUALITY'),('latest_m421_saved_language_board','PASS_M421_SAVED_FEATURE_DECISION_CONSISTENCY')]:
        r=json.loads((ROOT/prior[key]['result']).read_bytes());assert r['status']==status and r['gate_return_code']==0 and r['safe_buffers_released']
    oldmanifest=json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes())
    for row in oldmanifest['files']:assert sha(OLD/row['path'])==row['sha256']
    plan=json.loads((OLD/'PLAN.json').read_bytes());combo=BASE/'candidates/M420-layers12-13-full-visual-02';vp=json.loads((combo/'PLAN.json').read_bytes())
    plan.update(prerequisites=prior,integrated_visual_calls=2,integrated_language_calls=2,extra_DMA=0,performance_measurement=False,
        integrated_sources=dict(visual=dict(path='/home/ubuntu/m420_combination_visual_02/BOARD_RESULT.json',sha256=prior['latest_m420_combination_board']['sha256'],status='PASS_M420_LAYERS12_13_FULL_VISUAL_FEATURE_QUALITY'),language=dict(path='/home/ubuntu/m421_saved_feature_language_01/BOARD_RESULT.json',sha256=prior['latest_m421_saved_language_board']['sha256'],status='PASS_M421_SAVED_FEATURE_DECISION_CONSISTENCY')),
        visual_reused_packages=[dict(directory='/home/ubuntu/m420_combination_visual_candidate_02',manifest_sha256=sha(combo/'PACKAGE_MANIFEST.json'))]+vp['reused_packages'],lower_packages=vp['lower_packages'],
        numerical_rule='A visual and full original language exact; B computed visual, all154 language families, full72KV/logits and retries exact saved M420/M421 B. No new quality thresholds or timing claim.',visual_logical_calls=52,total_language_logical_calls=1556,additional_visual_stage_bytes=8912896,
        request_boundary='Two independent fixed computational requests, original preprocessing→visual→same original language/head. This is numerical integration, not normal service/Web admission or timing.')
    texts={}
    for name in ('m421_gate.py','m421_trials.py','m421_export.py','m421_saved_features.py'):
        s=(OLD/name).read_text(encoding='utf-8').replace('m421','m423').replace('M421','M423').replace('PASS_M423_SAVED_FEATURE_DECISION_CONSISTENCY','PASS_M423_INTEGRATED_VIDEO_NUMERICAL')
        s=s.replace('saved-feature-fixed159-language-quality','integrated-fixed159-visual-language-quality').replace('m423_saved_feature_language_01','m423_integrated_video_01')
        texts[name.replace('421','423')]=s
    g=texts['m423_gate.py']
    g=once(g,"        features,feature_ids=load_features(plan)","        from m423_request_visual import verify_sources\n        integrated_sources=verify_sources(plan)\n        result['integrated_sources_checked_before_overlay']=True\n        features,feature_ids=load_features(plan)")
    g=once(g,"                raise RuntimeError('Saved-feature gate forbids visual forward')","                if result.get('vision_request_active') is not True:raise RuntimeError('Integrated visual request scope not active')\n                return super().__call__(*a,**kw)")
    g=once(g,"        run(engine,runtime,policy,base,HERE,EVIDENCE,result,patch,features)","        from m423_request_visual import VisualProvider\n        provider=VisualProvider(engine,runtime,policy,base,HERE,result,integrated_sources)\n        run(engine,runtime,policy,base,HERE,EVIDENCE,result,patch,features,provider)\n        provider.dispose()")
    g=once(g,"+len(result.get('transactions',[]))","+len(result.get('transactions',[]))+len(result.get('visual_transactions',[]))")
    g=g.replace('two immutable saved features through unchanged language/head; no visual forward, no extra CMA/PS slot; no performance or layer expansion','two real original/candidate visual calls borrowing existing seven buffers, then unchanged language/head; no extra DMA/PS slot; no performance or expansion')
    texts['m423_gate.py']=g
    s=texts['m423_trials.py'];s=once(s,'def run(engine,runtime,policy,base,here,output,result,patch,features):','def run(engine,runtime,policy,base,here,output,result,patch,features,provider):')
    s=once(s,"        variant='original' if i==0 else 'layer12_13_candidate';families.clear()","        visual=provider(i)\n        variant='original' if i==0 else 'layer12_13_candidate';families.clear()")
    s=once(s,'        token,logits,kv=model.prefill(hidden)',"        result['language_scope_active']=True\n        try:token,logits,kv=model.prefill(hidden)\n        finally:result['language_scope_active']=False")
    anchor="        if i==0:\n            numeric="
    extra="        saved=provider.sources['language']['samples'][i]\n        exact_integrated={key:sample[key]==saved[key] for key in ('input','visual','token','logits','keys','values','families','grouped_attention_calls','counts')}\n        result.setdefault('integrated_exact_comparisons',[]).append(exact_integrated)\n        if not all(exact_integrated.values()):raise ValueError('Full integrated language differs from saved M421 reference')\n"
    s=once(s,anchor,extra+anchor);texts['m423_trials.py']=s
    assembly=(OLD/'m421_assemble.py').read_text(encoding='utf-8')
    assembly=once(assembly,"OLD=Path('/home/ubuntu/m415_saved_feature_candidate_04')","OLD=Path('/home/ubuntu/m421_saved_feature_candidate_01')")
    assembly=once(assembly,'20d90f813051938818301c1c7714cc73a6b977c663f7b47c1156e90dae423e2d',sha(OLD/'PACKAGE_MANIFEST.json'))
    texts['m423_assemble.py']=assembly.replace('M421_ASSEMBLY_PASS','M423_ASSEMBLY_PASS')
    texts['run_m423.sh']=(OLD/'run_m421.sh').read_text(encoding='utf-8').replace('m421','m423').replace('M421','M423').replace('m423_saved_feature_language_01','m423_integrated_video_01')
    PKG.mkdir()
    changed={row['path'] for row in oldmanifest['files'] if row['path'].startswith('m421') or row['path'] in ('PLAN.json','SHA256SUMS','run_m421.sh')}
    for row in oldmanifest['files']:
        if row['path'] not in changed:atomic(PKG/row['path'],(OLD/row['path']).read_bytes(),immutable=True)
    for name,source in [('m423_request_visual.py',HERE/'m423_request_visual.py'),('m422_borrowed_visual.py',HERE/'m422_borrowed_visual.py'),('m411_mlp_binding.py',combo/'m411_mlp_binding.py')]:texts[name]=source.read_text(encoding='utf-8')
    for name,s in texts.items():
        if name.endswith('.py'):ast.parse(s,feature_version=(3,10))
        atomic(PKG/name,s.encode('utf-8'),immutable=True)
    atomic(PKG/'PLAN.json',encoded(plan),immutable=True)
    names=sorted(p.name for p in PKG.iterdir());atomic(PKG/'SHA256SUMS',''.join(f'{sha(PKG/n)}  {n}\n' for n in names).encode('ascii'),immutable=True)
    files=sorted(PKG.iterdir());m=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(PKG/'PACKAGE_MANIFEST.json',encoded(m),immutable=True)
    v=dict(status='PASS_M423_PREPARATION_ONLY',prerequisites=prior,manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),file_count=m['file_count'],total_bytes=m['total_bytes'],plan=plan,prior_successful_manifest_sha256=sha(OLD/'PACKAGE_MANIFEST.json'),board_run=False,numerical_pass=False,performance_pass=False)
    p=BASE/'runs/M423-integrated-preparation-01/RESULT.json';atomic(p,encoded(v),immutable=True)
    sync('latest_m423_integrated_preparation',dict(status=v['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=v['manifest_sha256']),f'## M423 两层视觉接原语言数值准备（2026-10-06）\n\nSHA {sha(p)}；实际原版视觉→原语言一次、12＋13 PL借原七DMA视觉→原语言一次；52视觉PL＋1556语言逻辑分账，原缩放重试/pack/parse/GELU/Attention/输入策略不变。A全参考、B特征/154family/72KV/logits/重试须逐位M420/M421保存结果；源SHA/依赖前移资源之前，封锁新增DMA，切换清除静态寄存器缓存。只是准备，未上板或净耗时结论；组件/回收通过后一次数值，不能先性能/扩层/生产晋级。')
    print('M423_PREPARATION_SYNC',sha(p),v['manifest_sha256'],m['file_count'],m['total_bytes'])
if __name__=='__main__':main()
