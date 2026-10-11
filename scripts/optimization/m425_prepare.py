"""Build a clean, whitelisted lightweight warm-performance candidate."""
import ast,json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m421_prepare import once
OLD=BASE/'candidates/M423-integrated-video-01'
PKG=BASE/'candidates/M425-visual-MLP-warm-performance-02'

def main():
    if PKG.exists():raise RuntimeError('Immutable stage exists')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());prior={}
    for key in ('latest_m423_integrated_board','latest_m423_integrated_closure','latest_m425_warm_protocol'):
        e=board[key];assert sha(ROOT/e['result'])==e['sha256']
        assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'));prior[key]=e
    assert prior['latest_m423_integrated_closure']['numerical_pass'] is True
    protocol=(ROOT/prior['latest_m425_warm_protocol']['result']).with_name('PROTOCOL.json')
    assert sha(protocol)==prior['latest_m425_warm_protocol']['protocol_sha256']
    m=json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes())
    for row in m['files']:assert sha(OLD/row['path'])==row['sha256']
    texts={}
    g=(OLD/'m423_gate.py').read_text(encoding='utf-8')
    g=once(g,'/home/ubuntu/m423_integrated_video_01','/home/ubuntu/m425_warm_performance_01')
    g=g.replace('integrated-fixed159-visual-language-quality','controlled-warm-complete-request-performance')
    g=once(g,'from measurement import sha256, write_json', '''from measurement import sha256
def write_json(path,value):
    # Same atomic fsync/replace; compact JSON preserves every original field.
    path=Path(path);payload=(json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\\n').encode('utf-8')
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+f'.{os.getpid()}.partial')
    with temp.open('wb') as f:f.write(payload);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)''')
    g=g.replace('M423_HEARTBEAT','M425_HEARTBEAT').replace('M423_MEMORY','M425_MEMORY').replace('M423_FAILURE_OR_COMPLETION_STATE','M425_FAILURE_OR_COMPLETION_STATE').replace('M423_RESULT_SAVED','M425_RESULT_SAVED')
    g=g.replace('> 900','> 3000')
    g=once(g,"        from m423_trials import run","        from m425_trials import run")
    g=once(g,"        from m423_request_visual import VisualProvider\n        provider=VisualProvider(engine,runtime,policy,base,HERE,result,integrated_sources)","        from m425_timed_visual import TimedVisualProvider\n        provider=TimedVisualProvider(engine,runtime,policy,base,HERE,result,integrated_sources,enabled=True)")
    g=g.replace('PASS_M423_INTEGRATED_VIDEO_NUMERICAL','PASS_M425_CONTROLLED_WARM_MEASUREMENTS_COLLECTED')
    g=once(g,"        result['integrated_sources_checked_before_overlay']=True", "        perf_plan=json.loads((HERE/'PERFORMANCE_PLAN.json').read_bytes())\n        p=Path(perf_plan['integrated_numerical_result'])\n        if sha256(p)!=perf_plan['integrated_numerical_sha256']:raise RuntimeError('M423 full numerical prerequisite SHA differs')\n        q=json.loads(p.read_bytes())\n        if q['status']!='PASS_M423_INTEGRATED_VIDEO_NUMERICAL' or q['gate_return_code']!=0 or not q['numerical_pass'] or not q['safe_buffers_released'] or not q['stable_overlay_reloaded']:raise RuntimeError('M423 numerical/owner prerequisite differs')\n        if sha256(HERE/'WARM_PROTOCOL.json')!=perf_plan['protocol_sha256']:raise RuntimeError('New protocol SHA differs')\n        result['temperature_measurement_enabled']=False\n        result['integrated_sources_checked_before_overlay']=True")
    g=once(g,"(1 if policy is not None and policy.ever else 0)+len(result.get('transactions',[]))+len(result.get('visual_transactions',[]))","(1 if policy is not None and policy.ever else 0)+result.get('completed_language_physical',0)+result.get('completed_visual_physical',0)+len(result.get('transactions',[]))+len(result.get('visual_transactions',[]))")
    g=g.replace('from m423_export import emit_saved','from m425_export import emit_saved')
    g=g.replace('two real original/candidate visual calls borrowing existing seven buffers, then unchanged language/head; no extra DMA/PS slot; no performance or expansion','fixed four warmups and eight formal original/candidate complete requests; seven resident buffers; no extra DMA, temperature reads or layer expansion')
    g=g.replace('Close saved-feature decision consistency; no automatic expansion or performance','Collect saved bytes, synchronize, then adjudicate the fixed eight formal samples; no extra samples or promotion')
    texts['m425_gate.py']=g
    for name in ('m425_timed_visual.py','m425_warm.py','m425_environment.py','m425_trials.py'):texts[name]=(HERE/name).read_text(encoding='utf-8')
    texts['m425_export.py']=(OLD/'m423_export.py').read_text(encoding='utf-8').replace('m423_integrated_video_01','m425_warm_performance_01').replace('integrated-fixed159-visual-language-quality','controlled-warm-complete-request-performance').replace('M423','M425')
    texts['run_m425.sh']=(OLD/'run_m423.sh').read_text(encoding='utf-8').replace('m423','m425').replace('M423','M425').replace('m425_integrated_video_01','m425_warm_performance_01')
    texts['m425_assemble.py']=(OLD/'m423_assemble.py').read_text(encoding='utf-8').replace('/home/ubuntu/m421_saved_feature_candidate_01','/home/ubuntu/m423_integrated_video_candidate_01').replace('fedbbf711ba0dbcb63fadf0ba5d234da0d53e795f16ad643a6de80a0997b95da',sha(OLD/'PACKAGE_MANIFEST.json')).replace('M423_ASSEMBLY_PASS','M425_ASSEMBLY_PASS')
    plan=json.loads((OLD/'PLAN.json').read_bytes());plan.update(performance_measurement=True,temperature_measurement_enabled=False,maximum_requests=12,integrated_visual_calls=12,integrated_language_calls=12)
    texts['PLAN.json']=encoded(plan).decode('utf-8')
    texts['WARM_PROTOCOL.json']=protocol.read_text(encoding='utf-8')
    texts['PERFORMANCE_PLAN.json']=encoded(dict(protocol_sha256=sha(protocol),integrated_numerical_result='/home/ubuntu/m423_integrated_video_01/BOARD_RESULT.json',integrated_numerical_sha256=prior['latest_m423_integrated_board']['sha256'])).decode('utf-8')
    PKG.mkdir()
    excluded={'m423_gate.py','m423_export.py','m423_assemble.py','run_m423.sh','PLAN.json','SHA256SUMS'}
    for row in m['files']:
        if row['path'] not in excluded:atomic(PKG/row['path'],(OLD/row['path']).read_bytes(),immutable=True)
    for name,text in texts.items():
        if name.endswith('.py'):ast.parse(text,feature_version=(3,10))
        atomic(PKG/name,text.encode('utf-8'),immutable=True)
    files=sorted(PKG.iterdir());atomic(PKG/'SHA256SUMS',''.join(f'{sha(p)}  {p.name}\n' for p in files).encode('ascii'),immutable=True)
    files=sorted(PKG.iterdir());manifest=dict(file_count=len(files),total_bytes=sum(p.stat().st_size for p in files),files=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in files]);atomic(PKG/'PACKAGE_MANIFEST.json',encoded(manifest),immutable=True)
    value=dict(status='PREPARED_M425_TEMPERATURE_FREE_WARM_PERFORMANCE',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),prerequisites=prior,file_count=manifest['file_count'],total_bytes=manifest['total_bytes'],board_run=False,performance_pass=False)
    value['preparation01_retained_reason']='Before any board work, full 12-sample duplicated retry records with pretty JSON could exceed the 4MiB collector limit. Compact lossless atomic JSON only; all numerical/timing fields unchanged.'
    out=BASE/'runs/M425-performance-preparation-02/RESULT.json';atomic(out,encoded(value),immutable=True)
    sync('latest_m425_performance_preparation',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=value['manifest_sha256']),f'## M425 两层视觉完整暖请求轻量包准备（2026-10-06）\n\nSHA {sha(out)}；manifest {value["manifest_sha256"]}；原stream计时、候选暂存/pack/parse全部计入，完整特征/logits/72KV计时后核对，12请求共用原七DMA；不读取温度。新协议固定四预热＋八正式，原源码/前级/Overlay预检和安全释放复用，累计事务独立分账；未上板或性能结论。先组件及回收检查再一次运行。')
    print('M425_PREPARATION_SYNC',sha(out),value['manifest_sha256'],manifest['file_count'],manifest['total_bytes'])
if __name__=='__main__':main()
