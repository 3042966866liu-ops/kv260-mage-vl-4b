"""Actual package assembly, source-region guards and strict saved recovery tests."""
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m399_collect import PKG,decode
from m399_tail_chain_scope import PLAN
OLD=BASE/'candidates/M398-tail-reference-01'
PS=Path(r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe')

def export(r):
    raw=encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    return 'M399_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM399_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M399_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode('ascii')+'\n' for i,p in enumerate(parts))+'M399_DONE case=B1 gate_rc='+str(r['gate_return_code'])+' export_rc=0\n'

def synthetic_chains():
    original=json.loads((BASE/'runs/M398-tail-reference-board-01/BOARD_RESULT.json').read_text(encoding='utf-8'));r=copy.deepcopy(original)
    for k in ('video_result','visual_features','visual_exact_comparison','exact_comparison','prompt_token_ids','preprocessed','candidate_semantic','events','decoder','reference_capture','reference_capture_pass','candidate_numerical_pass','fixed_video_diagnostic_pass','tail_candidate_executed','head_observer_proof'):r.pop(k,None)
    f=original['reference_capture']['fixtures'];rows=[];transactions=[]
    for family,source,goldens in PLAN:
        rows.append(dict(layer=35,family=family,original_token_start=128,local_token_start=0,tokens=31,input=f[source]['tensor'],output={'model.language_model.layers.35.'+key:f[name]['tensor'] for key,name in goldens.items()},full_output_bitwise_equal=True))
        transactions.append([t for t in original['transactions'] if t['layer']==35 and t['family']==family][-1])
    delta=dict(logical_calls=3,host_calls=3,stage_bytes=45268992,scale_retry_count=0,pipeline_retry_launches=0,logical_expected_macros=42598400,expected_macros=42598400)
    # Explicit synthetic counters, not a board launch or macro-cost proof.
    r.update(status='PASS_M399_LAST31_CHAIN_NUMERICAL',gate_level='sealed-DMA-isolated-last31-three-chains',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
             original_reference_sha256=sha(BASE/'runs/M398-tail-reference-board-01/BOARD_RESULT.json'),model_forward_calls=0,vision_forward_calls=0,
             candidate_full_model_executed=False,chain_numerical_pass=True,logical_calls=3,host_calls=3,fpga_transactions=4,transactions=transactions,
             last31_chains=rows,chain_call_delta=delta,chain_runtime_evidence=delta,chain_scope=dict(closed=True,retained=False,reference_sha256=sha(BASE/'runs/M398-tail-reference-board-01/BOARD_RESULT.json'),
             reference_files_checked=7,reference_maps_released=True,chains=rows,extra_DMA=0,original_parser_workers=1,PS_prefetch=False,SiLU_workspace=False,full_model_candidate_executed=False,performance_pass=False))
    return r

def collector_tests():
    r=synthetic_chains();assert decode(export(r))[2]==r
    failure=dict(r,status='FAIL_UNSAFE_RETAINED',gate_return_code=1,errors=['EXPLICIT_FAKE_CONSUMER_ERROR']);assert decode(export(failure))[2]==failure
    bad=[]
    for key,value in [('manifest_sha256','0'*64),('case','A1'),('build_id','0'),('gate_level','wrong'),('gate_return_code',True),('memory_capacity_proven',True),
                      ('performance_pass',True),('formal_promotion_allowed',True),('errors',['error']),('unsafe_buffers_retained',True),('safe_buffers_released',False),
                      ('numerical_pass',False),('released_buffers',r['allocated_buffers']),('original_buffer_release_count',6),('model_forward_calls',1),('vision_forward_calls',1),
                      ('blocked_inference_attempts',['head']),('transactions',[]),('fpga_transactions',5),('logical_calls',4),('host_calls',4),('stable_overlay_reloaded',False),
                      ('boot_unchanged',False),('patch_registry_cleared',False),('original_reference_sha256','bad'),('ps_prefetch_enabled',True),('worker_started',True),
                      ('scope_weakref_dead',False),('silu_workspace_enabled',True),('candidate_full_model_executed',True),('chain_numerical_pass',False),
                      ('fixed_video_diagnostic_pass',True),('candidate_numerical_pass',True),('reference_capture_pass',True),('original_parser_workers',2),('extra_pynq_allocations',1),
                      ('diagnostic_ps_growth_limit_bytes',64<<20),('diagnostic_ps_available_margin_bytes',1),('additional_cma_requests_allowed',True)]:
        q=copy.deepcopy(r);q[key]=value;bad.append(export(q))
    for key,value in [('closed',False),('retained',True),('reference_maps_released',False),('reference_sha256','bad'),('reference_files_checked',6),('extra_DMA',1),
                      ('original_parser_workers',2),('PS_prefetch',True),('SiLU_workspace',True),('full_model_candidate_executed',True),('performance_pass',True)]:
        q=copy.deepcopy(r);q['chain_scope'][key]=value;bad.append(export(q))
    for key,value in [('tokens',32),('layer',0),('original_token_start',0),('local_token_start',128),('family','q'),('full_output_bitwise_equal',False),('input',{}),('output',{})]:
        q=copy.deepcopy(r);q['chain_scope']['chains'][0][key]=value;bad.append(export(q))
    for container in ('chain_call_delta','chain_runtime_evidence'):
        for key,value in [('logical_calls',4),('host_calls',4),('stage_bytes',0),('scale_retry_count',1),('pipeline_retry_launches',1),('expected_macros',0)]:
            q=copy.deepcopy(r);q[container]=dict(q[container]);q[container][key]=value;bad.append(export(q))
    for key,value in [('input_bytes',0),('output_bytes',0),('chain_index',0),('method','head-original-execute')]:
        q=copy.deepcopy(r);q['transactions'][0][key]=value;bad.append(export(q))
    q=copy.deepcopy(r)
    for key in ('chain_call_delta','chain_runtime_evidence'):
        q[key]['logical_expected_macros']=q[key]['expected_macros']=100
    bad.append(export(q))
    for kind in ('busy','monitor','memory','counter'):
        q=copy.deepcopy(r)
        if kind=='busy':q['final_snapshot']['mm2s_idle']=False;q['final_snapshot']['mm2s_dmasr']=4096
        elif kind=='monitor':q['sampled_memory']['observer_stopped']=False
        elif kind=='memory':q['stage_memory'][0]['admission']['observed_rss_growth_bytes']=1025<<20
        elif kind=='counter':q['stage_memory'][-1]['cma_counts']['reserved:alloc_pages_success']+=1
        bad.append(export(q))
    text=export(r);chunks=[s for s in text.splitlines(True) if 'RESULT_CHUNK' in s]
    bad.extend([text.replace(chunks[1],''),text+chunks[0],text.replace('RESULT_CHUNK=1/','RESULT_CHUNK=0/'),text.replace('export_rc=0','export_rc=1'),
                text.replace('M399_SAVED_GATE_RC=0','M399_SAVED_GATE_RC=1'),text.replace('M399_RESULT_SHA256=','M399_RESULT_SHA256=0')])
    for log in bad:
        try:decode(log)
        except (ValueError,KeyError,TypeError):pass
        else:raise AssertionError('Invalid saved chain metadata accepted')
    return len(bad)

def assembly_tests():
    spec=importlib.util.spec_from_file_location('actual_m399_assembly',PKG/'m399_assemble.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    assert mod.OLD.as_posix()=='/home/ubuntu/m398_tail_reference_candidate_01' and mod.OLD_SHA==sha(OLD/'PACKAGE_MANIFEST.json')
    assert "$remote='/home/ubuntu/m398_tail_reference_candidate_01'" in (HERE/'m398_control.ps1').read_text(encoding='utf-8-sig')
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'));old={f['path']:f for f in json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']}
    delta=[f['path'] for f in m['files'] if old.get(f['path'])!=f];root=ROOT/'tmp/m399/assembly-tests';root.mkdir(parents=True,exist_ok=True)
    for kind in ('good','old_manifest','source','missing','extra','count','bytes','traversal'):
        with tempfile.TemporaryDirectory(dir=root) as d:
            base=Path(d).resolve();assert base.parent==root.resolve();prior=base/'old';dest=base/'new';prior.mkdir();dest.mkdir()
            for p in OLD.iterdir():
                if p.is_file():(prior/p.name).write_bytes(p.read_bytes())
            for name in ['PACKAGE_MANIFEST.json']+delta:(dest/name).write_bytes((PKG/name).read_bytes())
            mm=copy.deepcopy(m)
            if kind=='old_manifest':(prior/'PACKAGE_MANIFEST.json').write_bytes(b'bad')
            elif kind=='source':(prior/next(f['path'] for f in m['files'] if f['path'] not in delta)).write_bytes(b'bad')
            elif kind=='missing':(dest/delta[0]).unlink()
            elif kind=='extra':(dest/'extra').write_bytes(b'x')
            elif kind=='count':mm['file_count']+=1
            elif kind=='bytes':mm['total_bytes']+=1
            elif kind=='traversal':mm['files'][0]['path']='../escape'
            if mm!=m:(dest/'PACKAGE_MANIFEST.json').write_bytes(encoded(mm))
            mod.HERE=dest;mod.OLD=prior
            try:mod.main(sha(dest/'PACKAGE_MANIFEST.json'))
            except RuntimeError:
                if kind=='good':raise
            else:
                if kind!='good':raise AssertionError('Assembly accepted '+kind)
    p=subprocess.run([str(PS),'-NoProfile','-File',str(HERE/'m399_control.ps1'),'-Mode','List'],capture_output=True,text=True,encoding='utf-8',check=True)
    assert json.loads(p.stdout)==['PACKAGE_MANIFEST.json']+delta
    return len(delta)

def main():
    assert sha(PKG/'m399_tail_chain_scope.py')==sha(HERE/'m399_tail_chain_scope.py')
    assert sha(PKG/'m399_tail_chain_gate.py')==sha(ROOT/'tmp/m399/chain-draft/m399_tail_chain_gate.py')
    negative=collector_tests()
    prior_path=BASE/'runs/M399-tail-chain-support-01/RESULT.json'
    assert sha(prior_path)=='08b0a016dcfd0547964c2eec7bfd352926d7774611675836501ea2c9c2180fbf'
    prior=json.loads(prior_path.read_text(encoding='utf-8'))
    assert prior['manifest_sha256']==sha(PKG/'PACKAGE_MANIFEST.json') and prior['actual_assembly_checks']==8
    for name in ('m399_control.ps1','m399_workflow.py','m399_prepare.py','m399_tail_chain_scope.py','test_m399_tail_chain_scope.py','test_m399_gate_region.py'):
        assert sha(HERE/name)==prior['source_sha256'][name]
    delta=prior['delta_files']
    p=subprocess.run([str(PS),'-NoProfile','-File',str(HERE/'m399_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8',check=True)
    assert 'M399_CONTROL_SELF_TEST_PASS' in p.stdout
    names=['m399_support.py','m399_control.ps1','m399_collect.py','m399_workflow.py','m399_prepare.py','m399_tail_chain_scope.py','test_m399_tail_chain_scope.py','test_m399_gate_region.py']
    value=dict(status='PASS_OFFLINE_LAST31_CHAIN_CONTROL_RECOVERY',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),component_checks=6,actual_gate_region_checks=4,
               collector_negative_checks=negative,actual_assembly_checks=8,delta_files=delta,actual_prior_remote_verified=True,failed_gate_still_collected=True,
               source_sha256={n:sha(HERE/n) for n in names},synthetic_DMA_counter_metadata_explicit=True,board_run=False,chain_numerical_pass=False,full_model=False,performance_pass=False)
    value['prior_support_sha256']=sha(prior_path)
    value['collector_macro_validation']='Exact 42598400 from pinned M396 three original chain costs; equal-but-wrong counters also rejected.'
    out=BASE/'runs/M399-tail-chain-support-02/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    sync('latest_m399_tail_chain_support',dict(status=value['status'],manifest_sha256=value['manifest_sha256'],result=out.relative_to(ROOT).as_posix(),sha256=h),
         f'## M399 三末31 chain回收计数收紧（2026-10-04）\n\nSHA `{h}`，新{negative}收集负例通过；宏计数须等于固定M396三chain总42598400，拒绝两份计数都相等但错误的100替身。复用01同manifest/同SHA的6组件、4实际region、8assembly与控制证据，PS List/SelfTest保持；未改冻结载荷、未重跑已过组件或硬件。DMA/Linear/内存/合成回收明确替身，不是板端数值或性能。COM3 sudo已过期/没有上传，等人工续期后唯一下一步一次三末31 chain；原M398参考PASS、生产政策/稳定回滚保持。')
    print(json.dumps(dict(status=value['status'],collector_negative_checks=negative,assembly_checks=8,delta_files=delta,result_sha256=h)))

if __name__=='__main__':main()
