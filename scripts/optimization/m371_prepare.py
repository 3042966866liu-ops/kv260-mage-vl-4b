"""Freeze one candidate-only diagnostic, reusing verified numerical/hardware gates."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from contextlib import nullcontext
import numpy as np
import m351_workflow as w

OLD=w.BASE/'candidates/M369-light-video-01'
PKG=w.BASE/'candidates/M371-candidate-prefill-profile-01'
OUT=w.BASE/'runs/M371-candidate-profile-preparation-01'


def once(s,old,new):
    if s.count(old)!=1:raise RuntimeError('Replacement identity/count differs: '+old[:80])
    return s.replace(old,new)


def tests():
    sys.path.insert(0,str(PKG))
    try:
        import m371_prefill_diagnostic as diagnostic
        import m371_profile_summary as summary
        import test_prefill_diagnostic as fixture
        base=fixture.SimpleNamespace(chain_window=lambda:None,copy_window_to_buffer=lambda:None,wait_transaction=lambda:None)
        runtime=fixture.Runtime(base);model=fixture.Model(runtime)
        d=diagnostic.PrefillDiagnostic(model,runtime,base,transfer_instrumenter=lambda *a:nullcontext())
        original=model.prefill
        called=[]
        def outer(x):called.append(1);return d.prefill(x)
        model.prefill=outer
        hidden=np.arange(159*2560,dtype=np.float32).reshape(159,2560)
        answer=model.prefill(hidden)
        assert len(called)==1 and answer is model.returned
        assert '_family' not in vars(model) and '_stage' not in vars(runtime)
        report=d.finalize();s=summary.summarize(report)
        assert s['main_thread_closure_error_ns']==0 and s['counter_delta']['logical_calls']==1
        assert s['background_exclusive_s_do_not_add'] and not s['cross_thread_addition_allowed']
        packed=summary.pack(report);decoded,raw=summary.unpack(packed)
        assert decoded==report and summary.summarize(decoded)==s
        failures=[]
        for label in ('exclusive','open','parent','root','failed','input'):
            value=copy.deepcopy(report)
            if label=='exclusive':value['trace']['events'][0]['exclusive_ns']+=1
            elif label=='open':value['trace']['events'][0]['end_ns']=None
            elif label=='parent':value['trace']['events'][0]['parent']=999999
            elif label=='root':value['trace']['events'][0]['name']='wrong'
            elif label=='failed':value['trace']['events'][0]['failed']=True
            else:value['input_shape']=[30,2560]
            try:summary.summarize(value)
            except RuntimeError:failures.append(label)
            else:raise AssertionError('Invalid trace accepted: '+label)
        for label in ('sha','length','encoding'):
            value=dict(packed)
            value[{'sha':'raw_sha256','length':'raw_bytes','encoding':'encoding'}[label]]={'sha':'0'*64,'length':1,'encoding':'bad'}[label]
            try:summary.unpack(value)
            except RuntimeError:failures.append(label)
            else:raise AssertionError('Invalid compression accepted')
        model.prefill=original
        # Run the existing component tests against the newly pinned-call adapter.
        fixture.PrefillDiagnostic=diagnostic.PrefillDiagnostic
        import unittest
        result=unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(fixture.PrefillTests))
        assert result.wasSuccessful() and result.testsRun==3
        return dict(checks=['pinned original prefill prevents outer timer recursion','actual threaded fake model return unchanged',
            'instance/global callbacks restored','exclusive main time closes exactly','worker costs kept separate',
            'bounded full trace compression and SHA roundtrip','three original adapter success/failure/bound tests'],negative_checks=failures,
            fake_model_MMIO_memory=True,hardware_proof=False)
    finally:sys.path.remove(str(PKG))


def main():
    if PKG.exists():raise RuntimeError('Immutable package exists; do not repeat preparation')
    oldmanifest=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    assert w.sha(OLD/'PACKAGE_MANIFEST.json')=='dc22fc6c4e8718832877640f7cd768dda12bf63c8e057239ad1fa902295fdd73'
    for r in oldmanifest['files']:assert w.sha(OLD/r['path'])==r['sha256']
    closure=json.loads((OLD/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    release=w.ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    for r in closure['files']:assert w.sha(release/r['path'])==r['sha256']
    hw=json.loads((OLD/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))
    for r in hw['prerequisites']:assert w.sha(w.ROOT/r['path'])==r['sha256']
    prior=w.BASE/'runs/M369-light-video-closure-01/RESULT.json';p=json.loads(prior.read_text(encoding='utf-8'))
    assert p['numerical_pass'] and p['performance_pass'] and w.sha(prior)=='812c8aa7587d8bc12d57a1d0df891a9bf784d583121b9a3b00305673e13525f3'
    for name in ['CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json']:assert w.sha(prior) in (w.ROOT/name).read_text(encoding='utf-8-sig')
    PKG.mkdir()
    excluded={'PACKAGE_MANIFEST.json','SHA256SUMS','run_m369_light_video.sh','m369_export_result.py','m369_assemble.py','m369_trials.py','m369_light_video_gate.py'}
    for row in oldmanifest['files']:
        if row['path'] not in excluded:shutil.copyfile(OLD/row['path'],PKG/row['path'])
    for name in ['transfer_trace.py','decode_trace.py','decode_io_trace.py','m371_profile_summary.py']:shutil.copyfile(w.HERE/name,PKG/name)
    adapter=(w.HERE/'prefill_diagnostic.py').read_text(encoding='utf-8')
    adapter=once(adapter,'self.model, self.runtime, self.base = model, runtime, base_module','self.model, self.runtime, self.base = model, runtime, base_module\n        self.original_prefill = model.prefill')
    adapter=once(adapter,'self.model.prefill.__func__.__module__','self.original_prefill.__func__.__module__')
    adapter=once(adapter,'result = self.model.prefill(hidden)','result = self.original_prefill(hidden)')
    w.atomic(PKG/'m371_prefill_diagnostic.py',adapter.encode())
    trials=(OLD/'m369_trials.py').read_text(encoding='utf-8')
    trials=once(trials,"ORDER='ABBABAAB'","ORDER='B'")
    trials=once(trials,'captured={};stage_ms={};original_prefill=engine.language.prefill;',
        'from m371_prefill_diagnostic import PrefillDiagnostic\n    from decode_io_trace import DecodeIOTrace\n    from m371_profile_summary import summarize,pack\n    diagnostic=PrefillDiagnostic(engine.language,runtime,base,trace_factory=DecodeIOTrace)\n    captured={};stage_ms={};original_prefill=diagnostic.prefill;')
    trials=once(trials,'        e=runtime.evidence()',
        "        profile=diagnostic.finalize()\n        result['candidate_prefill_profile']=summarize(profile)\n        result['packed_prefill_trace']=pack(profile)\n        e=runtime.evidence()\n        result['original_full_profile_counters']=e")
    trials=trials.replace('M369','M371').replace('all8_requests_completed','bounded_request_completed').replace('performance_measurements_collected','profile_measurements_collected')
    trials=once(trials,"result['measurement_scope']='Preloaded original request, original timers, warm original PS code cache; initialization and all SHA validation outside request'",
        "result['measurement_scope']='One candidate fixed159 instrumented Prefill; PS visual cache warm, natural files; excludes loading/vision; not a new performance comparison'")
    w.atomic(PKG/'m371_trials.py',trials.encode())
    gate=(OLD/'m369_light_video_gate.py').read_text(encoding='utf-8').replace('M369','M371').replace('m369','m371')
    gate=once(gate,'is_candidate=False  # Stable is always the first member of ABBABAAB','is_candidate=True  # One already-verified parallel candidate, no prefetch')
    gate=gate.replace('balanced-fixed159-video-light-performance','candidate-fixed159-prefill-cost-diagnostic').replace('PASS_M371_LIGHT_VIDEO_MEASUREMENTS','PASS_M371_CANDIDATE_PROFILE')
    gate=gate.replace("result['build_id']='0x4D395832/0x4D333537'","result['build_id']=TARGET_BUILD")
    gate=gate.replace('Adjudicate all8 original full-request times and order variability; no automatic promotion','Attribute candidate exposed preparation/device/PS time; no automatic optimization/promotion')
    # Keep the prior sparse policy bytes; this experiment changes observations only.
    gate=gate.replace('from m371_light_policy import StagePolicy','from m369_light_policy import StagePolicy')
    gate=gate.replace('M371_LIGHT_VIDEO','M371_CANDIDATE_PROFILE')
    w.atomic(PKG/'m371_light_video_gate.py',gate.encode())
    export=(OLD/'m369_export_result.py').read_text(encoding='utf-8').replace('M369','M371').replace('m369','m371').replace('balanced-fixed159-video-light-performance','candidate-fixed159-prefill-cost-diagnostic')
    w.atomic(PKG/'m371_export_result.py',export.encode())
    runner=(OLD/'run_m369_light_video.sh').read_text(encoding='utf-8').replace('M369','M371').replace('m369','m371').replace('M371_ENABLE_LIGHT_VIDEO','M371_ENABLE_CANDIDATE_PROFILE')
    w.atomic(PKG/'run_m371_light_video.sh',runner.encode())
    assembly=(OLD/'m369_assemble.py').read_text(encoding='utf-8').replace('M369','M371').replace("'/home/ubuntu/m368_staged_video_candidate_03'","'/home/ubuntu/m369_light_video_candidate_01'").replace('f5937684306cd0ce40683a9bc46097b69cc7a9c7625bf208883eaada8071fb66',w.sha(OLD/'PACKAGE_MANIFEST.json'))
    w.atomic(PKG/'m371_assemble.py',assembly.encode())
    checks=tests()
    for path in PKG.glob('*.py'):ast.parse(path.read_text(encoding='utf-8'),feature_version=(3,10))
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(PKG.iterdir())]
    w.atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode())
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=w.sha(PKG/'SHA256SUMS')))
    w.atomic(PKG/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='m371-candidate-prefill-cost-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    assert not list(PKG.rglob('__pycache__')) and not list(PKG.rglob('*.pyc'))
    r=dict(status='PASS_OFFLINE_CANDIDATE_PROFILE_PREPARATION',manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),
        prior_performance_sha256=w.sha(prior),checks=checks,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows),
        python310_syntax=True,same_sha_hardware_evidence_reused=True,build_id='0x4D333537',order='B',
        frozen_source_count=len(closure['files']),explicit_extra_cma_allocations=0,prefetch_enabled=False,
        existing_candidate_cost_breakdown_available=False,existing_M369_detailed_counters_not_saved=True,
        diagnostic_request_count=1,expected_logical_calls=778,expected_physical_calls=781,
        minimal_physical_calls=1,expected_total_physical_calls=782,
        board_run=False,new_performance_pass=False,formal_promotion_allowed=False,
        next_step='COM3 shell and sudo; manifest-first transfer and same-terminal environment; execute one candidate request, strict packed full-trace recovery, then exclusive attribution. No prefetch or new circuit.')
    w.atomic(OUT/'RESULT.json',w.encoded(r),immutable=True);digest=w.sha(OUT/'RESULT.json')
    w.atomic(OUT/'REPORT.md',('# M371 候选耗时诊断准备\n\n已有M369保留总计时，未保存内部phase/read/copy/wait字段；旧M339仅稳定核，不能代入。\n\n新包仅一次候选0x4D333537固定159请求，原缓存预热；不启用预取、不改电路。复用M339逐线程独占计时及pinned transfer AST，修正外层计时hook下的prefill绑定以避免递归。PS读/复制/同步、激活/尺度/打包、等待、解析与Attention分开，完整trace有界压缩并SHA保存。\n\n'+json.dumps(r,ensure_ascii=False,indent=2)+'\n').encode(),immutable=True)
    w.sync('latest_m371_candidate_profile_preparation',dict(status=r['status'],sha256=digest,result=(OUT/'RESULT.json').relative_to(w.ROOT).as_posix(),manifest_sha256=r['manifest_sha256'],board_run=False,performance_pass=False),
        f'## M371 候选版暴露耗时诊断准备（2026-10-02）\n\n候选0x4D333537；M369的约65.57s只含Prefill总计时，未保存内部phase，不能套用M339稳定占比。一个固定159请求、778逻辑/781物理加1合法minimal，复用已过同SHA硬件/数值；主线程独占闭合、后台不相加、完整trace有界压缩及SHA。离线回调/线程/归因负例通过；无额外CMA、预取关闭、未上板。准备证据SHA `{digest}`；manifest `{r["manifest_sha256"]}`。下一步COM3恢复后单次候选画像；生产准入/RSS收尾仍独立，不否定M369净收益。')
    print(json.dumps(dict(status=r['status'],sha256=digest,manifest_sha256=r['manifest_sha256'],files=len(rows),bytes=r['total_bytes'])))


if __name__=='__main__':main()
