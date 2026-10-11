"""Fixed-text new scope/control/collection support with declared CPU fixtures."""
import ast,base64,copy,hashlib,json,subprocess,textwrap
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m379_prepare import PKG,OLD,once
def main():
    prep=json.loads((BASE/'runs/M379-gate-up-text-preparation-01/RESULT.json').read_text(encoding='utf-8'));prior=prep['two_parser_layer_sha256']
    controller=(HERE/'m378_control.ps1').read_text(encoding='utf-8').replace('M378','M379').replace('m378','m379').replace('M379-gate-up-layer-01','M379-gate-up-text-01').replace('/home/ubuntu/m379_gate_up_layer_candidate_01','/home/ubuntu/m379_gate_up_text_candidate_01').replace('latest_m379_gate_up_layer','latest_m379_gate_up_text').replace('M379-gate-up-layer-board-01','M379-gate-up-text-board-01').replace('run_m379_staged_layer.sh','run_m379_staged_text.sh').replace('candidates/M377-gate-up-pair-01/PACKAGE_MANIFEST.json','candidates/M366-staged-text-03/PACKAGE_MANIFEST.json')
    atomic(HERE/'m379_control.ps1',controller.encode('utf-8'))
    workflow=(HERE/'m378_workflow.py').read_text(encoding='utf-8').replace('M378','M379').replace('m378','m379').replace('M379-gate-up-layer-01','M379-gate-up-text-01').replace('candidates/M377-gate-up-pair-01','candidates/M366-staged-text-03').replace('M379-gate-up-layer-transfer-01','M379-gate-up-text-transfer-01').replace('latest_m379_gate_up_layer','latest_m379_gate_up_text').replace('27载荷',str(json.loads((PKG/'PACKAGE_MANIFEST.json').read_text())['file_count'])+'载荷').replace('一次双worker单层数值门禁','一次双worker固定文本数值门禁')
    atomic(HERE/'m379_workflow.py',workflow.encode('utf-8'))
    collector=(HERE/'m36603_collect.py').read_text(encoding='utf-8').replace('M366','M379').replace('M379-staged-text-03','M379-gate-up-text-01').replace('M379-staged-text-board-02','M379-gate-up-text-board-01').replace('latest_m366_staged_layer_board','latest_m379_gate_up_text_board')
    collector=once(collector,'from board_safety import safe_to_release','from board_safety import safe_to_release\nfrom m376_gate_up_workers import PINNED')
    collector=once(collector,"        if not r['same_overlay_minimal_proof']['full_output_exact']", "        if r['two_parser_layer_sha256']!='"+prior+"' or r['ps_prefetch_enabled'] is not False:raise ValueError('New layer prerequisite/scope differs')\n        scope=r['parser_scope']\n        if any(scope[k]!=v for k,v in dict(parse_workers=2,gate_up_calls=36,bindings_restored=True,extra_dma_allocations=0,pending_output_slots=2,statistics_lock=True,source_sha256=PINNED,performance_pass=False).items()):raise ValueError('Parser ownership/coverage differs')\n        if not r['same_overlay_minimal_proof']['full_output_exact']")
    collector=collector.replace('下一步先固定文本解读并同步，真实视频需独立论证与新包，不能自动扩大。','本次双解析worker固定文本正确性；同步后才能冻结原159视频数值门禁，新增性能仍待验证。')
    atomic(HERE/'m379_collect.py',collector.encode('utf-8'))
    p=subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoProfile','-File',str(HERE/'m379_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8');assert p.returncode==0 and 'M379_CONTROL_SELF_TEST_PASS' in p.stdout,p.stdout+p.stderr
    from test_m376_gate_up_workers import FakeDMA,inputs
    runtime=FakeDMA();result={}
    class Model:
        def prefill(self,x):
            for layer in range(36):
                for family in (('q','kv','attention_out','gate_up','mlp_down') if layer<10 else ('qkv','attention_out','gate_up','mlp_down')):runtime.language_family_many(layer,family,x)
            return 17,None,None
    source=(PKG/'m379_staged_text_gate.py').read_text(encoding='utf-8');start=source.index('        from m376_gate_up_workers import GateUpWorkers');end=source.index("        policy.capture('after-fixed-text'",start)
    namespace=dict(runtime=runtime,result=result,model=Model(),hidden=inputs(30));exec(compile(textwrap.dedent(source[start:end]),'actual-new-fixed-text-scope','exec'),namespace)
    assert result['parser_scope']['gate_up_calls']==36 and result['parser_scope']['bindings_restored'] and 'language_family_many' not in vars(runtime)
    from m379_collect import decode
    row=json.loads((BASE/'runs/M366-staged-text-board-02/BOARD_RESULT.json').read_text(encoding='utf-8'));row.update(status='PASS_M379_FIXED_TEXT_DIAGNOSTIC',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),two_parser_layer_sha256=prior,parser_scope=result['parser_scope'],ps_prefetch_enabled=False)
    def export(r):
        raw=encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M379_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM379_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M379_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(v).decode()+'\n' for i,v in enumerate(parts))+f'M379_DONE case=B1 gate_rc={r["gate_return_code"]} export_rc=0\n'
    assert decode(export(row))[2]==row;assert decode(export(dict(row,status='FAIL',gate_return_code=1,errors=['deliberate failure'])))[2]['gate_return_code']==1
    bad=[]
    for k,v in [('two_parser_layer_sha256','0'*64),('ps_prefetch_enabled',True),('model_forward_calls',0),('safe_buffers_released',False),('fpga_transactions',0),('memory_capacity_proven',True),('performance_pass',True),('manifest_sha256','0'*64),('layer_result',{})]:bad.append(dict(row,**{k:v}))
    for k,v in [('parse_workers',1),('gate_up_calls',35),('bindings_restored',False),('extra_dma_allocations',1),('source_sha256',{})]:
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
    for n in ('m379_collect.py','m379_workflow.py','m379_support.py'):ast.parse((HERE/n).read_text(encoding='utf-8'),feature_version=(3,10))
    r=dict(status='PASS_OFFLINE_TWO_WORKER_TEXT_SCOPE_CONTROL_RECOVERY',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),actual_scope_orchestration=True,fake_dma_and_model_callable_explicit=True,real_original_parser_futures=True,collector_old_text_reference_fixture_only=True,collector_negative_checks=count,controller_failure_collects=True,board_run=False,numerical_pass=False,performance_pass=False,source_sha256={n:sha(HERE/n) for n in ('m379_control.ps1','m379_workflow.py','m379_collect.py','m379_support.py','m376_gate_up_workers.py')})
    p=BASE/'runs/M379-gate-up-text-support-01/RESULT.json';atomic(p,encoded(r),immutable=True);digest=sha(p);sync('latest_m379_gate_up_text_support',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256']),f'## M379 固定文本双worker支持（2026-10-03）\n\n实际scope编排配显式fake DMA/model callable，原解析/Future执行154family、36次gate_up双worker并恢复；旧完整文本参考仅collector fixture。{count}项负例拒绝，故意失败仍收集。支持 SHA {digest}。下一步一次真实固定文本完整数值。')
    print('M379_SUPPORT_PASS',digest,count)
if __name__=='__main__':main()
