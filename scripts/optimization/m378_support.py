"""Changed single-layer scope and collector fault checks, explicit CPU fixtures."""
import ast,base64,copy,hashlib,json,subprocess
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m378_prepare import PKG,OLD,once
def main():
    prep=json.loads((BASE/'runs/M378-gate-up-layer-preparation-01/RESULT.json').read_text(encoding='utf-8'));prior=prep['family_pair_prerequisite_sha256']
    s=(HERE/'m377_control.ps1').read_text(encoding='utf-8').replace('M377','M378').replace('m377','m378').replace('M378-gate-up-pair-01','M378-gate-up-layer-01').replace('/home/ubuntu/m378_gate_up_pair_candidate_01','/home/ubuntu/m378_gate_up_layer_candidate_01').replace('latest_m378_gate_up_pair','latest_m378_gate_up_layer').replace('M378-gate-up-pair-board-01','M378-gate-up-layer-board-01').replace('run_m378_gate_up_pair.sh','run_m378_staged_layer.sh').replace('ENABLE_GATE_UP_PAIR','ENABLE_STAGED_LAYER').replace('candidates/M365-staged-layer-03/PACKAGE_MANIFEST.json','candidates/M377-gate-up-pair-01/PACKAGE_MANIFEST.json')
    atomic(HERE/'m378_control.ps1',s.encode('utf-8'))
    workflow=(HERE/'m377_workflow.py').read_text(encoding='utf-8').replace('M377','M378').replace('m377','m378').replace('M378-gate-up-pair-01','M378-gate-up-layer-01').replace('candidates/M365-staged-layer-03','candidates/M377-gate-up-pair-01').replace('M378-gate-up-pair-transfer-01','M378-gate-up-layer-transfer-01').replace('latest_m378_gate_up_pair','latest_m378_gate_up_layer').replace('28载荷','27载荷').replace('一次隔离gate_up family数值对照','一次双worker单层数值门禁')
    atomic(HERE/'m378_workflow.py',workflow.encode('utf-8'))
    collector=(HERE/'m365_collect.py').read_text(encoding='utf-8').replace('M365','M378').replace('M378-staged-layer-03','M378-gate-up-layer-01').replace('M378-staged-layer-board-01','M378-gate-up-layer-board-01').replace('latest_m365_staged_layer_board','latest_m378_gate_up_layer_board')
    collector=once(collector,'from board_safety import safe_to_release','from board_safety import safe_to_release\nfrom m376_gate_up_workers import PINNED')
    collector=once(collector,"        if not r['same_overlay_minimal_proof']['full_output_exact']", "        if r['family_pair_prerequisite_sha256']!='"+prior+"' or r['ps_prefetch_enabled'] is not False:raise ValueError('Family prerequisite/scope differs')\n        scope=r['parser_scope']\n        if any(scope[k]!=v for k,v in dict(parse_workers=2,gate_up_calls=1,bindings_restored=True,extra_dma_allocations=0,pending_output_slots=2,statistics_lock=True,source_sha256=PINNED,performance_pass=False).items()):raise ValueError('Parser binding/scope differs')\n        if not r['same_overlay_minimal_proof']['full_output_exact']")
    collector=collector.replace('下一步先单层解读并同步，固定文本需独立论证与新包，不能自动扩大。','此处仅双worker单层数值；同步后准备原固定文本完整数值，不宣称新增性能。')
    atomic(HERE/'m378_collect.py',collector.encode('utf-8'))
    pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe';p=subprocess.run([pwsh,'-NoProfile','-File',str(HERE/'m378_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8');assert p.returncode==0 and 'M378_CONTROL_SELF_TEST_PASS' in p.stdout,p.stdout+p.stderr
    from test_m376_gate_up_workers import FakeDMA,inputs
    source=(PKG/'m378_staged_layer_gate.py').read_text(encoding='utf-8');tree=ast.parse(source)
    runtime=FakeDMA();result={};namespace=dict(runtime=runtime,result=result,model=None,hidden=inputs(159),one_layer=lambda model,values:([runtime.language_family_many(0,f,values) for f in ('q','kv','attention_out','gate_up','mlp_down')],None))
    # Execute actual scope orchestration lines from the package, real frozen parser/Futures, fake DMA.
    lines=source[source.index('        from m376_gate_up_workers import GateUpWorkers'):source.index('        policy.capture(\'after-layer0\'',source.index('        from m376_gate_up_workers import GateUpWorkers'))]
    import textwrap
    exec(compile(textwrap.dedent(lines),'actual-new-layer-scope','exec'),namespace)
    assert result['parser_scope']['bindings_restored'] and result['parser_scope']['gate_up_calls']==1 and 'language_family_many' not in vars(runtime)
    from m378_collect import decode
    row=json.loads((BASE/'runs/M365-staged-layer-board-01/BOARD_RESULT.json').read_text(encoding='utf-8'));row.update(status='PASS_M378_SINGLE_LAYER_DIAGNOSTIC',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),family_pair_prerequisite_sha256=prior,parser_scope=result['parser_scope'],ps_prefetch_enabled=False)
    def export(r):
        raw=encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M378_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM378_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M378_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(v).decode()+'\n' for i,v in enumerate(parts))+f'M378_DONE case=B1 gate_rc={r["gate_return_code"]} export_rc=0\n'
    assert decode(export(row))[2]==row;assert decode(export(dict(row,status='FAIL',gate_return_code=1,errors=['deliberate failure'])))[2]['gate_return_code']==1
    bad=[]
    for k,v in [('family_pair_prerequisite_sha256','0'*64),('ps_prefetch_enabled',True),('model_forward_calls',0),('safe_buffers_released',False),('fpga_transactions',0),('memory_capacity_proven',True),('performance_pass',True),('manifest_sha256','0'*64),('layer_result',{})]:bad.append(dict(row,**{k:v}))
    for k,v in [('parse_workers',1),('gate_up_calls',2),('bindings_restored',False),('extra_dma_allocations',1),('source_sha256',{})]:
        x=copy.deepcopy(row);x['parser_scope'][k]=v;bad.append(x)
    count=0
    for r in bad:
        try:decode(export(r))
        except ValueError:count+=1
        else:raise AssertionError('Invalid result accepted')
    for log in (export(row)+export(row),export(row).replace('CHUNK=1/','CHUNK=0/'),export(row).replace('export_rc=0','export_rc=1')):
        try:decode(log)
        except ValueError:count+=1
        else:raise AssertionError('Invalid transfer accepted')
    for n in ('m378_collect.py','m378_workflow.py','m378_support.py'):ast.parse((HERE/n).read_text(encoding='utf-8'),feature_version=(3,10))
    r=dict(status='PASS_OFFLINE_TWO_WORKER_LAYER_SCOPE_CONTROL_RECOVERY',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),actual_scope_orchestration=True,fake_dma_and_layer_callable_explicit=True,real_original_parser_futures=True,collector_layer_reference_fixture_reused_only=True,collector_negative_checks=count,controller_failure_collects=True,board_run=False,numerical_pass=False,performance_pass=False,source_sha256={n:sha(HERE/n) for n in ('m378_control.ps1','m378_workflow.py','m378_collect.py','m378_support.py','m376_gate_up_workers.py')})
    p=BASE/'runs/M378-gate-up-layer-support-01/RESULT.json';atomic(p,encoded(r),immutable=True);digest=sha(p);sync('latest_m378_gate_up_layer_support',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256']),f'## M378 单层双worker控制/回收支持（2026-10-03）\n\n真实新包scope编排、原解析/Future、显式fake DMA/layer callable验证五family，仅gate_up变2线程并恢复；复用旧层参考的collector fixture不是新硬件证据。{count}项负例拒绝，故意失败仍收集。支持 SHA {digest}。下一步只一次真实单层数值门禁。')
    print('M378_SUPPORT_PASS',digest,count)
if __name__=='__main__':main()
