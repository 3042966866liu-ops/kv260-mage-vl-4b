"""Video scope and saved-result control checks; explicit synthetic CPU fixtures."""
import ast,base64,copy,hashlib,json,subprocess
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m380_prepare import PKG,OLD,once
def main():
    prep=json.loads((BASE/'runs/M380-gate-up-video-preparation-01/RESULT.json').read_text(encoding='utf-8'));prior=prep['two_parser_text_sha256']
    controller=(HERE/'m379_control.ps1').read_text(encoding='utf-8').replace('M379','M380').replace('m379','m380').replace('M380-gate-up-text-01','M380-gate-up-video-01').replace('/home/ubuntu/m380_gate_up_text_candidate_01','/home/ubuntu/m380_gate_up_video_candidate_01').replace('latest_m380_gate_up_text','latest_m380_gate_up_video').replace('M380-gate-up-text-board-01','M380-gate-up-video-board-01').replace('run_m380_staged_text.sh','run_m380_staged_video.sh').replace('ENABLE_STAGED_LAYER','ENABLE_STAGED_VIDEO').replace('candidates/M366-staged-text-03/PACKAGE_MANIFEST.json','candidates/M368-staged-video-03/PACKAGE_MANIFEST.json').replace('-TimeoutSeconds 900', '-TimeoutSeconds 1200')
    atomic(HERE/'m380_control.ps1',controller.encode('utf-8'))
    workflow=(HERE/'m379_workflow.py').read_text(encoding='utf-8').replace('M379','M380').replace('m379','m380').replace('M380-gate-up-text-01','M380-gate-up-video-01').replace('candidates/M366-staged-text-03','candidates/M368-staged-video-03').replace('M380-gate-up-text-transfer-01','M380-gate-up-video-transfer-01').replace('latest_m380_gate_up_text','latest_m380_gate_up_video').replace('26载荷',str(json.loads((PKG/'PACKAGE_MANIFEST.json').read_text())['file_count'])+'载荷').replace('一次双worker固定文本数值门禁','一次双worker原159视频数值门禁')
    atomic(HERE/'m380_workflow.py',workflow.encode('utf-8'))
    collector=(HERE/'m36803_collect.py').read_text(encoding='utf-8').replace('M368','M380').replace('M380-staged-video-03','M380-gate-up-video-01').replace('M380-staged-video-board-02','M380-gate-up-video-board-01').replace('latest_m368_staged_layer_board','latest_m380_gate_up_video_board')
    collector=once(collector,'from board_safety import safe_to_release','from board_safety import safe_to_release\nfrom m376_gate_up_workers import PINNED')
    collector=once(collector,"        if not r['same_overlay_minimal_proof']['full_output_exact']", "        if r['two_parser_text_sha256']!='"+prior+"' or r['same_loading_path_video_sha256']!='"+prep['original_video_raw_sha256']+"' or r['ps_prefetch_enabled'] is not False:raise ValueError('New text/source prerequisite differs')\n        scope=r['parser_scope']\n        if any(scope[k]!=v for k,v in dict(parse_workers=2,gate_up_calls=36,bindings_restored=True,extra_dma_allocations=0,pending_output_slots=2,statistics_lock=True,source_sha256=PINNED,performance_pass=False).items()):raise ValueError('Parser ownership/coverage differs')\n        if not r['same_overlay_minimal_proof']['full_output_exact']")
    collector=collector.replace('下一步先视频裁决并同步；通过后才可准备轻量交错完整请求性能。','本次双解析worker视频完整数值；同步后才准备同Build单/双worker轻量交错完整请求性能，不复跑旧硬件八次对照。')
    atomic(HERE/'m380_collect.py',collector.encode('utf-8'))
    p=subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoProfile','-File',str(HERE/'m380_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8');assert p.returncode==0 and 'M380_CONTROL_SELF_TEST_PASS' in p.stdout,p.stdout+p.stderr
    from test_m376_gate_up_workers import FakeDMA,inputs,np,CHAIN
    runtime=FakeDMA(dict(CHAIN,groups=40));result={};captured={};labels=[];expected=json.loads((PKG/'VIDEO_EXPECTED.json').read_text(encoding='utf-8'))
    def fake_prefill(x):
        for layer in range(36):
            for family in (('q','kv','attention_out','gate_up','mlp_down') if layer<10 else ('qkv','attention_out','gate_up','mlp_down')):runtime.language_family_many(layer,family,x)
        return 15,None,None
    source=(PKG/'m380_staged_video_gate.py').read_text(encoding='utf-8');callback=next(n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.FunctionDef) and n.name=='observed_prefill')
    from types import SimpleNamespace
    namespace=dict(runtime=runtime,result=result,captured=captured,expected=expected,tensor=lambda value:expected['baseline']['input'],policy=SimpleNamespace(capture=lambda label,check:labels.append(label)),original_prefill=fake_prefill)
    exec(compile(ast.Module(body=[callback],type_ignores=[]),'actual-new-video-prefill-scope','exec'),namespace);namespace['observed_prefill'](inputs(159,2560))
    assert result['parser_scope']['gate_up_calls']==36 and result['parser_scope']['bindings_restored'] and result['model_forward_calls']==1 and len(labels)==2 and 'language_family_many' not in vars(runtime)
    from m380_collect import decode
    row=json.loads((BASE/'runs/M368-staged-video-board-02/BOARD_RESULT.json').read_text(encoding='utf-8'));row.update(status='PASS_M380_FIXED_VIDEO_DIAGNOSTIC',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),two_parser_text_sha256=prior,same_loading_path_video_sha256=prep['original_video_raw_sha256'],parser_scope=result['parser_scope'],ps_prefetch_enabled=False)
    def export(r):
        raw=encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M380_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM380_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M380_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(v).decode()+'\n' for i,v in enumerate(parts))+f'M380_DONE case=B1 gate_rc={r["gate_return_code"]} export_rc=0\n'
    assert decode(export(row))[2]==row;assert decode(export(dict(row,status='FAIL',gate_return_code=1,errors=['deliberate failure'])))[2]['gate_return_code']==1
    bad=[]
    for k,v in [('two_parser_text_sha256','0'*64),('same_loading_path_video_sha256','0'*64),('ps_prefetch_enabled',True),('model_forward_calls',0),('safe_buffers_released',False),('fpga_transactions',0),('memory_capacity_proven',True),('performance_pass',True),('manifest_sha256','0'*64),('video_result',{})]:bad.append(dict(row,**{k:v}))
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
    for n in ('m380_collect.py','m380_workflow.py','m380_support.py'):ast.parse((HERE/n).read_text(encoding='utf-8'),feature_version=(3,10))
    r=dict(status='PASS_OFFLINE_TWO_WORKER_VIDEO_SCOPE_CONTROL_RECOVERY',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),actual_prefill_scope_orchestration=True,fake_dma_model_input_identity_explicit=True,real_original_parser_futures=True,collector_old_video_reference_fixture_only=True,collector_negative_checks=count,controller_failure_collects=True,rejected_attempts=['Offline support fake chain groups1 expected64 columns while actual callback159x2560; rejected before any upload. Corrected explicit fake groups40 only; frozen package/helper unchanged.'],board_run=False,numerical_pass=False,performance_pass=False,source_sha256={n:sha(HERE/n) for n in ('m380_control.ps1','m380_workflow.py','m380_collect.py','m380_support.py','m376_gate_up_workers.py')})
    p=BASE/'runs/M380-gate-up-video-support-01/RESULT.json';atomic(p,encoded(r),immutable=True);digest=sha(p);sync('latest_m380_gate_up_video_support',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256']),f'## M380 双解析worker视频支持（2026-10-03）\n\n实际新包observed_prefill编排、原解析/Future执行154family及36gate_up，显式fake DMA/model/input identity，不冒称视频数值。旧完整视频参考仅collector fixture；{count}项负例拒绝，故意失败仍收集。支持 SHA {digest}。下一步一次原159视频完整数值。')
    print('M380_SUPPORT_PASS',digest,count)
if __name__=='__main__':main()
