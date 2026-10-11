"""Actual frozen orchestration with explicit runtime/MMIO/memory test doubles."""
import ast,base64,copy,hashlib,json,subprocess,textwrap,types
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m382_prepare import PKG,OLD,once
from m382_ps_slot import run_probe,SlotOwner,RetainedSlotError
from m370_patch_scope import PatchScope
from test_m382_ps_slot import memory

def main():
    source=(HERE/'m378_control.ps1').read_text(encoding='utf-8').replace('M378','M382').replace('m378','m382').replace('M382-gate-up-layer','M382-sealed-ps-slot').replace('m382_gate_up_layer_candidate','m382_sealed_ps_slot_candidate').replace('latest_m382_gate_up_layer','latest_m382_sealed_ps_slot').replace('run_m382_staged_layer.sh','run_m382_load_slot.sh').replace('ENABLE_STAGED_LAYER','ENABLE_LOAD_ONLY_SLOT').replace('candidates/M377-gate-up-pair-01/PACKAGE_MANIFEST.json','candidates/M378-gate-up-layer-01/PACKAGE_MANIFEST.json')
    source=source.replace("'tmp/m382/sudo_precheck_01.log'","'tmp/m382/sudo_precheck_02.log'")
    atomic(HERE/'m382_control.ps1',source.encode('utf-8'))
    source=(HERE/'m378_workflow.py').read_text(encoding='utf-8').replace('M378','M382').replace('m378','m382').replace('M382-gate-up-layer','M382-sealed-ps-slot').replace('candidates/M377-gate-up-pair-01','candidates/M378-gate-up-layer-01').replace('latest_m382_gate_up_layer','latest_m382_sealed_ps_slot').replace('单层等待诊断包','只加载PS slot诊断包').replace('精确M365已验证包','精确M378已验证包').replace('27载荷','25载荷').replace('一次双worker单层数值门禁','一次封锁额外DMA的完整runtime/PS slot只加载诊断')
    atomic(HERE/'m382_workflow.py',source.encode('utf-8'))
    pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    p=subprocess.run([pwsh,'-NoProfile','-File',str(HERE/'m382_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    assert p.returncode==0 and 'M382_CONTROL_SELF_TEST_PASS' in p.stdout,p.stdout+p.stderr
    source=(PKG/'m382_load_slot_gate.py').read_text(encoding='utf-8');tree=ast.parse(source)
    forbid_node=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='forbid')
    ns={};exec(compile(ast.Module(body=[forbid_node],type_ignores=[]),'actual-forbid','exec'),ns)
    slots=[];blocked=[];result=dict(loaded_capacity=dict(meets_threshold=False),released_buffers=[],ps_slot={})
    runtime=types.SimpleNamespace(_m365_closed=False,host_calls=0,logical_calls=0,allocate=lambda *a:None,dma=types.SimpleNamespace(sendchannel=types.SimpleNamespace(transfer=lambda *a:None),recvchannel=types.SimpleNamespace(transfer=lambda *a:None)),kernel=types.SimpleNamespace(write=lambda *a:None))
    engine=types.SimpleNamespace(board=runtime,language=object(),vision=object(),tokenizer=object())
    buffers=[types.SimpleNamespace(nbytes=n) for n in [6963200]*4+[389152,2621440,2621440]]
    counts=lambda:{'area:success':7,'area:fail':0}
    policy=types.SimpleNamespace(seal=lambda buffers,build:None,snapshot=lambda:memory(),counters=counts,safe=lambda:True)
    pynq=types.SimpleNamespace(allocate=lambda *a:None);registry=PatchScope()
    ns.update(policy=policy,allocations=buffers,TARGET_BUILD='0x4D333537',result=result,patch=registry.patch,pynq=pynq,runtime=runtime,blocked=blocked,initialized=True,engine=engine,SHAPES=[int(b.nbytes) for b in buffers],slots=slots,mark=lambda name:memory())
    def probe(*a):return run_probe(*a,settle_s=.06,page_bytes=4096)
    ns['run_probe']=probe
    section=source[source.index('        policy.seal(allocations,'):source.index("        result['boot_unchanged']",source.index('        policy.seal(allocations,'))]
    exec(compile(textwrap.dedent(section),'actual-new-slot-orchestration','exec'),ns)
    assert not slots and result['resident_before_slot'] and result['resident_after_slot_release'] and result['load_only_slot_pass']
    assert result['ps_slot']['release']['released_ports']==4 and not result['ps_prefetch_enabled']
    guards=[pynq.allocate,runtime.allocate,runtime.dma.sendchannel.transfer,runtime.dma.recvchannel.transfer,runtime.kernel.write]
    for guard in guards:
        try:guard(1)
        except RuntimeError:pass
        else:raise AssertionError('Actual blocked path accepted')
    assert len(blocked)==5 and not ns['resident']()
    blocked.clear();assert ns['resident']()
    engine.vision=None;assert not ns['resident']();engine.vision=object()
    buffers.append(types.SimpleNamespace(nbytes=1));assert not ns['resident']();buffers.pop()
    runtime.host_calls=1;assert not ns['resident']();runtime.host_calls=0
    result['released_buffers'].append({});assert not ns['resident']();result['released_buffers'].clear()
    registry.restore_all(completion_proven=True,release_proven=True);assert not registry.entries
    # Test actual idempotent seven-owned release with explicit no-transaction safety.
    from owned_buffer_release import OwnedBufferRelease
    released=[];calls=[]
    release_hooks=[OwnedBufferRelease(lambda i=i:calls.append(i),lambda:True,lambda i=i:released.append(i)) for i in range(7)]
    for hook in reversed(release_hooks):hook();hook()
    assert calls==released==list(reversed(range(7)))
    from m382_collect import decode
    row=json.loads((BASE/'runs/M378-gate-up-layer-board-01/BOARD_RESULT.json').read_text(encoding='utf-8'))
    row.update(result,status='PASS_M382_SEALED_LOAD_ONLY_PS_SLOT',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),gate_level='sealed-DMA-load-only-PS-slot-diagnostic',gate_return_code=0,errors=[],model_forward_calls=0,numerical_pass=False,fpga_transactions=0,host_calls=0,logical_calls=0,worker_started=False,extra_pynq_allocations=0,patch_registry_cleared=True,safe_buffers_released=True,ps_slot_released=True,ps_slot_port_count_before_release=0,original_buffer_release_count=7,unsafe_buffers_retained=False,transactions=[],elapsed_s_diagnostic_not_performance=1)
    # Original result is only geometry/environment fixture; all new memory/PS
    # and never-submitted fields are explicitly synthetic, never board evidence.
    allocated=json.loads((BASE/'runs/M378-gate-up-layer-board-01/BOARD_RESULT.json').read_text(encoding='utf-8'))['allocated_buffers']
    row['allocated_buffers']=allocated;row['released_buffers']=list(reversed(allocated))
    never=dict(ap_ctrl=4,ap_return=0,mm2s_dmasr=0,s2mm_dmasr=0,mm2s_error=False,s2mm_error=False,kernel_read_error='',return_read_error='',dma_read_error='')
    row['loaded_snapshot']=row['final_snapshot']=never;row['sampled_memory']=dict(observer_stopped=True,stop_reason=None)
    def export(r):
        raw=encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M382_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM382_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M382_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(v).decode()+'\n' for i,v in enumerate(parts))+f'M382_DONE case=B1 gate_rc={r["gate_return_code"]} export_rc=0\n'
    assert decode(export(row))[2]==row
    assert decode(export(dict(row,status='FAIL',gate_return_code=1,errors=['deliberate failure'])))[2]['gate_return_code']==1
    bad=[]
    for k,v in [('model_forward_calls',1),('fpga_transactions',1),('numerical_pass',True),('memory_capacity_proven',True),('performance_pass',True),('safe_buffers_released',False),('resident_after_slot_release',False),('extra_pynq_allocations',1),('allocator_sealed',False),('patch_registry_cleared',False),('released_buffers',[]),('manifest_sha256','0'*64)]:bad.append(dict(row,**{k:v}))
    for k,v in [('objects_released',False),('observer_stopped',False),('slot_bytes',1),('ports',[]),('checkpoints',[]),('initial_cma_counts',{}),('budget_growth_bytes',1),('original_error','failure')]:
        x=copy.deepcopy(row);x['ps_slot'][k]=v;bad.append(x)
    x=copy.deepcopy(row);x['ps_slot']['checkpoints'][0]['cma_counts']={'changed':1};bad.append(x)
    x=copy.deepcopy(row);x['final_snapshot']['ap_ctrl']=1;bad.append(x)
    negatives=0
    for r in bad:
        try:decode(export(r))
        except ValueError:negatives+=1
        else:raise AssertionError('Invalid result accepted')
    for log in (export(row)+export(row),export(row).replace('CHUNK=1/','CHUNK=0/'),export(row).replace('export_rc=0','export_rc=1')):
        try:decode(log)
        except ValueError:negatives+=1
        else:raise AssertionError('Invalid transfer accepted')
    for n in ('m382_collect.py','m382_workflow.py','m382_support.py'):ast.parse((HERE/n).read_text(encoding='utf-8'),feature_version=(3,10))
    logs=[]
    for i,code in ((1,1),(2,0)):
        log=ROOT/f'tmp/m382/sudo_precheck_{i:02d}.log';assert f'__M382_CHECK_SUDO_RC_{code}__' in log.read_text(encoding='utf-8-sig');logs.append(dict(path=log.relative_to(ROOT).as_posix(),sha256=sha(log),sudo_rc=code))
    auth=BASE/'runs/M382-authorization-recovery-01/RESULT.json'
    ar=dict(status='PASS_HUMAN_SHELL_SUDO_RECOVERY',checks=logs,board_run=False,overlay_loaded=False)
    atomic(auth,encoded(ar),immutable=True);ad=sha(auth)
    sync('latest_m382_authorization',dict(status=ar['status'],result=auth.relative_to(ROOT).as_posix(),sha256=ad),f'## M382 COM3人工续期恢复\n\n首次sudo rc1未上传；用户续期后第二次同COM3 shell确认/sudo rc0。两份原日志保留，恢复 SHA {ad}；无Overlay/模型。')
    r=dict(status='PASS_OFFLINE_SEALED_PS_SLOT_CONTROL_RECOVERY',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),actual_frozen_scope_orchestration=True,actual_real_slot_bytearrays_and_weakrefs=True,explicit_fake_runtime_MMIO_memory=True,actual_five_blocked_paths_rejected=True,resident_identity_negative_checks=5,actual_idempotent_release_hooks=7,collector_synthetic_fixture_only=True,collector_negative_checks=negatives,controller_failure_collects=True,board_run=False,numerical_pass=False,performance_pass=False,source_sha256={n:sha(HERE/n) for n in ('m382_control.ps1','m382_workflow.py','m382_collect.py','m382_support.py','m382_ps_slot.py','test_m382_ps_slot.py')})
    path=BASE/'runs/M382-sealed-ps-slot-support-01/RESULT.json';atomic(path,encoded(r),immutable=True);digest=sha(path)
    sync('latest_m382_sealed_ps_slot_support',dict(status=r['status'],result=path.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256']),f'## M382 只加载PS slot控制及回收支持（2026-10-03）\n\n执行真实冻结gate的新编排＋实际bytearrays/weakrefs，memory/runtime/MMIO明确替身；五实际阻断入口、resident负例及七幂等释放钩子核对，{negatives}项collector负例拒绝，控制失败仍收集。支持 SHA {digest}。尚未上板；下一步唯一一次完整runtime/七DMA＋普通slot诊断，无forward/PL。')
    print('M382_SUPPORT_PASS',digest,negatives)
if __name__=='__main__':main()
