"""Execute actual new trial control with explicit fake model/MMIO/parser-scope."""
import ast,base64,copy,hashlib,json,subprocess,sys,types
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m381_prepare import PKG,OLD,once
def main():
    prep=json.loads((BASE/'runs/M381-gate-up-performance-preparation-01/RESULT.json').read_text(encoding='utf-8'));prior=prep['two_parser_video_sha256']
    controller=(HERE/'m380_control.ps1').read_text(encoding='utf-8').replace('M380','M381').replace('m380','m381').replace('M381-gate-up-video-01','M381-gate-up-performance-01').replace('/home/ubuntu/m381_gate_up_video_candidate_01','/home/ubuntu/m381_gate_up_performance_candidate_01').replace('latest_m381_gate_up_video','latest_m381_gate_up_performance').replace('M381-gate-up-video-board-01','M381-gate-up-performance-board-01').replace('run_m381_staged_video.sh','run_m381_light_video.sh').replace('ENABLE_STAGED_VIDEO','ENABLE_LIGHT_VIDEO').replace('candidates/M368-staged-video-03/PACKAGE_MANIFEST.json','candidates/M369-light-video-01/PACKAGE_MANIFEST.json').replace('-TimeoutSeconds 1200','-TimeoutSeconds 3900')
    atomic(HERE/'m381_control.ps1',controller.encode('utf-8'))
    workflow=(HERE/'m380_workflow.py').read_text(encoding='utf-8').replace('M380','M381').replace('m380','m381').replace('M381-gate-up-video-01','M381-gate-up-performance-01').replace('candidates/M368-staged-video-03','candidates/M369-light-video-01').replace('M381-gate-up-video-transfer-01','M381-gate-up-performance-transfer-01').replace('latest_m381_gate_up_video','latest_m381_gate_up_performance').replace('33载荷',str(json.loads((PKG/'PACKAGE_MANIFEST.json').read_text())['file_count'])+'载荷').replace('一次双worker原159视频数值门禁','一次同并行核单/双worker交错请求对照')
    atomic(HERE/'m381_workflow.py',workflow.encode('utf-8'))
    c=(HERE/'m369_collect.py').read_text(encoding='utf-8').replace('M369','M381').replace('M381-light-video-01','M381-gate-up-performance-01').replace('M381-light-video-board-01','M381-gate-up-performance-board-01').replace('latest_m369_light_video_board','latest_m381_gate_up_performance_board').replace('balanced-fixed159-video-light-performance','balanced-fixed159-video-one-versus-two-parser-performance')
    c=once(c,'from board_safety import safe_to_release','from board_safety import safe_to_release\nfrom m376_gate_up_workers import PINNED')
    c=once(c,"            build='0x4D395832' if 'ABBABAAB'[i]=='A' else '0x4D333537'","            build='0x4D333537'")
    c=once(c,"        if r['order']!='ABBABAAB'", "        if r['build_id']!='0x4D333537' or r['two_parser_video_sha256']!='"+prior+"' or r['ps_prefetch_enabled'] is not False or not r['historical_hardware_40_81_percent_result_unchanged']:raise ValueError('Changed parser prerequisite/scope differs')\n        if r['order']!='ABBABAAB'")
    c=once(c,"            n=s['numeric_sha_after_timer']", "            scope=s['parser_scope']\n            wanted=dict(parse_workers=1,original_single_worker_dispatch=True,bindings_restored=True,extra_dma_allocations=0) if s['variant']=='A' else dict(parse_workers=2,gate_up_calls=36,bindings_restored=True,extra_dma_allocations=0,pending_output_slots=2,statistics_lock=True,source_sha256=PINNED,performance_pass=False)\n            if any(scope[k]!=v for k,v in wanted.items()) or not s['owner_registry_cleared'] or s['restored_owner_patch_count']!=4:raise ValueError('Parser variant/owner lifecycle differs')\n            n=s['numeric_sha_after_timer']")
    c=c.replace('稳定0x4D395832/候选0x4D333537','两组都Build0x4D333537；A原1/B只gate_up2解析worker')
    atomic(HERE/'m381_collect.py',c.encode('utf-8'))
    p=subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoProfile','-File',str(HERE/'m381_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8');assert p.returncode==0 and 'M381_CONTROL_SELF_TEST_PASS' in p.stdout,p.stdout+p.stderr
    # Reuse exact frozen M276 stream harness, replacing only its declared fakes/variant mapping.
    h=(HERE/'m369_component_checks.py').read_text(encoding='utf-8').replace('import m369_trials as trials','import m381_trials as trials').replace("old=w.BASE/'candidates/M368-staged-video-03'","old=w.BASE/'candidates/M381-gate-up-performance-01'")
    h=once(h,"('FRAMES','STACK_SHA','ADDON','minimal','io_snapshot','tensor')","('FRAMES','STACK_SHA','ADDON','minimal','io_snapshot','tensor','GateUpWorkers')")
    h=once(h,"build=0x4d395832 if variant=='A' else 0x4d333537","build=0x4d333537")
    h=once(h,'            patches=[]',"            from m370_patch_scope import PatchScope\n            registry=PatchScope();cleanup_calls=[];scope_calls=[]\n            class FakeParserScope:\n                def __init__(self,board,workers,enabled):\n                    assert workers==2 and enabled is True and not flag['timed']\n                    self.board=board;scope_calls.append('init2')\n                def __enter__(self):\n                    assert not flag['timed'];scope_calls.append('enter2');return self\n                def __exit__(self,*a):scope_calls.append('exit2')\n                def report(self):\n                    assert not flag['timed']\n                    from m376_gate_up_workers import PINNED\n                    return dict(parse_workers=2,gate_up_calls=36,bindings_restored=True,extra_dma_allocations=0,pending_output_slots=2,statistics_lock=True,source_sha256=PINNED,performance_pass=False)\n            trials.GateUpWorkers=FakeParserScope\n            patches=[]")
    h=once(h,'            def patch(obj,name,value):patches.append((obj,name,getattr(obj,name)));setattr(obj,name,value)',"            def patch(obj,name,value):return registry.patch(obj,name,value)\n            def restore_trial(board,policy):\n                assert board._m368_closed and policy.safe()\n                n=registry.restore_owner(board,completion_proven=True,release_proven=True);cleanup_calls.append(n)\n                assert n==4 and not any(e[0] is board for e in registry.entries)\n                return n")
    h=once(h,'trials.run_trials(engine,board,policy,base,root,root,result,new,patch)','trials.run_trials(engine,board,policy,base,root,root,result,new,patch,restore_trial)')
    h=once(h,"                    assert result['fpga_transactions_total']==6256","                    assert result['fpga_transactions_total']==6256\n                    assert cleanup_calls==[4]*8 and scope_calls==['init2','enter2','exit2']*4\n                    assert all(s['build_id']=='0x4D333537' and s['owner_registry_cleared'] for s in result['samples'])")
    h=once(h,'                requests.clear();closed.clear();result.clear();failure[\'kind\']=kind',"                requests.clear();closed.clear();result.clear();cleanup_calls.clear();scope_calls.clear();failure['kind']=kind")
    h=once(h,'                    for obj,name,value in reversed(patches):setattr(obj,name,value)\n                    patches.clear();visual[0,0]=0',"                    # Fixture teardown only: owners/PL are explicit Python fakes, not board cleanup.\n                    for obj,name,present,value in reversed(registry.entries):\n                        if present:setattr(obj,name,value)\n                        else:delattr(obj,name)\n                    registry.entries.clear();patches.clear();visual[0,0]=0")
    namespace=dict(__name__='m381_cpu_harness_fixture',__file__=str(HERE/'m381_support.py'));exec(compile(h,'actual-new-trial-control-explicit-fakes','exec'),namespace);reports=namespace['checks']()
    import m381_collect as collector
    row=json.loads((BASE/'runs/M369-light-video-board-01/BOARD_RESULT.json').read_text(encoding='utf-8'));row.update(status='PASS_M381_LIGHT_VIDEO_MEASUREMENTS',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),gate_level='balanced-fixed159-video-one-versus-two-parser-performance',build_id='0x4D333537',two_parser_video_sha256=prior,ps_prefetch_enabled=False,historical_hardware_40_81_percent_result_unchanged=True)
    from m376_gate_up_workers import PINNED
    for s in row['samples']:
        s['build_id']='0x4D333537';s['final_snapshot']['ap_return']=0x4d333537
        s['parser_scope']=dict(parse_workers=1,original_single_worker_dispatch=True,bindings_restored=True,extra_dma_allocations=0) if s['variant']=='A' else dict(parse_workers=2,gate_up_calls=36,bindings_restored=True,extra_dma_allocations=0,pending_output_slots=2,statistics_lock=True,source_sha256=PINNED,performance_pass=False)
        s['owner_registry_cleared']=True;s['restored_owner_patch_count']=4
    def export(r):
        raw=encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M381_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM381_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M381_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(v).decode()+'\n' for i,v in enumerate(parts))+f'M381_DONE case=B1 gate_rc={r["gate_return_code"]} export_rc=0\n'
    assert collector.decode(export(row))[2]==row;assert collector.decode(export(dict(row,status='FAIL',gate_return_code=1,errors=['deliberate failure'])))[2]['gate_return_code']==1
    bad=[]
    for k,v in [('two_parser_video_sha256','0'*64),('ps_prefetch_enabled',True),('build_id','0x4D395832'),('order','ABABABAB'),('model_forward_calls',7),('safe_buffers_released',False),('fpga_transactions_total',1),('performance_pass',True),('manifest_sha256','0'*64)]:bad.append(dict(row,**{k:v}))
    for kind in ('width','coverage','lifecycle','patches','hardware','numerics','counts'):
        r=copy.deepcopy(row);s=r['samples'][1]
        if kind=='width':s['parser_scope']['parse_workers']=1
        elif kind=='coverage':s['parser_scope']['gate_up_calls']=35
        elif kind=='lifecycle':s['owner_registry_cleared']=False
        elif kind=='patches':s['restored_owner_patch_count']=0
        elif kind=='hardware':s['build_id']='0x4D395832'
        elif kind=='numerics':s['numeric_sha_after_timer']['logits']['sha256']='0'*64
        elif kind=='counts':s['counts']['logical_calls']=777
        bad.append(r)
    count=0
    for r in bad:
        try:collector.decode(export(r))
        except ValueError:count+=1
        else:raise AssertionError('Invalid result accepted')
    for log in (export(row)+export(row),export(row).replace('CHUNK=1/','CHUNK=0/'),export(row).replace('export_rc=0','export_rc=1')):
        try:collector.decode(log)
        except ValueError:count+=1
        else:raise AssertionError('Invalid transfer accepted')
    for n in ('m381_collect.py','m381_workflow.py','m381_support.py'):ast.parse((HERE/n).read_text(encoding='utf-8'),feature_version=(3,10))
    r=dict(status='PASS_OFFLINE_TWO_PARSER_BALANCED_TRIAL_CONTROL_RECOVERY',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),actual_new_trials_and_frozen_stream=True,explicit_fake_model_mmio_memory_and_parser_scope=True,checks=reports,eight_current_build_requests=True,four_candidate_scope_pairs_outside_timers=True,eight_owner_cleanup_checks=True,active_failure_retains=True,collector_legacy_evidence_shape_fixture_only=True,collector_negative_checks=count,controller_failure_collects=True,board_run=False,numerical_pass=False,performance_pass=False,source_sha256={n:sha(HERE/n) for n in ('m381_control.ps1','m381_workflow.py','m381_collect.py','m381_support.py','m376_gate_up_workers.py','m370_patch_scope.py')})
    p=BASE/'runs/M381-gate-up-performance-support-01/RESULT.json';atomic(p,encoded(r),immutable=True);digest=sha(p);sync('latest_m381_gate_up_performance_support',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256']),f'## M381 同并行核单/双worker交错控制支持（2026-10-03）\n\n实际新trials及原M276 stream编排配显式fake model/MMIO/memory/parser scope，八次全部当前Build、四B候选scope在计时外生成，八owner各4绑定清理，坏视觉拒绝及活动故障保留。{count}项collector负例拒绝，旧原证据仅几何fixture不冒称新性能。支持 SHA {digest}；下一步一次新变体完整请求对照。')
    print('M381_SUPPORT_PASS',digest,count)
if __name__=='__main__':main()
