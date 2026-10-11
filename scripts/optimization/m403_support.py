"""Actual new trials/frozen stream and strict saved-result negative checks."""
import ast
import base64
import copy
import hashlib
import importlib.util
import inspect
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m403_prepare import PKG,OLD,once

PS=Path(r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe')


def expected_scope():
    return json.loads((BASE/'runs/M402-tail-video-board-01/BOARD_RESULT.json').read_bytes())['tail_scope']


def count_checks():
    from test_m402_count_scope import Tests,server
    from m403_timed_count_scope import TimedVideoCountScope
    test=Tests();srv,e,stream,req=test.case();original=srv.expected_physical_calls
    scope=TimedVideoCountScope(srv,lambda:True,enabled=True)
    iterator=stream(e,req);seen=[]
    for event,payload in iterator:
        seen.append(event)
        if event=='complete':
            assert scope.closed and srv.expected_physical_calls is original
            assert payload['proof']['expected_pl_logical_chain_calls']==766
    assert seen[-1]=='complete' and scope.called==1
    # Invalid inputs, thread, source, ownership and reentry remain fail-closed.
    import test_m402_count_scope as old
    saved=old.VideoCountScope;old.VideoCountScope=TimedVideoCountScope
    class Derived(old.Tests):
        def test_actual_stream_candidate_proof_and_restore(self):pass
        def test_other_inputs_default_off_and_reentry_refused(self):
            s=server();original=s.expected_physical_calls
            with self.assertRaises(RuntimeError):TimedVideoCountScope(s,lambda:True)
            obj=TimedVideoCountScope(s,lambda:True,enabled=True)
            for args in ((30,1),(159,2),(True,1),(159,True)):
                with self.assertRaises(RuntimeError):s.expected_physical_calls(*args)
            self.assertEqual(s.expected_physical_calls(159,1),766)
            self.assertIs(s.expected_physical_calls,original)
            self.assertEqual(s.expected_physical_calls(159,1),778)
            with self.assertRaises(RuntimeError):obj.count(159,1)
            obj.close()
        def test_unsafe_missing_call_or_foreign_binding_blocks_close(self):
            s=server();live=[True];obj=TimedVideoCountScope(s,lambda:live[0],enabled=True)
            with self.assertRaises(RuntimeError):obj.close()
            live[0]=False
            with self.assertRaises(RuntimeError):s.expected_physical_calls(159,1)
            assert not obj.closed and obj.called==0
            live[0]=True;s.expected_physical_calls(159,1)
            assert obj.closed
        def test_cross_thread_refused(self):
            s=server();obj=TimedVideoCountScope(s,lambda:True,enabled=True);errors=[]
            import threading
            def call():
                try:s.expected_physical_calls(159,1)
                except RuntimeError:errors.append('refused')
            t=threading.Thread(target=call);t.start();t.join();self.assertEqual(errors,['refused'])
            s.expected_physical_calls(159,1);self.assertTrue(obj.closed)
    try:
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(Derived)
        result=unittest.TextTestRunner(verbosity=1).run(suite)
        assert result.wasSuccessful()
    finally:old.VideoCountScope=saved
    return result.testsRun


def adapt_harness(h):
    h=h.replace('from m393_silu_scope import RetainedTailOwnerError','from m401_prefill_tail_scope import RetainedTailOwnerError').replace('from m394_collect import expected_scope','from m403_support import expected_scope')
    h=once(h,'self.model=model;scope_calls.append(\'init\')',"self.model=model;scope_calls.append('init');assert kw['tokens']==159")
    h=once(h,"assert flag['request_active'];scope_calls.append('bind')","assert flag['request_active'];scope_calls.append('bind');flag['candidate']=True")
    h=once(h,"ref=copy.deepcopy(expected)","ref=copy.deepcopy(expected)\n            candidate_ref=json.loads((old/'VIDEO_EXPECTED.json').read_bytes())['candidate']")
    h=once(h,"(root/'VIDEO_EXPECTED.json').write_text(json.dumps(dict(baseline=ref)),encoding='utf-8')", "candidate_ref.update({k:ref[k] for k in ('input','logits','keys','values')})\n            (root/'VIDEO_EXPECTED.json').write_text(json.dumps(dict(baseline=ref,candidate=candidate_ref)),encoding='utf-8')")
    h=once(h,"row=copy.deepcopy(ref if flag['timed'] or requests else ref)","current=candidate_ref if flag.get('candidate') else ref\n                    row=copy.deepcopy(current)")
    h=h.replace("scale_retry_count=ref['retry_count'],pipeline_retry_launches=ref['retry_launches'],fused_nonfinite_detections=ref['nonfinite_detections']","scale_retry_count=current['retry_count'],pipeline_retry_launches=current['retry_launches'],fused_nonfinite_detections=current['nonfinite_detections']")
    h=once(h,"result['transactions']=[{'method':'head-original-execute' if i>=773 else '_launch_once'} for i in range(781)]", "calls=767 if flag.get('candidate') else 781\n                    result['transactions']=[{'method':'head-original-execute' if i>=calls-8 else '_launch_once'} for i in range(calls)]")
    h=once(h,"server=N(BUILD_ID='0x4D395832',KERNEL=ref['semantic']['proof']['kernel'],expected_physical_calls=lambda *a:778)","from test_m402_count_scope import server as frozen_server\n            server=frozen_server();server_original=server.expected_physical_calls;server.KERNEL=ref['semantic']['proof']['kernel'];video._server=server")
    h=once(h,"flag['timed']=False;flag['request_active']=True","flag['timed']=False;flag['request_active']=True;flag['candidate']=False")
    h=h.replace("result['fpga_transactions_total']==6256","result['fpga_transactions_total']==6200").replace('778logical781physical8head each trial','A778/781 and B766/767 with8head each trial')
    h=once(h,"and not result['retained_tail_scope']","and not result['retained_tail_scope'] and not result['retained_count_scope']\n                    assert server.expected_physical_calls(159,1)==778")
    h=once(h,"registry.entries.clear();patches.clear();visual[0,0]=0","registry.entries.clear();patches.clear();visual[0,0]=0\n                    # Explicit fake fixture disposal only; production failures retain owners.\n                    server.expected_physical_calls=server_original")
    return h


def trial_checks():
    import m395_support
    fn=inspect.getsource(m395_support.trial_checks)
    fn=fn.replace('m395','m403').replace('M395','M403').replace('silu-performance','tail-performance').replace('SiluLayerScope','LastLayerTailScope').replace('RetainedSiluOwnerError','RetainedTailOwnerError').replace('retained_SiLU_scope','retained_tail_scope')
    fn=once(fn,"    ns=dict(__name__='m403_trial_fixture'","    h=adapt_harness(h)\n    ns=dict(__name__='m403_trial_fixture'")
    fn=fn.replace("assert \"unsafe=unsafe or result.get('retained_tail_scope',False)\" in gate","assert \"unsafe=unsafe or result.get('retained_tail_scope',False) or result.get('retained_count_scope',False)\" in gate")
    ns=dict(globals());exec(compile(fn,'<actual-M403-trials-harness>','exec'),ns)
    return ns['trial_checks']()


def export(r):
    raw=encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    return 'M403_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM403_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M403_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(v).decode()+'\n' for i,v in enumerate(parts))+f'M403_DONE case=B1 gate_rc={r["gate_return_code"]} export_rc=0\n'


def collector_checks():
    import m403_collect as c
    from m403_prepare import SCOPE
    numeric=json.loads((BASE/'runs/M402-tail-video-board-01/BOARD_RESULT.json').read_bytes())
    refs=json.loads((PKG/'VIDEO_EXPECTED.json').read_bytes())
    # Explicit synthetic timings/records from the old saved measurement schema.
    r=json.loads((BASE/'runs/M395-silu-performance-board-01/BOARD_RESULT.json').read_bytes())
    r.update(status='PASS_M403_LIGHT_VIDEO_MEASUREMENTS',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),gate_level=SCOPE,tail_video_prerequisite_sha256=sha(BASE/'runs/M402-tail-video-board-01/BOARD_RESULT.json'),ps_prefetch_enabled=False,silu_workspace_enabled=False,tail_candidate_enabled='B only',source_precheck_before_hardware_import=numeric['source_precheck_before_hardware_import'],count_source_precheck=numeric['count_source_precheck'])
    for s in r['samples']:
        exp=refs['candidate' if s['variant']=='B' else 'baseline']
        s['tail_scope']=dict(expected_scope(),scope_weakref_dead=True) if s['variant']=='B' else dict(enabled=False,original_full_final_layer=True,extra_dma_allocations=0)
        s['count_scope']=dict(numeric['count_scope'],closed_inside_original_total_timer=True,scope_weakref_dead=True) if s['variant']=='B' else dict(enabled=False,original_expected=778,binding_unchanged=True)
        s['semantic']=exp['semantic'];s['counts']={k:exp[k] for k in s['counts']}
        s['scale_attempts_sha_after_timer']=hashlib.sha256(json.dumps(exp['scale_attempts'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        s['retry_records']=[a for a in exp['scale_attempts'] if len(a['attempted_shifts'])>1]
    r['fpga_transactions_total']=6200
    assert c.decode(export(r))[2]==r
    bad=[]
    for k,v in [('tail_video_prerequisite_sha256','bad'),('source_precheck_before_hardware_import',{}),('count_source_precheck',{}),('ps_prefetch_enabled',True),('silu_workspace_enabled',True),('tail_candidate_enabled',False),('order','ABABABAB'),('model_forward_calls',7),('safe_buffers_released',False),('fpga_transactions_total',1),('performance_pass',True),('manifest_sha256','bad'),('gate_return_code',True)]:
        q=copy.deepcopy(r);q[k]=v;bad.append(export(q))
    for kind in ('scope','count','owner','parser','patch','numeric','counter','retry','timer','cache','busy','baseline'):
        q=copy.deepcopy(r);s=q['samples'][1]
        if kind=='scope':s['tail_scope']['selected'][0]['token_count']=1
        elif kind=='count':s['count_scope']['closed_inside_original_total_timer']=False
        elif kind=='owner':s['count_scope']['scope_weakref_dead']=False
        elif kind=='parser':s['parser_scope']['parse_workers']=2
        elif kind=='patch':s['restored_owner_patch_count']=4
        elif kind=='numeric':s['numeric_sha_after_timer']['logits']['sha256']='bad'
        elif kind=='counter':s['counts']['logical_calls']=778
        elif kind=='retry':s['retry_records']=[]
        elif kind=='timer':s['timing']['stages_ms']['head']=s['timing']['stages_ms']['prefill']+1
        elif kind=='cache':s['after_cache']['cache_misses']=27
        elif kind=='busy':s['final_snapshot']['mm2s_dmasr']=4096
        elif kind=='baseline':q['samples'][0]['count_scope']['original_expected']=766
        bad.append(export(q))
    text=export(r);chunks=[x for x in text.splitlines(True) if 'RESULT_CHUNK' in x]
    bad += [text+chunks[0],text.replace(chunks[1],''),text.replace('CHUNK=1/','CHUNK=0/'),text.replace('export_rc=0','export_rc=1')]
    for log in bad:
        try:c.decode(log)
        except (ValueError,RuntimeError,KeyError,TypeError):pass
        else:raise AssertionError('Invalid performance evidence accepted')
    # Test actual atomic destination and synchronization key/order, without writes.
    original=(c.w.atomic,c.w.sync,c.decode);actions=[]
    try:
        c.decode=lambda _:('0'*64,b'explicit-fake-result',r)
        c.w.atomic=lambda path,*a,**kw:actions.append(('atomic',path.relative_to(ROOT).as_posix(),kw))
        c.w.sync=lambda key,*a:actions.append(('sync',key))
        from contextlib import redirect_stdout
        import io
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp/m403') as d:
            path=Path(d)/'saved.log';path.write_text('fake',encoding='utf-8')
            with redirect_stdout(io.StringIO()):c.collect(path)
        assert actions[0][0:2]==('atomic','deployment/mage_vl4b/optimization_v1/runs/M403-tail-performance-board-01/BOARD_RESULT.json') and actions[0][2]['immutable']
        assert actions[1]==('sync','latest_m403_tail_performance_board')
    finally:c.w.atomic,c.w.sync,c.decode=original
    return len(bad)


def assembly_checks():
    spec=importlib.util.spec_from_file_location('m403_actual_assembly',PKG/'m403_assemble.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    assert m.OLD.as_posix()=='/home/ubuntu/m395_silu_performance_candidate_01' and m.OLD_SHA==sha(OLD/'PACKAGE_MANIFEST.json')
    manifest=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes());prior={r['path']:r for r in json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes())['files']};delta=[r['path'] for r in manifest['files'] if prior.get(r['path'])!=r]
    root=ROOT/'tmp/m403';root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as d:
        previous=Path(d)/'old';dest=Path(d)/'new';previous.mkdir();dest.mkdir()
        shutil=__import__('shutil')
        for row in json.loads((OLD/'PACKAGE_MANIFEST.json').read_bytes())['files']:shutil.copyfile(OLD/row['path'],previous/row['path'])
        shutil.copyfile(OLD/'PACKAGE_MANIFEST.json',previous/'PACKAGE_MANIFEST.json')
        for n in ['PACKAGE_MANIFEST.json']+delta:shutil.copyfile(PKG/n,dest/n)
        m.OLD=previous;m.HERE=dest;m.main(sha(dest/'PACKAGE_MANIFEST.json'))
        assert {p.name for p in dest.iterdir()}==set(r['path'] for r in manifest['files'])|{'PACKAGE_MANIFEST.json'}
    listed=subprocess.run([str(PS),'-NoProfile','-File',str(HERE/'m403_control.ps1'),'-Mode','List'],capture_output=True,text=True,encoding='utf-8',check=True)
    assert json.loads(listed.stdout)==['PACKAGE_MANIFEST.json']+delta
    # Actual stdlib entry verifies full immutable whitelist/source before import.
    spec=importlib.util.spec_from_file_location('m403_entry',PKG/'m403_video_entry.py');entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
    entry.SOURCE=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/deployment/mage_vl4b/m242_m241_fixed_text_board_candidate/m241_video_language_runtime.py'
    proof=entry.precheck(sha(PKG/'PACKAGE_MANIFEST.json'))
    try:entry.precheck('0'*64)
    except RuntimeError:pass
    else:raise AssertionError('Wrong entry SHA accepted')
    return len(delta),proof


def main():
    count=count_checks();reports=trial_checks();negative=collector_checks();delta,proof=assembly_checks()
    checked=subprocess.run([str(PS),'-NoProfile','-File',str(HERE/'m403_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8',check=True)
    assert 'M403_CONTROL_SELF_TEST_PASS' in checked.stdout
    names=['m403_prepare.py','m403_support.py','m403_control.ps1','m403_workflow.py','m403_collect.py','m403_timed_count_scope.py','m402_count_scope.py','test_m402_count_scope.py','m395_support.py','m369_component_checks.py']
    value=dict(status='PASS_OFFLINE_TAIL_BALANCED_CONTROL_RECOVERY',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),checks=reports,count_checks=count,collector_negative_checks=negative,assembly_delta_files=delta,source_precheck=proof,actual_new_trials_and_original_stream=True,actual_frozen_count_and_auto_close=True,explicit_scope_model_PL_memory_doubles=True,source_binding_close_inside_request=True,failed_scope_stops_DMA_cleanup=True,controller_failure_still_collects=True,atomic_saved_destination_and_sync_order_checked=True,board_run=False,performance_pass=False,source_sha256={n:sha(HERE/n) for n in names})
    out=BASE/'runs/M403-tail-performance-support-01/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    sync('latest_m403_tail_performance_support',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=h,manifest_sha256=value['manifest_sha256']),f'## M403 末层轻量编排/回收支持（2026-10-04）\n\nSHA {h}；实际新trials与冻结M276 stream、真实冻结计数源码/原计时内恢复，模型/PL/内存/scope明确替身，8次编排A778/781 B766/767、每次七DMA逆序释放/owner恢复、失败保留；{negative}严格回收拒绝、实际原子目标/三记录顺序、精确M395组装/控制载荷和故意失败收集通过。前资源stdlib源码检查、递归missing0、同SHA数值/硬件证据复用。只有离线支持，尚无新上板或性能。下一步一次ABBABAAB；无稳定净收益关闭变体。')
    print(json.dumps(value|dict(sha256=h)))


if __name__=='__main__':main()
