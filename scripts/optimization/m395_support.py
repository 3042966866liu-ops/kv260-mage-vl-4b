"""Actual trial orchestration/stream with explicit scope/model/PL doubles."""
import ast,base64,copy,hashlib,importlib.util,json,subprocess,sys,tempfile
from pathlib import Path
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m395_prepare import PKG,OLD,once

PS=Path(r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe')

def trial_checks():
    h=(HERE/'m369_component_checks.py').read_text(encoding='utf-8').replace('import m369_trials as trials','import m395_trials as trials').replace("old=w.BASE/'candidates/M368-staged-video-03'","old=w.BASE/'candidates/M395-silu-performance-01'")
    h=once(h,"('FRAMES','STACK_SHA','ADDON','minimal','io_snapshot','tensor')","('FRAMES','STACK_SHA','ADDON','minimal','io_snapshot','tensor','SiluLayerScope')")
    h=h.replace("('m276_video_runtime','m366_head_observer')","('m276_video_runtime','m366_head_observer','m241_video_language_runtime')")
    h=once(h,'self.done=False',"self.done=False;self.allocate=lambda *a:None")
    h=once(h,"flag={'timed':False}","flag={'timed':False,'request_active':False}")
    h=once(h,"                    flag['timed']=False\n                    try:yield from scope['stream'](self,request)\n                    finally:flag['timed']=False","                    flag['timed']=False;flag['request_active']=True\n                    try:yield from scope['stream'](self,request)\n                    finally:flag['timed']=False;flag['request_active']=False")
    h=once(h,'            patches=[]',"""            from m370_patch_scope import PatchScope
            from m393_silu_scope import RetainedSiluOwnerError
            from m394_collect import expected_scope
            registry=PatchScope();cleanup=[];scope_calls=[]
            class FakeScope:
                def __init__(self,model,policy,resident,**kw):
                    assert flag['request_active'] and resident() and policy.safe() and kw['enabled']
                    self.model=model;scope_calls.append('init')
                    if failure['kind']=='entry':raise RetainedSiluOwnerError('Explicit fake entry failure')
                def bind(self,module):
                    assert flag['request_active'];scope_calls.append('bind')
                    return lambda model,hidden:Language.prefill(model,hidden)
                def close(self):
                    assert flag['request_active'];scope_calls.append('close')
                    if failure['kind']=='close':raise RetainedSiluOwnerError('Explicit fake close failure')
                def report(self):return expected_scope()
            trials.SiluLayerScope=FakeScope
            sys.modules['m241_video_language_runtime']=types.ModuleType('m241_video_language_runtime')
            patches=[]""")
    h=once(h,'            def patch(obj,name,value):patches.append((obj,name,getattr(obj,name)));setattr(obj,name,value)',"""            def patch(obj,name,value):return registry.patch(obj,name,value)
            def restore_trial(board,policy):
                assert board._m368_closed and policy.safe()
                n=registry.restore_owner(board,completion_proven=True,release_proven=True);cleanup.append(n)
                assert n==5 and not any(e[0] is board for e in registry.entries)
                return n""")
    h=h.replace("build=0x4d395832 if variant=='A' else 0x4d333537","build=0x4d333537")
    h=once(h,"for kind in (None,'active','visual'):","for kind in (None,'active','visual','entry','close'):")
    h=once(h,"requests.clear();closed.clear();result.clear();failure['kind']=kind","requests.clear();closed.clear();result.clear();cleanup.clear();scope_calls.clear();failure['kind']=kind")
    h=once(h,'engine.language.grouped_attention_calls=0','engine.language.grouped_attention_calls=0;result[\'blocked_inference_attempts\']=[]')
    h=once(h,'trials.run_trials(engine,board,policy,base,root,root,result,new,patch)','trials.run_trials(engine,board,policy,base,root,root,result,new,patch,restore_trial)')
    h=once(h,"                    assert result['fpga_transactions_total']==6256","                    assert result['fpga_transactions_total']==6256\n                    assert cleanup==[5]*8 and scope_calls==['init','bind','close']*4 and not result['retained_SiLU_scope']\n                    assert all(s['build_id']=='0x4D333537' and s['owner_registry_cleared'] and s['parser_scope']['parse_workers']==1 for s in result['samples'])")
    h=once(h,'                except TimeoutError:',"                except RetainedSiluOwnerError:\n                    assert kind in ('entry','close') and result['retained_SiLU_scope'] and len(closed)==1 and len(result['samples'])==1\n                    reports+=['SiLU '+kind+' fault retains owner and stops DMA release']\n                except TimeoutError:")
    h=once(h,'                    for obj,name,value in reversed(patches):setattr(obj,name,value)\n                    patches.clear();visual[0,0]=0',"                    for obj,name,present,value in reversed(registry.entries):\n                        if present:setattr(obj,name,value)\n                        else:delattr(obj,name)\n                    registry.entries.clear();patches.clear();visual[0,0]=0")
    root=ROOT/'tmp/m395/fixture';root.mkdir(parents=True,exist_ok=True)
    # Local test work stays in the verified workspace, including cleanup.
    h=h.replace('with tempfile.TemporaryDirectory() as folder:',f"with tempfile.TemporaryDirectory(dir={str(root)!r}) as folder:")
    ns=dict(__name__='m395_trial_fixture',__file__=str(HERE/'m395_support.py'));exec(compile(h,'actual-trials-explicit-doubles','exec'),ns)
    reports=ns['checks']()
    gate=(PKG/'m395_light_video_gate.py').read_text(encoding='utf-8')
    assert "unsafe=unsafe or result.get('retained_SiLU_scope',False)" in gate
    return reports

def export(r):
    raw=encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    return 'M395_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM395_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M395_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(v).decode()+'\n' for i,v in enumerate(parts))+f'M395_DONE case=B1 gate_rc={r["gate_return_code"]} export_rc=0\n'

def collector_checks():
    import m395_collect as c
    from m394_collect import expected_scope
    p=json.loads((BASE/'runs/M395-silu-performance-preparation-01/RESULT.json').read_text(encoding='utf-8'))
    r=json.loads((BASE/'runs/M388-ps-performance-board-01/BOARD_RESULT.json').read_text(encoding='utf-8'))
    r.update(status='PASS_M395_LIGHT_VIDEO_MEASUREMENTS',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),gate_level='balanced-fixed159-video-original-expression-versus-SiLU-workspace',
             silu_video_prerequisite_sha256=p['video_raw_sha256'],ps_prefetch_enabled=False,silu_workspace_enabled='B only')
    for s in r['samples']:s['silu_scope']=dict(expected_scope(),scope_weakref_dead=True) if s['variant']=='B' else dict(enabled=False,original_expression=True,extra_pynq_allocations=0)
    assert c.decode(export(r))[2]==r
    f=dict(r,status='FAIL_UNSAFE_RETAINED',gate_return_code=1,errors=['EXPLICIT_FAKE_RETAINED_FAILURE']);assert c.decode(export(f))[2]==f
    bad=[]
    for k,v in [('silu_video_prerequisite_sha256','bad'),('ps_prefetch_enabled',True),('silu_workspace_enabled',False),('build_id','0'),('order','ABABABAB'),('model_forward_calls',7),('safe_buffers_released',False),('fpga_transactions_total',1),('performance_pass',True),('manifest_sha256','bad'),('gate_return_code',True)]:
        q=copy.deepcopy(r);q[k]=v;bad.append(export(q))
    for kind in ('calls','buffer','owner','parser','patch','numeric','counter','retry','timer','cache','busy'):
        q=copy.deepcopy(r);s=q['samples'][1]
        if kind=='calls':s['silu_scope']['calls']=35
        elif kind=='buffer':s['silu_scope']['workspace_buffer_released']=False
        elif kind=='owner':s['silu_scope']['scope_weakref_dead']=False
        elif kind=='parser':s['parser_scope']['parse_workers']=2
        elif kind=='patch':s['restored_owner_patch_count']=4
        elif kind=='numeric':s['numeric_sha_after_timer']['logits']['sha256']='bad'
        elif kind=='counter':s['counts']['host_calls']=780
        elif kind=='retry':s['retry_records']=[]
        elif kind=='timer':s['timing']['stages_ms']['head']=s['timing']['stages_ms']['prefill']+1
        elif kind=='cache':s['after_cache']['cache_misses']=27
        elif kind=='busy':s['final_snapshot']['mm2s_dmasr']=4096
        bad.append(export(q))
    t=export(r);chunks=[x for x in t.splitlines(True) if 'RESULT_CHUNK' in x]
    bad +=[t+chunks[0],t.replace(chunks[1],''),t.replace('CHUNK=1/','CHUNK=0/'),t.replace('export_rc=0','export_rc=1')]
    for log in bad:
        try:c.decode(log)
        except (ValueError,RuntimeError,KeyError,TypeError):pass
        else:raise AssertionError('Invalid performance evidence accepted')
    return len(bad)

def assembly_checks():
    spec=importlib.util.spec_from_file_location('m395_actual_assembly',PKG/'m395_assemble.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    assert mod.OLD.as_posix()=='/home/ubuntu/m388_ps_performance_candidate_01' and mod.OLD_SHA==sha(OLD/'PACKAGE_MANIFEST.json')
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'));old={r['path']:r for r in json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']};delta=[r['path'] for r in m['files'] if old.get(r['path'])!=r]
    root=ROOT/'tmp/m395/assembly';root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as d:
        folder=Path(d).resolve();assert folder.parent==root.resolve();prior=folder/'old';dest=folder/'new';prior.mkdir();dest.mkdir()
        for p in OLD.iterdir():
            if p.is_file():(prior/p.name).write_bytes(p.read_bytes())
        for n in ['PACKAGE_MANIFEST.json']+delta:(dest/n).write_bytes((PKG/n).read_bytes())
        mod.OLD=prior;mod.HERE=dest;mod.main(sha(dest/'PACKAGE_MANIFEST.json'))
        assert all(sha(dest/r['path'])==r['sha256'] for r in m['files'])
    listing=subprocess.run([str(PS),'-NoProfile','-File',str(HERE/'m395_control.ps1'),'-Mode','List'],capture_output=True,text=True,encoding='utf-8',check=True)
    assert json.loads(listing.stdout)==['PACKAGE_MANIFEST.json']+delta
    return len(delta)

def main():
    reports=trial_checks();negative=collector_checks();delta=assembly_checks()
    p=subprocess.run([str(PS),'-NoProfile','-File',str(HERE/'m395_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8',check=True);assert 'M395_CONTROL_SELF_TEST_PASS' in p.stdout
    names=['m395_support.py','m395_control.ps1','m395_collect.py','m395_workflow.py','m395_prepare.py','m395_support_prepare.py','m393_silu_scope.py','m393_silu_workspace.py','m394_collect.py']
    value=dict(status='PASS_OFFLINE_SILU_BALANCED_CONTROL_RECOVERY',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),checks=reports,collector_negative_checks=negative,assembly_delta_files=delta,
               actual_new_trials_and_original_stream=True,explicit_scope_model_PL_memory_doubles=True,source_binding_allocation_close_inside_request=True,failed_scope_stops_DMA_cleanup=True,
               source_math_lifetime_same_SHA_previous_video=True,controller_failure_still_collects=True,board_run=False,performance_pass=False,source_sha256={n:sha(HERE/n) for n in names})
    out=BASE/'runs/M395-silu-performance-support-01/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    sync('latest_m395_silu_performance_support',dict(status=value['status'],manifest_sha256=value['manifest_sha256'],result=out.relative_to(ROOT).as_posix(),sha256=h),
         f'## M395 SiLU轻量编排/回收支持（2026-10-04）\n\n实际新trials与原M276 stream、scope/model/PL/内存明确替身，8请求/4B scope绑定/分配/关闭在计时内，entry/close失败保留阻止DMA释放、下一请求；{negative}回收负例、完整真实旧远程组装与PS载荷选择、控制故意失败收集通过。SHA {h}；数学/scope同SHA复用本轮新视频证据，不是完整请求提速。下一步一次本级ABBABAAB，净收益不成立关闭此变体。')
    print(json.dumps(value|{'sha256':h}))

if __name__=='__main__':main()
