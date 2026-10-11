"""Controller and raw recovery fault tests with explicit synthetic evidence."""
import ast,base64,copy,hashlib,json,subprocess
from m351_workflow import ROOT,HERE,BASE,sha,encoded,atomic,sync
from m377_prepare import PKG,PRIOR,once
def main():
    s=(HERE/'m374_control.ps1').read_text(encoding='utf-8').replace('M374','M377').replace('m374','m377')
    s=s.replace('M377-layer-future-wait-01','M377-gate-up-pair-01').replace('/home/ubuntu/m377_layer_future_wait_candidate_01','/home/ubuntu/m377_gate_up_pair_candidate_01').replace('layer_wait','gate_up_pair').replace('M377-layer-wait-board-01','M377-gate-up-pair-board-01').replace('run_m377_staged_layer.sh','run_m377_gate_up_pair.sh').replace('ENABLE_STAGED_LAYER','ENABLE_GATE_UP_PAIR').replace('__M377_PRECHECK_SUDO_RC_0__','__M377_CHECK_SUDO_RC_0__')
    s=once(s,"if ($prep.manifest_sha256 -ne $digest)","$supportRaw=Get-Content -LiteralPath (Join-Path $workspace $support.result) -Raw -Encoding UTF8 | ConvertFrom-Json\nforeach ($property in $supportRaw.source_sha256.PSObject.Properties) {\n    if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $property.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $property.Value) { throw 'Support source drift' }\n}\nif ($prep.manifest_sha256 -ne $digest)")
    atomic(HERE/'m377_control.ps1',s.encode('utf-8'))
    workflow=(HERE/'m374_workflow.py').read_text(encoding='utf-8').replace('M374','M377').replace('m374','m377').replace('M377-layer-future-wait-01','M377-gate-up-pair-01').replace('M377-layer-wait-transfer-01','M377-gate-up-pair-transfer-01').replace('layer_wait','gate_up_pair')
    workflow=workflow.replace('30载荷','28载荷').replace('一次隔离单层观察','一次隔离gate_up family数值对照')
    atomic(HERE/'m377_workflow.py',workflow.encode('utf-8'))
    pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    p=subprocess.run([pwsh,'-NoProfile','-File',str(HERE/'m377_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    assert p.returncode==0 and 'M377_CONTROL_SELF_TEST_PASS' in p.stdout,p.stdout+p.stderr
    from m377_collect import decode
    from test_m377_gate_up_pair import Runtime,Policy,np
    from m377_gate_up_pair import run_pair
    pair=run_pair(Runtime(),Policy(),np.zeros((159,2560),np.float32))
    row=json.loads((BASE/'runs/M365-staged-layer-board-01/BOARD_RESULT.json').read_text(encoding='utf-8'))
    expected=json.loads((PKG/'LAYER_EXPECTED.json').read_text(encoding='utf-8'))
    target=next(f['output'] for f in expected['baseline']['families'] if f['family']=='gate_up')
    # Only collector shape/identity fixtures, not genuine hardware numerics.
    for p in pair['pairs']:
        p['input']=copy.deepcopy(expected['input_contract']['input_tensor']);p['outputs']=copy.deepcopy(target)
    t=next(t for t in row['transactions'] if t['family']=='gate_up');physical=pair['pairs'][0]['counts']['host_calls']
    row.update(status='PASS_M377_GATE_UP_PAIR_NUMERICAL',gate_level='independent-gate-up-family-pair',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),model_forward_calls=0,parser_capability_sha256=PRIOR,ps_prefetch_enabled=False,gate_up_family_pair_pass=True,family_pair=pair,logical_calls=10,host_calls=physical*2,transactions=[copy.deepcopy(t) for _ in range(physical*2)],fpga_transactions=physical*2+1)
    for label in ('before-gate-up-workers:1','after-gate-up-workers:1','before-gate-up-workers:2','after-gate-up-workers:2'):row['stage_memory'].append(dict(label=label,admission={}))
    def export(r):
        raw=encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M377_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM377_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M377_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(v).decode()+'\n' for i,v in enumerate(parts))+f'M377_DONE case=B1 gate_rc={r["gate_return_code"]} export_rc=0\n'
    assert decode(export(row))[2]==row
    fail=dict(row,status='FAIL',gate_return_code=1,errors=['deliberate failure']);assert decode(export(fail))[2]==fail
    bad=[]
    for k,v in [('model_forward_calls',1),('parser_capability_sha256','0'*64),('safe_buffers_released',False),('logical_calls',11),('host_calls',1),('fpga_transactions',1),('memory_capacity_proven',True),('performance_pass',True),('manifest_sha256','0'*64),('ps_prefetch_enabled',True),('stage_memory',[])]:bad.append(dict(row,**{k:v}))
    for kind in ('output','width','input','counts','retries','binding','pins','chain','release','monitor'):
        r=copy.deepcopy(row)
        if kind=='output':next(iter(r['family_pair']['pairs'][1]['outputs'].values()))['sha256']='0'*64
        elif kind=='width':
            for p in r['family_pair']['pairs']:next(iter(p['outputs'].values()))['shape']=[159,1]
        elif kind=='input':r['family_pair']['pairs'][0]['input']['sha256']='0'*64
        elif kind=='counts':
            for p in r['family_pair']['pairs']:p['counts']['parse_calls']=1
        elif kind=='retries':r['family_pair']['pairs'][1]['scale_attempts']=[]
        elif kind=='binding':r['family_pair']['pairs'][1]['scope']['bindings_restored']=False
        elif kind=='pins':r['family_pair']['pairs'][1]['scope']['source_sha256']={}
        elif kind=='chain':r['transactions'][0]['family']='q'
        elif kind=='release':r['released_buffers']=[]
        elif kind=='monitor':r['sampled_memory']['stop_reason']='fail'
        bad.append(r)
    negative=0
    for r in bad:
        try:decode(export(r))
        except ValueError:negative+=1
        else:raise AssertionError('Invalid evidence accepted')
    for log in (export(row)+export(row),export(row).replace('CHUNK=1/','CHUNK=0/'),export(row).replace('export_rc=0','export_rc=1'),export(row).replace('SAVED_GATE_RC=0','SAVED_GATE_RC=1')):
        try:decode(log)
        except ValueError:negative+=1
        else:raise AssertionError('Invalid transfer accepted')
    for n in ('m377_collect.py','m377_workflow.py','m377_support.py'):ast.parse((HERE/n).read_text(encoding='utf-8'),feature_version=(3,10))
    r=dict(status='PASS_OFFLINE_GATE_UP_PAIR_CONTROL_AND_RECOVERY',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),actual_pair_entry_fake_dma_policy=True,frozen_parser_actual_futures=True,collector_identity_fixture_explicit_synthetic=True,collector_negative_checks=negative,controller_failure_collects=True,python310_syntax=True,board_run=False,numerical_pass=False,performance_pass=False,source_sha256={n:sha(HERE/n) for n in ('m377_control.ps1','m377_workflow.py','m377_collect.py','m377_support.py','m377_gate_up_pair.py','m376_gate_up_workers.py')})
    path=BASE/'runs/M377-gate-up-pair-support-01/RESULT.json';atomic(path,encoded(r),immutable=True);digest=sha(path)
    sync('latest_m377_gate_up_pair_support',dict(status=r['status'],result=path.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256']),f'## M377 控制和原字节回收支持（2026-10-03）\n\n实际pair入口/原解析/Future以显式fake DMA/policy验证；数值几何回收fixture明确合成，不是新硬件证据。{negative}项错误身份/范围/输出/计数/重试/生命周期/分块负例拒绝，控制故意失败仍收集。支持 SHA {digest}；下一步COM3同终端sudo检查一次、manifest-first900B逐SHA上传后，一次family门禁。')
    print('M377_SUPPORT_PASS',digest,negative)
if __name__=='__main__':main()
