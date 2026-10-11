"""Whitelist performance packet: only kernel variant changes, both visual B."""
import ast,json,shutil
import m351_workflow as w
from m441_host_io08 import atomic
from m441_prepare_layer09 import once,verify_package
OLD=w.BASE/'candidates/M437-late11-natural-IO-performance-01'
VIDEO=w.BASE/'candidates/M441-fixed-video-09'
PKG=w.BASE/'candidates/M441-complete-request-performance-09'
REMOTE='/home/ubuntu/m441_complete_request_candidate_09'
EVIDENCE='/home/ubuntu/m441_complete_request_evidence_09'

def main():
    if PKG.exists():raise RuntimeError('Immutable packet exists')
    verify_package(OLD);verify_package(VIDEO)
    board=json.loads((w.ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    prior={}
    for key in ('latest_m441_fixed_video_board','latest_m441_fixed_video_closure','latest_m441_complete_request_protocol','latest_m441_kernel_switch_component'):
        e=board[key];assert w.sha(w.ROOT/e['result'])==e['sha256']
        assert all(e['sha256'] in (w.ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
        prior[key]=e
    protocol=(w.ROOT/prior['latest_m441_complete_request_protocol']['result']).with_name('PROTOCOL.json')
    stage=w.ROOT/'tmp/m441_performance09/package_staging';stage.mkdir(parents=True,exist_ok=False)
    excluded={'PACKAGE_MANIFEST.json','SHA256SUMS','DEPENDENCY_CLOSURE.json','m437_gate.py','m437_trials.py','m437_entry.py','m437_export.py','m437_assemble.py','run_m437.sh','M357_COMPARE_PREREQUISITE.json','HARDWARE_CLOSURE.json','STAGE_PREREQUISITE.json','WARM_PROTOCOL.json','PERFORMANCE_PLAN.json'}
    for p in OLD.iterdir():
        if p.name not in excluded:shutil.copyfile(p,stage/p.name)
    for name in ('M441_COMPARE_PREREQUISITE.json','HARDWARE_CLOSURE.json','STAGE_PREREQUISITE.json'):shutil.copyfile(VIDEO/name,stage/name)
    shutil.copyfile(w.ROOT/prior['latest_m441_fixed_video_board']['result'],stage/'M441_VIDEO_PREREQUISITE.json')
    shutil.copyfile(w.HERE/'m441_kernel_switch09.py',stage/'m441_kernel_switch09.py')
    shutil.copyfile(protocol,stage/'WARM_PROTOCOL.json')
    perf=json.loads((OLD/'PERFORMANCE_PLAN.json').read_bytes());perf.update(protocol_sha256=w.sha(protocol),m441_video_sha256=prior['latest_m441_fixed_video_board']['sha256'])
    atomic(stage/'PERFORMANCE_PLAN.json',w.encoded(perf))
    gate=(OLD/'m437_gate.py').read_text(encoding='utf-8')
    for a,b in [('M437','M441P'),('m437_trials','m441_performance_trials'),('m437_export','m441_performance_export'),('/home/ubuntu/m437_natural_IO_result_01',EVIDENCE),('natural-IO-complete-request-performance','same-visual-kernel-complete-request-performance')]:gate=gate.replace(a,b)
    for a,b in [("Path('/home/ubuntu/m357_candidate_01')","Path('/home/ubuntu/m441_candidate_01')"),("CAND_SHA = '2e9cbd00d0d01edf05e171674f71f86a94ce389a0658ce6c5466cebb77220d18'","CAND_SHA = '56253626a550c9c1358e805e6e3ad9b8b03c2fd9c1ff048be87c64c9f04dd5a0'"),("PRIOR_SHA = 'ca35750d1b7043b76a16c75b97341616823137a58d91545576de0361a6ba3bde'","PRIOR_SHA = '0b416a17669ae1a5690a62650237ce6ced33f922017625f685401ca806e2273d'"),("'0x4D333537' if is_candidate","'0x4D343431' if is_candidate")]:gate=once(gate,a,b)
    gate=gate.replace('M357_COMPARE_PREREQUISITE.json','M441_COMPARE_PREREQUISITE.json').replace('PASS_M357_COMPARE','PASS_M441_COMPARE')
    gate=once(gate,"        if prior['status']!='PASS_INDEPENDENT_FIXED_TEXT_CAPACITY_AND_NUMERICS' or prior['raw_sha256']!='b7c2532715f6b90201c9c092e83bcf5245ad7e6ad0b3e5d9bdace60618406ebb':raise RuntimeError('Independent text prerequisite differs')","        if sha256(HERE/'STAGE_PREREQUISITE.json')!='0562c15fd56f185a98f2ee8c169ab4bd2939abfb0ec482ec7126fbd5bf53abc7' or prior['status']!='PASS_M441T_FIXED_TEXT_DIAGNOSTIC' or not prior['numerical_pass'] or not prior['safe_buffers_released']:raise RuntimeError('M441 text prerequisite differs')")
    guard="        saved=verify_complete_numerical(perf_plan)"
    new=guard+"\n        video_raw=HERE/'M441_VIDEO_PREREQUISITE.json'\n        video_proof=json.loads(video_raw.read_bytes())\n        if sha256(video_raw)!=perf_plan['m441_video_sha256'] or video_proof['status']!='PASS_M441V_INTEGRATED_VIDEO_NUMERICAL' or not video_proof['numerical_pass'] or not video_proof['safe_buffers_released'] or video_proof['unsafe_buffers_retained']:raise RuntimeError('Actual M441 full video prerequisite differs')\n        result['m441_video_numerical_source_sha256']=perf_plan['m441_video_sha256']"
    gate=once(gate,guard,new)
    anchor='        run(engine,runtime,policy,base,HERE,EVIDENCE,result,patch,features,provider)'
    switch='''        from m441_kernel_switch09 import KernelSwitch
        def switch_environment(variant,index):
            target=Path('/home/ubuntu/m357_candidate_01') if variant=='A' else CANDIDATE
            expected='2e9cbd00d0d01edf05e171674f71f86a94ce389a0658ce6c5466cebb77220d18' if variant=='A' else CAND_SHA
            verified=verify_frozen_package(target,expected)
            record=EVIDENCE/('switch_'+str(index)+'_'+variant+'_environment.json')
            cp=subprocess.run([sys.executable,'-B',str(reuse/'m120_board_env_preflight.py'),'--candidate',str(target),'--expected-package-manifest-sha256',expected,'--result',str(record)],timeout=90)
            if cp.returncode:raise RuntimeError('Switch environment rejected before Overlay')
            result.setdefault('kernel_switch_environment',[]).append(dict(index=index,variant=variant,manifest_sha256=expected,environment_sha256=sha256(record),package_identity=verified))
            return str(target/'overlay/m120_m89x2_t32.bit')
        switch=KernelSwitch(runtime,policy,base,result,enabled=True,load_overlay=pynq.Overlay,environment=switch_environment,patch=patch,video_server=video_server,packet=packet,golden=golden)
        run(engine,runtime,policy,base,HERE,EVIDENCE,result,patch,features,provider,switch)
'''
    gate=once(gate,anchor,switch.rstrip())
    gate=once(gate,"result['fpga_transactions']=(1 if policy is not None and policy.ever else 0)+", "result['fpga_transactions']=(1 if policy is not None and policy.ever else 0)+result.get('kernel_switch_minimal_attempts',0)+")
    gate=gate.replace('saved-feature-language-original-then-layers13-23','same-late11-two-kernels-full-request')
    trials=(OLD/'m437_trials.py').read_text(encoding='utf-8').replace('M437','M441P')
    trials=once(trials,'features,provider):','features,provider,switch):')
    trials=once(trials,"sequence.before(n);index=0 if variant=='A' else 1","sequence.before(n);index=1\n        switch.select(variant,n+1)\n        expected_build='0x4D333537' if variant=='A' else '0x4D343431'")
    trials=once(trials,"semantic=validate_request_stream(events,after_cache,'0x4D333537')","semantic=validate_request_stream(events,after_cache,expected_build)")
    trials=once(trials,"snapshot['ap_return']!=0x4d333537","snapshot['ap_return']!=int(expected_build,16)")
    trials=once(trials,'sample=dict(index=n+1,variant=variant,timing=',"sample=dict(index=n+1,variant=variant,kernel_build=expected_build,timing=")
    for name,text in {'m441_performance_gate.py':gate,'m441_performance_trials.py':trials,'m441_performance_entry.py':(OLD/'m437_entry.py').read_text().replace('m437_gate.py','m441_performance_gate.py'),'m441_performance_export.py':(OLD/'m437_export.py').read_text().replace('M437','M441P').replace('/home/ubuntu/m437_natural_IO_result_01',EVIDENCE).replace('natural-IO-complete-request-performance','same-visual-kernel-complete-request-performance'),'run_m441_performance.sh':(OLD/'run_m437.sh').read_text().replace('M437','M441P').replace('m437_entry.py','m441_performance_entry.py').replace('m437_export.py','m441_performance_export.py').replace('/home/ubuntu/m437_natural_IO_result_01',EVIDENCE)}.items():
        if name.endswith('.py'):ast.parse(text,feature_version=(3,10))
        atomic(stage/name,text.encode('utf-8'))
    assembly=(VIDEO/'m441_video_assemble.py').read_text(encoding='utf-8')
    at=' source[sha(saved_text)]=saved_text'
    extra="\n old4=Path('/home/ubuntu/m437_natural_IO_candidate_01')\n if sha(old4/'PACKAGE_MANIFEST.json')!='"+w.sha(OLD/'PACKAGE_MANIFEST.json')+"':raise RuntimeError('Actual M437 package differs')\n source.update({r['sha256']:old4/r['path'] for r in json.loads((old4/'PACKAGE_MANIFEST.json').read_bytes())['files']})\n saved_video=Path('/home/ubuntu/m441_fixed_video_evidence_09/BOARD_RESULT.json')\n if sha(saved_video)!='"+perf['m441_video_sha256']+"':raise RuntimeError('Actual saved video differs')\n source[sha(saved_video)]=saved_video\n"
    assembly=once(assembly,at,at+extra).replace('M441V','M441P')
    assert '/home/ubuntu/m437_natural_IO_candidate_01' in (w.HERE/'m437_control03.ps1').read_text(encoding='utf-8-sig')
    atomic(stage/'m441_performance_assemble.py',assembly.encode('utf-8'))
    assert gate.index('Actual M441 full video prerequisite differs')<gate.index("patch(pynq,'Overlay'")
    assert (stage/'m431_borrowed_visual.py').read_bytes()==(OLD/'m431_borrowed_visual.py').read_bytes()
    assert trials.index('switch.select')<trials.index("print(f'M441P_REQUEST_BEGIN")
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(stage.iterdir())]
    atomic(stage/'SHA256SUMS',''.join(x['sha256']+'  '+x['path']+'\n' for x in rows).encode('ascii'));rows.append(dict(path='SHA256SUMS',bytes=(stage/'SHA256SUMS').stat().st_size,sha256=w.sha(stage/'SHA256SUMS')))
    atomic(stage/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='m441-performance-v09',files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))))
    verify_package(stage);stage.rename(PKG)
    ctl=(w.HERE/'m441_video_control09.ps1').read_text(encoding='utf-8')
    for a,b in [('fixed-video','complete-request-performance'),('FIXED_VIDEO','PERFORMANCE'),('m441_video','m441_performance'),('m441_fixed_video','m441_complete_request'),('M441V','M441P')]:ctl=ctl.replace(a,b)
    ctl=ctl.replace('M432-late11-integrated-video-02/PACKAGE_MANIFEST.json','M437-late11-natural-IO-performance-01/PACKAGE_MANIFEST.json')
    ctl=ctl.replace("'0562c15fd56f185a98f2ee8c169ab4bd2939abfb0ec482ec7126fbd5bf53abc7'","'0562c15fd56f185a98f2ee8c169ab4bd2939abfb0ec482ec7126fbd5bf53abc7','"+perf['m441_video_sha256']+"'")
    ctl=ctl.replace('-TimeoutSeconds 1500 -MarkerPrefix','-TimeoutSeconds 5100 -MarkerPrefix')
    ctl=ctl.replace('/home/ubuntu/m441_complete_request_candidate_09',REMOTE)
    atomic(w.HERE/'m441_performance_control09.ps1',ctl.encode('utf-8'),immutable=True)
    out=w.BASE/'runs/M441-complete-request-preparation-09';r=dict(status='PREPARED_M441_COMPLETE_REQUEST_PERFORMANCE09',manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),prerequisites=prior,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows),maximum_requests=12,expected_physical=12813,same_visual_policy=True,board_executed=False,performance_pass=False)
    atomic(out/'RESULT.json',w.encoded(r),immutable=True);d=w.sha(out/'RESULT.json')
    w.sync('latest_m441_complete_request_preparation',dict(status=r['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=d,manifest_sha256=r['manifest_sha256']),f'## M441 完整请求隔离包准备09（2026-10-09）\n\nSHA {d}，双方同后11层视觉；A原M357/B新M441只变核，切换前后环境/七owner/全minimal在计时外。固定4＋8及12813物理，计时后全数值；原stream、原数学和借用生命周期保持。只有包，尚未支持/上传/性能。')
    print(r['status'],d,r['manifest_sha256'])

if __name__=='__main__':main()
