"""Actual new trial control, explicit PS/model/MMIO doubles, saved recovery."""
import ast,base64,copy,hashlib,json,subprocess,sys,tempfile,shutil
from pathlib import Path
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m388_prepare import PKG,OLD,VIDEO,once
def main():
    prep=json.loads((BASE/'runs/M388-ps-performance-preparation-01/RESULT.json').read_text(encoding='utf-8'));prior=prep['PS_video_prerequisite_sha256']
    s=(HERE/'m387_control_recovered_02.ps1').read_text(encoding='utf-8').replace('M387','M388').replace('m387','m388').replace('ps-video','ps-performance').replace('ps_video','ps_performance').replace('PS_VIDEO','LIGHT_VIDEO').replace('run_m388_ps_video.sh','run_m388_light_video.sh').replace('run_m388_ps_performance.sh','run_m388_light_video.sh').replace('sudo_precheck_02.log','sudo_precheck_01.log').replace('candidates/M386-ps-text-01','candidates/M387-ps-video-01').replace('candidates/M380-gate-up-video-01','candidates/M381-gate-up-performance-01').replace('-TimeoutSeconds 900','-TimeoutSeconds 3900')
    atomic(HERE/'m388_control.ps1',s.encode('utf-8'))
    s=(HERE/'m387_workflow.py').read_text(encoding='utf-8').replace('M387','M388').replace('m387','m388').replace('ps-video','ps-performance').replace('ps_video','ps_performance').replace('candidates/M386-ps-text-01','candidates/M387-ps-video-01').replace('candidates/M380-gate-up-video-01','candidates/M381-gate-up-performance-01').replace('37载荷',str(json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['file_count'])+'载荷').replace('精确M386与M380','精确M387与M381').replace('固定159视频162窗口','同核原暂存/PS预读交错请求').replace('一次PS暂存固定159视频完整数值门禁','一次同核原暂存/PS预读ABBABAAB完整请求对照')
    atomic(HERE/'m388_workflow.py',s.encode('utf-8'))
    c=(HERE/'m381_collect.py').read_text(encoding='utf-8').replace('M381','M388').replace('m381','m388').replace('gate-up-performance','ps-performance').replace('gate_up_performance','ps_performance').replace('balanced-fixed159-video-one-versus-two-parser-performance','balanced-fixed159-video-original-staging-versus-PS-prefetch').replace('two_parser_video_sha256','PS_video_prerequisite_sha256').replace('947646a295cc3c60a0a80c49f89e9465ce7e9bac9a9446e34e3504b6d7f21985',prior).replace("r['ps_prefetch_enabled'] is not False","r['ps_prefetch_enabled']!='B only'")
    c=once(c,'from m376_gate_up_workers import PINNED',"sys.path.insert(0,str(w.BASE/'candidates/M388-ps-performance-01'))\nfrom m368_stage_policy import assess,SHAPES")
    a=c.index("            wanted=dict(parse_workers=1,");z=c.index("            n=s['numeric_sha_after_timer']",a)
    c=c[:a]+"            wanted=dict(parse_workers=1,original_single_worker_dispatch=True,bindings_restored=True,extra_dma_allocations=0)\n            if scope!=wanted or not s['owner_registry_cleared'] or s['restored_owner_patch_count']!=5:raise ValueError('Original parser/sealed owner lifecycle differs')\n            p=s['ps_session']\n            if s['variant']=='A':\n                if p!=dict(enabled=False,original_staging=True,extra_pynq_allocations=0):raise ValueError('Original staging changed')\n            else:\n                component=p['component']\n                required=dict(status='COMPLETE_COMPONENT_ONLY',stages=162,submissions=162,ps_payload_bytes=27852800,extra_cma_allocation_calls=0,total_weight_bytes=expected['stage_bytes'],open_files=0,live_views=0,performance_pass=False,hardware_contract_changed=False)\n                if any(component[k]!=v for k,v in required.items()) or p['production_policy_changed'] or p['additional_dma_allocations'] or not p['source_component_unchanged'] or not p['session_weakref_dead']:raise ValueError('PS scope/count/lifetime differs')\n                if p['slot_release']!=dict(released_ports=4,bytearrays_sole_owned_before_release=True,all_owner_weakrefs_dead=True,explicit_gc_or_trim=False):raise ValueError('PS owner release differs')\n                if p['budget_growth_bytes']!=1024<<20 or p['available_margin_bytes']!=64<<20 or len(p['independent_memory_checks'])<166:raise ValueError('PS admission coverage differs')\n                for x in p['independent_memory_checks']:\n                    decision=assess(x['memory'],p['budget_baseline_rss'],x['cma_counts'],p['independent_memory_checks'][0]['cma_counts'],sealed=True,buffer_bytes=SHAPES)\n                    if decision!=x['decision']:raise ValueError('Actual PS memory decision differs')\n"+c[z:]
    c=c.replace('A原1/B只gate_up2解析worker','A原暂存/B普通PS预读，均原单parser').replace('Changed parser prerequisite','Changed PS prerequisite')
    # Last metadata-prefix mistake is checked before freezing controller support.
    assert "w.sync('latest_m388_ps_performance_board'" in c and 'm376' not in c
    atomic(HERE/'m388_collect.py',c.encode('utf-8'))
    ctl=subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoProfile','-File',str(HERE/'m388_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8');assert ctl.returncode==0 and 'M388_CONTROL_SELF_TEST_PASS' in ctl.stdout,ctl.stdout+ctl.stderr
    # Reuse frozen original M276 stream harness. No PS algorithm reimplementation:
    # real PS I/O/sole-owner behavior was checked at the previous scope; here PS,
    # model/MMIO/memory are explicit doubles to exercise timed control/failures.
    h=(HERE/'m369_component_checks.py').read_text(encoding='utf-8').replace('import m369_trials as trials','import m388_trials as trials').replace("old=w.BASE/'candidates/M368-staged-video-03'","old=w.BASE/'candidates/M388-ps-performance-01'")
    h=once(h,"('FRAMES','STACK_SHA','ADDON','minimal','io_snapshot','tensor')","('FRAMES','STACK_SHA','ADDON','minimal','io_snapshot','tensor','VideoPSReadSession')")
    h=once(h,'self.done=False',"self.done=False;self.allocate=lambda *a:None;self.language_layout=object();self.head_layout=object();self.head_contract=N(chains=[{} for _ in range(8)]);self._language_chain=lambda *a:{}")
    h=once(h,"result={};requests=[];closed=[];flag={'timed':False}","result={};requests=[];closed=[];flag={'timed':False,'request_active':False}")
    h=once(h,"                    flag['timed']=False\n                    try:yield from scope['stream'](self,request)\n                    finally:flag['timed']=False", "                    flag['timed']=False;flag['request_active']=True\n                    try:yield from scope['stream'](self,request)\n                    finally:flag['timed']=False;flag['request_active']=False")
    h=once(h,'            patches=[]',"            from m370_patch_scope import PatchScope\n            from ps_read_ahead import RetainedPSResourcesError\n            registry=PatchScope();cleanup_calls=[];scope_calls=[]\n            class FakePSScope:\n                def __init__(self,board,base,plan,**kw):\n                    assert flag['request_active'] and len(plan)==162 and kw['enabled'] and kw['resident']()\n                    assert kw['policy'].build==0x4d333537\n                    scope_calls.append('init');self.board=board\n                    if failure['kind']=='PSenter':raise RetainedPSResourcesError('Explicit fake PS entry retained')\n                def __enter__(self):scope_calls.append('enter');return self\n                def __exit__(self,*a):\n                    scope_calls.append('exit')\n                    if failure['kind']=='PSclose':raise RetainedPSResourcesError('Explicit fake PS close retained')\n                def report(self):\n                    assert flag['request_active'];return {'explicit_fake':True}\n            trials.VideoPSReadSession=FakePSScope\n            patches=[]")
    h=once(h,'            def patch(obj,name,value):patches.append((obj,name,getattr(obj,name)));setattr(obj,name,value)',"            def patch(obj,name,value):return registry.patch(obj,name,value)\n            def restore_trial(board,policy):\n                assert board._m368_closed and policy.safe()\n                n=registry.restore_owner(board,completion_proven=True,release_proven=True);cleanup_calls.append(n)\n                assert n==5 and not any(e[0] is board for e in registry.entries)\n                return n")
    h=once(h,"build=0x4d395832 if variant=='A' else 0x4d333537","build=0x4d333537")
    h=once(h,"for kind in (None,'active','visual'):","for kind in (None,'active','visual','PSenter','PSclose'):")
    h=once(h,"requests.clear();closed.clear();result.clear();failure['kind']=kind","requests.clear();closed.clear();result.clear();cleanup_calls.clear();scope_calls.clear();failure['kind']=kind")
    h=once(h,'engine.board=board;engine.language.runtime=board;engine.language.grouped_attention_calls=0',"engine.board=board;engine.language.runtime=board;engine.language.grouped_attention_calls=0;engine.tokenizer=object();result['blocked_inference_attempts']=[]")
    h=once(h,'trials.run_trials(engine,board,policy,base,root,root,result,new,patch)','trials.run_trials(engine,board,policy,base,root,root,result,new,patch,restore_trial)')
    h=once(h,"                    assert result['fpga_transactions_total']==6256","                    assert result['fpga_transactions_total']==6256\n                    assert cleanup_calls==[5]*8 and scope_calls==['init','enter','exit']*4\n                    assert not result['retained_PS_scope'] and all(s['build_id']=='0x4D333537' and s['owner_registry_cleared'] and s['parser_scope']['parse_workers']==1 for s in result['samples'])")
    h=once(h,"                except TimeoutError:","                except RetainedPSResourcesError:\n                    assert kind in ('PSenter','PSclose') and result['retained_PS_scope'] and len(closed)==1 and len(result['samples'])==1\n                    reports+=['PS '+kind+' failure retains scope and prevents next DMA close']\n                except TimeoutError:")
    h=once(h,'                    for obj,name,value in reversed(patches):setattr(obj,name,value)\n                    patches.clear();visual[0,0]=0',"                    # Teardown explicit Python doubles only, never board recovery.\n                    for obj,name,present,value in reversed(registry.entries):\n                        if present:setattr(obj,name,value)\n                        else:delattr(obj,name)\n                    registry.entries.clear();patches.clear();visual[0,0]=0")
    ns=dict(__name__='m388_cpu_control_fixture',__file__=str(HERE/'m388_support.py'));exec(compile(h,'actual-new-PS-trials-explicit-doubles','exec'),ns);reports=ns['checks']()
    # Exact two-source assembly over original immutable source files, including
    # every payload. Negative checks reuse unchanged algorithm proved in M387.
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);dest=root/'candidate';primary=root/'primary';secondary=root/'secondary';dest.mkdir();shutil.copytree(VIDEO,primary);shutil.copytree(OLD,secondary)
        manifest=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'));first={r['path']:r for r in json.loads((VIDEO/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']};second={r['path']:r for r in json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']}
        for row in manifest['files']:
            if first.get(row['path'])!=row and second.get(row['path'])!=row:shutil.copyfile(PKG/row['path'],dest/row['path'])
        shutil.copyfile(PKG/'PACKAGE_MANIFEST.json',dest/'PACKAGE_MANIFEST.json')
        s=(PKG/'m388_assemble.py').read_text(encoding='utf-8').replace('/home/ubuntu/m387_ps_video_candidate_01',primary.as_posix()).replace('/home/ubuntu/m381_gate_up_performance_candidate_01',secondary.as_posix())
        namespace=dict(__file__=str(dest/'m388_assemble.py'),__name__='assembly-fixture');exec(compile(s,'actual-new-assembly','exec'),namespace);namespace['main'](sha(dest/'PACKAGE_MANIFEST.json'))
        assert all(sha(dest/r['path'])==r['sha256'] for r in manifest['files'])
    import m388_collect as collector
    row=json.loads((BASE/'runs/M381-gate-up-performance-board-01/BOARD_RESULT.json').read_text(encoding='utf-8'));row.update(status='PASS_M388_LIGHT_VIDEO_MEASUREMENTS',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),gate_level='balanced-fixed159-video-original-staging-versus-PS-prefetch',PS_video_prerequisite_sha256=prior,ps_prefetch_enabled='B only',historical_hardware_40_81_percent_result_unchanged=True)
    actual_ps=json.loads((BASE/'runs/M387-ps-video-board-01/BOARD_RESULT.json').read_text(encoding='utf-8'))['ps_session']
    for s in row['samples']:
        s['parser_scope']=dict(parse_workers=1,original_single_worker_dispatch=True,bindings_restored=True,extra_dma_allocations=0);s['restored_owner_patch_count']=5
        s['ps_session']=dict(actual_ps,session_weakref_dead=True) if s['variant']=='B' else dict(enabled=False,original_staging=True,extra_pynq_allocations=0)
    def export(r):
        raw=encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M388_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM388_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M388_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(v).decode()+'\n' for i,v in enumerate(parts))+f'M388_DONE case=B1 gate_rc={r["gate_return_code"]} export_rc=0\n'
    assert collector.decode(export(row))[2]==row
    assert collector.decode(export(dict(row,status='FAIL',gate_return_code=1,errors=['deliberate'])))[2]['gate_return_code']==1
    bad=[]
    for k,v in [('PS_video_prerequisite_sha256','0'*64),('ps_prefetch_enabled',True),('build_id','0x4D395832'),('order','ABABABAB'),('model_forward_calls',7),('safe_buffers_released',False),('fpga_transactions_total',1),('performance_pass',True),('manifest_sha256','0'*64)]:bad.append(dict(row,**{k:v}))
    for kind in ('parser','owner','stages','budget','slot','worker','session','source','numeric','counter'):
        r=copy.deepcopy(row);sample=r['samples'][1];p=sample['ps_session']
        if kind=='parser':sample['parser_scope']['parse_workers']=2
        elif kind=='owner':sample['restored_owner_patch_count']=4
        elif kind=='stages':p['component']['stages']=161
        elif kind=='budget':p['budget_growth_bytes']=256<<20
        elif kind=='slot':p['slot_release']['all_owner_weakrefs_dead']=False
        elif kind=='worker':p['component']['open_files']=1
        elif kind=='session':p['session_weakref_dead']=False
        elif kind=='source':p['source_component_unchanged']=False
        elif kind=='numeric':sample['numeric_sha_after_timer']['logits']['sha256']='0'*64
        elif kind=='counter':p['independent_memory_checks'][1]['cma_counts']['unknown']=1
        bad.append(r)
    for r in bad:
        try:collector.decode(export(r))
        except (ValueError,RuntimeError,KeyError,MemoryError):pass
        else:raise AssertionError('Invalid PS performance result accepted')
    for log in [export(row)+export(row),export(row).replace('CHUNK=1/','CHUNK=0/'),export(row).replace('export_rc=0','export_rc=1')]:
        try:collector.decode(log)
        except ValueError:pass
        else:raise AssertionError('Invalid raw accepted')
    names=('m388_control.ps1','m388_workflow.py','m388_collect.py','m388_support.py','m388_prepare.py')
    for name in names:
        if name.endswith('.py'):ast.parse((HERE/name).read_text(encoding='utf-8'),feature_version=(3,10))
    result=dict(status='PASS_OFFLINE_PS_BALANCED_TRIAL_CONTROL_RECOVERY',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),actual_new_trials_and_original_frozen_stream=True,explicit_PS_model_MMIO_memory_doubles=True,checks=reports,candidate_PS_scope_inside_original_request_timer=True,PS_entry_and_close_failure_retains=True,source_and_algorithm_same_SHA_preceding_gate_reused=True,new_assembly_all_files_exact=True,collector_old_numeric_evidence_fixture_only=True,collector_negative_checks=len(bad)+3,controller_failure_collects=True,board_run=False,numerical_pass=False,performance_pass=False,source_sha256={n:sha(HERE/n) for n in names})
    p=BASE/'runs/M388-ps-performance-support-01/RESULT.json';atomic(p,encoded(result),immutable=True);d=sha(p)
    sync('latest_m388_ps_performance_support',dict(status=result['status'],result=p.relative_to(ROOT).as_posix(),sha256=d,manifest_sha256=result['manifest_sha256']),f'## M388 PS轻量交错控制/回收支持（2026-10-03）\n\n实际新trials＋原M276 stream、PS/model/MMIO/memory明确替身；八请求/四B scope在请求计时内，PS entry/close故障保留阻止DMA清理；两源完整assembly核对及{len(bad)+3}回收负例、控制故意失败收集通过。SHA {d}；旧组件算法/新视频数值同SHA复用，不冒称新性能。下一步同COM3授权后一次本级ABBABAAB，任何容量/生命周期失败停止扩大。')
    print('M388_SUPPORT_PASS',d,len(bad)+3,reports)
if __name__=='__main__':main()
