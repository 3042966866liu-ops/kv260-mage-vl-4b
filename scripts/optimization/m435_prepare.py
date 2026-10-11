"""Prepare exactly two B diagnostic requests; never run the old warm protocol."""
import ast
import json
from pathlib import Path
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
from m427_prepare import once

OLD = BASE / 'candidates/M433-late11-complete-request-warm-01'
PKG = BASE / 'candidates/M435-weight-read-observation-01'


def main():
    if (PKG/'PACKAGE_MANIFEST.json').exists():
        raise RuntimeError('Immutable packet exists')
    board = json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    prior = {k: board[k] for k in ('latest_m434_read_path_audit', 'latest_m432_integrated_board', 'latest_m433_warm_failure_interpretation')}
    for e in prior.values():
        assert sha(ROOT/e['result']) == e['sha256']
        assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
    audit = json.loads((ROOT/prior['latest_m434_read_path_audit']['result']).read_bytes())
    manifest = json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes())
    for r in manifest['files']:
        assert sha(OLD/r['path']) == r['sha256'] and (OLD/r['path']).stat().st_size == r['bytes']
    plan = json.loads((OLD/'PLAN.json').read_bytes())
    plan.update(performance_measurement=False, maximum_requests=2, integrated_visual_calls=2,
                integrated_language_calls=2, prerequisites=prior, request_boundary='Exactly BB diagnostic; all I/O retained, no warm/formal performance eligibility')
    files = [{'path': '/home/ubuntu/tellme_release_install_20260926/deployment/mage_vl4b/m181_m120_video_board_candidate/vision_layout/weights'+str(i)+'.bin', 'group': 'visual'} for i in range(4)]
    reads = []
    for r in audit['visual_windows']:
        reads.append(dict(group='visual', path=files[r['port']]['path'], offset=r['offset'], bytes=r['bytes'], layer=r['layer'], part=r['part']))
    for name, layout in audit['language_layouts'].items():
        group = 'language' if name == 'language' else 'head'
        remote = '/home/ubuntu/tellme_release_install_20260926/'+layout['remote']
        paths = [remote+'/'+r['path'] for r in layout['files']]
        files.extend(dict(path=p, group=group) for p in paths)
        c = json.loads((ROOT/layout['contract_path']).read_bytes())
        for chain in c['chains']:
            for port in range(4):
                reads.append(dict(group=group, path=paths[port], offset=chain['staged_base_words']*16,
                                  bytes=chain['staged_bytes_per_shard'], chain=chain['chain_index']))
    assert len(files) == 12 and len(reads) == 736
    assert all(0 < r['bytes'] <= 16 << 20 for r in reads)
    observation = dict(requests='BB', request_count=2, files=files, expected_reads=reads,
                       mincore_boundaries=['before-request','after-vision','after-language'],
                       storage_limit=None, performance_experiment=False, prior_audit_sha256=prior['latest_m434_read_path_audit']['sha256'])
    gate = (OLD/'m433_gate.py').read_text(encoding='utf-8').replace('m433_late11_warm_request_01', 'm435_weight_read_observation_01')
    gate = gate.replace('M433', 'M435').replace('controlled-warm-complete-request-performance', 'fixed-BB-file-IO-residency-diagnostic')
    gate = gate.replace('from m433_trials import run', 'from m435_trials import run').replace('from m433_export import emit_saved', 'from m435_export import emit_saved')
    gate = gate.replace('PASS_M435_CONTROLLED_WARM_MEASUREMENTS_COLLECTED', 'PASS_M435_BB_IO_DIAGNOSTIC')
    gate = once(gate, 'runtime = engine = base = lock = policy = None', 'runtime = engine = base = lock = policy = provider = None')
    gate = once(gate, "        result['integrated_sources_checked_before_overlay']=True", """        from m435_io_observer import linux_probe_fixture
        from test_m435_io_observer import ObserverTests
        import unittest,io
        test_log=io.StringIO()
        tests=unittest.TextTestRunner(stream=test_log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ObserverTests))
        result['observer_component_tests']=dict(run=tests.testsRun,skipped=len(tests.skipped),output=test_log.getvalue(),success=tests.wasSuccessful())
        if not tests.wasSuccessful() or tests.testsRun!=15 or tests.skipped:raise RuntimeError('Board CPU-only observer component rejected before resources')
        result['linux_residency_probe']=linux_probe_fixture(EVIDENCE)
        result['observer_checked_before_overlay']=True
        result['integrated_sources_checked_before_overlay']=True""")
    gate = once(gate, '        run(engine,runtime,policy,base,HERE,EVIDENCE,result,patch,features,provider)', """        from m435_io_observer import IOObserver
        observation=json.loads((HERE/'OBSERVATION_PLAN.json').read_bytes())
        observer=IOObserver({row['path']:row['group'] for row in observation['files']},engine.vision.store,result)
        with observer:
            run(engine,runtime,policy,base,HERE,EVIDENCE,result,patch,features,provider,observer)""")
    gate = once(gate, "                result['ps_slot_port_count_before_release']=len(slots)", """                if provider is not None and not provider.disposed:
                    provider.dispose()
                result['ps_slot_port_count_before_release']=len(slots)""")
    gate = gate.replace('Close exactly the saved fixed warm experiment; no extra requests, fitted threshold or production promotion', 'Interpret exactly two B file I/O/residency diagnostic requests; no performance or automatic rerun')
    gate = gate.replace('> 3000', '> 1200')
    trials = (OLD/'m433_trials.py').read_text(encoding='utf-8').replace('M433', 'M435')
    trials = trials.replace('from m425_warm import ORDER,WarmSequence', 'ORDER="BB"')
    trials = once(trials, 'def run(engine,runtime,policy,base,here,output,result,patch,features,provider):', 'def run(engine,runtime,policy,base,here,output,result,patch,features,provider,observer):')
    trials = once(trials, "        t=time.perf_counter();answer=provider(index,*a,**kw);stage_ms['vision']=(time.perf_counter()-t)*1000", """        observer.phase='vision'
        vision_io_before=observer_counters()
        t=time.perf_counter();answer=provider(index,*a,**kw);stage_ms['vision']=(time.perf_counter()-t)*1000
        phase_IO['vision']=observer_delta(vision_io_before,observer_counters())
        observer.phase='none'
        observer.snapshot('after-vision')""")
    trials = once(trials, "        t=time.perf_counter()\n        try:answer=original_prefill(hidden)", """        observer.phase='prefill'
        language_io_before=observer_counters()
        t=time.perf_counter()
        try:answer=original_prefill(hidden)""")
    trials = once(trials, "        stage_ms['prefill']=(time.perf_counter()-t)*1000;captured['output']=answer;return answer", """        stage_ms['prefill']=(time.perf_counter()-t)*1000
        phase_IO['prefill']=observer_delta(language_io_before,observer_counters())
        observer.phase='none'
        observer.snapshot('after-language')
        captured['output']=answer;return answer""")
    trials = once(trials, '    captured={};stage_ms={};index=0', '    from m435_io_observer import counters as observer_counters,delta as observer_delta\n    captured={};stage_ms={};phase_IO={};index=1')
    trials = once(trials, "    sequence=WarmSequence(result,reference_environment,protocol_sha=protocol_sha)", "    result['diagnostic_order']='BB';result['timings_not_performance']=True")
    trials = once(trials, "        sequence.before(n);index=0 if variant=='A' else 1", "        index=1;observer.request=n+1\n        observer.snapshot('before-request')\n        phase_IO.clear()")
    trials = once(trials, 'sample=dict(index=n+1,variant=variant,timing=', 'sample=dict(index=n+1,variant=variant,phase_IO=dict(phase_IO),timing=')
    trials = once(trials, '        sequence.record(sample)', "        observation=json.loads((here/'OBSERVATION_PLAN.json').read_bytes())\n        actual=[dict(group=r['group'],path=r['path'],offset=r['offset'],bytes=r['returned_bytes']) for r in observer.reads if r['request']==n+1]\n        expected=[{k:r[k] for k in ('group','path','offset','bytes')} for r in observation['expected_reads']]\n        if actual!=expected:raise RuntimeError('Actual 736 per-request file windows differ')")
    trials = trials.replace("result['all12_requests_completed']=True", "result['all2_requests_completed']=True")
    trials = trials.replace("result['performance_measurements_collected']=True", "result['performance_measurements_collected']=False")
    texts = {'m435_gate.py': gate, 'm435_trials.py': trials,
             'PLAN.json': encoded(plan).decode(), 'OBSERVATION_PLAN.json': encoded(observation).decode()}
    for name in ('m435_io_observer.py', 'test_m435_io_observer.py'):
        texts[name] = (HERE/name).read_text(encoding='utf-8')
    for old, new in (('m433_entry.py','m435_entry.py'),('m433_export.py','m435_export.py'),('run_m433.sh','run_m435.sh')):
        texts[new] = (OLD/old).read_text(encoding='utf-8').replace('M433','M435').replace('m433','m435').replace('m435_late11_warm_request_01','m435_weight_read_observation_01').replace('controlled-warm-complete-request-performance','fixed-BB-file-IO-residency-diagnostic')
    texts['m435_assemble.py'] = (OLD/'m433_assemble.py').read_text(encoding='utf-8').replace('/home/ubuntu/m432_late11_integrated_candidate_02', '/home/ubuntu/m433_late11_warm_candidate_01').replace('37579ee6572d076a547842ba868c04a3797dd2a0375724c2a6fce333a9b9a0ee', sha(OLD/'PACKAGE_MANIFEST.json')).replace('M433_ASSEMBLY_PASS','M435_ASSEMBLY_PASS')
    assert gate.index('observer_checked_before_overlay') < gate.index('import pynq')
    PKG.mkdir(parents=True,exist_ok=True)  # Incomplete unpublished staging; every existing byte still checked immutable.
    exclude = {'m433_gate.py','m433_trials.py','m433_entry.py','m433_export.py','m433_assemble.py','run_m433.sh','PLAN.json','SHA256SUMS','DEPENDENCY_CLOSURE.json'}
    for r in manifest['files']:
        if r['path'] not in exclude:
            atomic(PKG/r['path'], (OLD/r['path']).read_bytes(), immutable=True)
    for name, text in texts.items():
        if name.endswith('.py'):
            ast.parse(text, feature_version=(3,10))
        atomic(PKG/name, text.encode('utf-8'), immutable=True)
    deps = json.loads((OLD/'DEPENDENCY_CLOSURE.json').read_bytes())
    deps['files'] = {k: v for k,v in deps['files'].items() if k not in ('m433_gate','m433_trials','m433_entry','m433_export','m433_assemble')}
    deps['files'].update({Path(n).stem: sha(PKG/n) for n in texts if n.endswith('.py')})
    deps.update(missing=[], recursive_modules=len(deps['files']), derivation='Same-SHA frozen dependency closure, five roots replaced; observer only stdlib')
    atomic(PKG/'DEPENDENCY_CLOSURE.json', encoded(deps), immutable=True)
    atomic(PKG/'SHA256SUMS', ''.join(f'{sha(p)}  {p.name}\n' for p in sorted(PKG.iterdir())).encode(), immutable=True)
    files = sorted(PKG.iterdir())
    m = dict(file_count=len(files), total_bytes=sum(p.stat().st_size for p in files), files=[dict(path=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in files])
    atomic(PKG/'PACKAGE_MANIFEST.json', encoded(m), immutable=True)
    record = dict(status='PREPARED_M435_BB_NARROW_IO_SUPPORT_PENDING', manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
                  prerequisites=prior, file_count=m['file_count'], total_bytes=m['total_bytes'], fixed_requests='BB',
                  expected_physical=2135, extra_DMA=0, cache_eviction=False, numerical_reference_reused=True,
                  board_run=False, performance_pass=False, temperature_measurement_enabled=False)
    out = BASE/'runs/M435-IO-observation-preparation-01/RESULT.json'
    atomic(out, encoded(record), immutable=True)
    sync('latest_m435_IO_preparation',dict(status=record['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=record['manifest_sha256']),
         f'## M435 固定两个B窄I/O观察包准备（2026-10-07）\n\nSHA {sha(out)}，manifest {record["manifest_sha256"]}；每请求88视觉/648语言head原窗口read＋CPU decode，12文件三边界权限有效mincore。固定BB，不清缓存/不全缓存准入/无新性能；原数值、2135物理预期和原七DMA释放保持。探针/实际钩子组件在任何Overlay前执行；失败也dispose原provider仅安全状态释放。包未上传；后续先完整配套检查。')
    print('M435_PREPARATION_SYNC',sha(out),record['manifest_sha256'])


if __name__ == '__main__':
    main()
