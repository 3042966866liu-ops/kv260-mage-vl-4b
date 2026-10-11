"""Generate fail-closed layer control/collector and verify changed scope."""
import ast,base64,copy,hashlib,json,subprocess,sys
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m385_prepare import PKG,OLD,RAW,once
def main():
    s=(HERE/'m384_control.ps1').read_text(encoding='utf-8').replace('M384','M385').replace('m384','m385').replace('M385-ps-chain-01','M385-ps-layer-02').replace('M385-ps-chain','M385-ps-layer').replace('m385_ps_chain','m385_ps_layer').replace('latest_m385_ps_chain','latest_m385_ps_layer').replace('ENABLE_PS_CHAIN','ENABLE_PS_LAYER').replace('candidates/M383-ps-descriptor-01','candidates/M384-ps-chain-01')
    atomic(HERE/'m385_control.ps1',s.encode('utf-8'))
    s=(HERE/'m384_workflow.py').read_text(encoding='utf-8').replace('M384','M385').replace('m384','m385').replace('M385-ps-chain-01','M385-ps-layer-02').replace('M385-ps-chain','M385-ps-layer').replace('latest_m385_ps_chain','latest_m385_ps_layer').replace('candidates/M383-ps-descriptor-01','candidates/M384-ps-chain-01').replace('27载荷','31载荷').replace('精确M383','精确M384').replace('完整chain','单层五窗口').replace('完整chain完整输出','单层完整数值')
    atomic(HERE/'m385_workflow.py',s.encode('utf-8'))
    s=(HERE/'m365_collect.py').read_text(encoding='utf-8').replace('M365','M385').replace('M385-staged-layer-03','M385-ps-layer-02').replace('M385-staged-layer-board-01','M385-ps-layer-board-01').replace('latest_m365_staged_layer_board','latest_m385_ps_layer_board').replace('PASS_M385_SINGLE_LAYER_DIAGNOSTIC','PASS_M385_PS_LAYER_NUMERICAL').replace('independent-single-layer-capacity-diagnostic','sealed-DMA-PS-single-layer-numerical')
    s=once(s,'from board_safety import safe_to_release','from board_safety import safe_to_release\nfrom m365_stage_policy import assess,SHAPES')
    s=once(s,"        if not r['same_overlay_minimal_proof']['full_output_exact']",'''        if r['chain_prerequisite_sha256']!='''+repr(RAW)+''' or not r['ps_prefetch_enabled'] or not r['session_weakref_dead'] or not r['patch_registry_cleared'] or not r['worker_started'] or r['extra_pynq_allocations'] or r['original_parser_workers']!=1:raise ValueError('PS prerequisite/scope/lifetime differs')
        p=r['ps_session'];c=p['component']
        required=dict(status='COMPLETE_COMPONENT_ONLY',stages=5,submissions=5,ps_payload_bytes=27852800,extra_cma_allocation_calls=0,total_weight_bytes=expected['stage_bytes'],open_files=0,live_views=0,performance_pass=False,hardware_contract_changed=False)
        if any(c[k]!=v for k,v in required.items()) or p['production_policy_changed'] or p['additional_dma_allocations'] or not p['source_component_unchanged']:raise ValueError('PS plan/accounting differs')
        if p['slot_release']!=dict(released_ports=4,bytearrays_sole_owned_before_release=True,all_owner_weakrefs_dead=True,explicit_gc_or_trim=False):raise ValueError('PS slot release differs')
        if p['budget_growth_bytes']!=256<<20 or p['available_margin_bytes']!=64<<20:raise ValueError('Combined layer budget differs')
        if len(p['independent_memory_checks'])<9:raise ValueError('PS memory coverage absent')
        counts=p['independent_memory_checks'][0]['cma_counts']
        for x in p['independent_memory_checks']:
            actual=assess(x['memory'],p['budget_baseline_rss'],x['cma_counts'],counts,sealed=True,buffer_bytes=SHAPES)
            if x['decision']!=actual:raise ValueError('PS actual admission differs')
        for x in r['stage_memory']:
            if x['admission'] is not None:
                actual=assess(x['memory'],p['budget_baseline_rss'],x['cma_counts'],counts,sealed=True,buffer_bytes=SHAPES)
                if x['admission']!=actual:raise ValueError('Physical/family memory decision differs')
        if not r['same_overlay_minimal_proof']['full_output_exact']''')
    s=s.replace('只layer0/159重复文本embedding，非视频','只layer0/159重复文本embedding和五窗口PS预读，原单parser，非视频').replace('下一步先单层解读并同步，固定文本需独立论证与新包，不能自动扩大。','下一步仅本级数值和生命周期闭合，之后准备固定文本；容量或生命周期问题停止扩大。')
    atomic(HERE/'m385_collect.py',s.encode('utf-8'))
    py=subprocess.run([sys.executable,'-X','utf8','-B',str(HERE/'test_m385_layer_ps_read.py')],capture_output=True,text=True,encoding='utf-8')
    if py.returncode:raise RuntimeError(py.stdout+py.stderr)
    pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    ctl=subprocess.run([pwsh,'-NoProfile','-File',str(HERE/'m385_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    assert ctl.returncode==0 and 'M385_CONTROL_SELF_TEST_PASS' in ctl.stdout,ctl.stdout+ctl.stderr
    from m385_collect import decode
    row=json.loads((BASE/'runs/M378-gate-up-layer-board-01/BOARD_RESULT.json').read_text(encoding='utf-8'))
    row.pop('parser_scope');row.update(status='PASS_M385_PS_LAYER_NUMERICAL',gate_level='sealed-DMA-PS-single-layer-numerical',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),chain_prerequisite_sha256=RAW,ps_prefetch_enabled=True,session_weakref_dead=True,patch_registry_cleared=True,worker_started=True,extra_pynq_allocations=0,original_parser_workers=1)
    baseline=row['stage_memory'][0]['memory']['process_bytes']['VmRSS']
    first=next(x for x in row['stage_memory'] if x['label']=='diagnostic-admission-after-seven-real-buffers');baseline=first['memory']['process_bytes']['VmRSS'];counts=first['cma_counts']
    checks=[dict(before_payload=False,memory=x['memory'],decision=x['admission'],cma_counts=x['cma_counts']) for x in row['stage_memory'] if x['admission']]
    row['ps_session']=dict(component=dict(status='COMPLETE_COMPONENT_ONLY',stages=5,submissions=5,ps_payload_bytes=27852800,extra_cma_allocation_calls=0,total_weight_bytes=row['layer_result']['stage_bytes'],open_files=0,live_views=0,performance_pass=False,hardware_contract_changed=False),budget_growth_bytes=256<<20,available_margin_bytes=64<<20,budget_baseline_rss=baseline,independent_memory_checks=checks,slot_release=dict(released_ports=4,bytearrays_sole_owned_before_release=True,all_owner_weakrefs_dead=True,explicit_gc_or_trim=False),production_policy_changed=False,additional_dma_allocations=0,source_component_unchanged=True)
    def export(r):
        raw=encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M385_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM385_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M385_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(v).decode()+'\n' for i,v in enumerate(parts))+f'M385_DONE case=B1 gate_rc={r["gate_return_code"]} export_rc=0\n'
    assert decode(export(row))[2]==row
    assert decode(export(dict(row,status='FAIL',gate_return_code=1,errors=['deliberate'])))[2]['gate_return_code']==1
    bad=[]
    for k,v in [('chain_prerequisite_sha256','0'*64),('ps_prefetch_enabled',False),('session_weakref_dead',False),('original_parser_workers',2),('extra_pynq_allocations',1),('patch_registry_cleared',False),('layer_result',{}),('fpga_transactions',0),('safe_buffers_released',False),('performance_pass',True),('manifest_sha256','0'*64)]:bad.append(dict(row,**{k:v}))
    for k,v in [('budget_growth_bytes',320<<20),('available_margin_bytes',0),('budget_baseline_rss',0),('slot_release',{}),('independent_memory_checks',[])]:
        x=copy.deepcopy(row);x['ps_session'][k]=v;bad.append(x)
    for k,v in [('stages',4),('submissions',6),('total_weight_bytes',0),('open_files',1),('live_views',1)]:
        x=copy.deepcopy(row);x['ps_session']['component'][k]=v;bad.append(x)
    x=copy.deepcopy(row);x['ps_session']['independent_memory_checks'][0]['cma_counts']={};bad.append(x)
    for x in bad:
        try:decode(export(x))
        except (ValueError,RuntimeError,KeyError,MemoryError):pass
        else:raise AssertionError('Invalid layer result accepted')
    for log in [export(row)+export(row),export(row).replace('CHUNK=1/','CHUNK=0/'),export(row).replace('export_rc=0','export_rc=1')]:
        try:decode(log)
        except ValueError:pass
        else:raise AssertionError('Invalid raw accepted')
    names=('m385_control.ps1','m385_workflow.py','m385_collect.py','m385_support.py','m385_layer_ps_read.py','test_m385_layer_ps_read.py','m385_prepare.py')
    for n in names:
        if n.endswith('.py'):ast.parse((HERE/n).read_text(encoding='utf-8'),feature_version=(3,10))
    r=dict(status='PASS_OFFLINE_PS_LAYER_SCOPE_BUDGET_CONTROL_RECOVERY',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),new_adapter_tests=8,test_output=py.stderr,actual_frozen_five_window_orchestration=True,real_fixture_read_copy_weakrefs=True,explicit_fake_DMA_layer_math_memory=True,collector_previous_layer_fixture_only=True,collector_negative_checks=len(bad)+3,controller_failure_collects=True,board_run=False,numerical_pass=False,performance_pass=False,source_sha256={n:sha(HERE/n) for n in names})
    p=BASE/'runs/M385-ps-layer-support-01/RESULT.json';atomic(p,encoded(r),immutable=True);d=sha(p)
    sync('latest_m385_ps_layer_support',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=d,manifest_sha256=r['manifest_sha256']),f'## M385 PS单层控制及新准入闭合（2026-10-03）\n\n实际冻结五窗口编排＋真实fixture/read/copy/weakref，新256MiB共用预算8项检查及{len(bad)+3}回收负例；DMA/层数学/内存明确替身，非数值上板证据。故意失败始终收集，支持SHA {d}。初次离线遗漏层binder已拒绝保留SHA b36d0c26813218c854ac6790eea3dafba0526513562ecd1d4a8b0df8e57eb63e，新02补齐missing0；旧01不上板。下一步一次原单层PS数值门禁，生命周期/容量失败停止扩大。')
    print('M385_SUPPORT_PASS',d,len(bad)+3)
if __name__=='__main__':main()
