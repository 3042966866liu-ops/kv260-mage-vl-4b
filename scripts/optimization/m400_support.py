"""New layer envelope/actual assembly/control checks; reuse unchanged scope tests."""
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m400_collect import PKG,decode
OLD=BASE/'candidates/M399-tail-chain-01'
PS=Path(r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe')


def export(r):
    raw=encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    return 'M400_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM400_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M400_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode('ascii')+'\n' for i,p in enumerate(parts))+'M400_DONE case=B1 gate_rc='+str(r['gate_return_code'])+' export_rc=0\n'


def synthetic_layer():
    r=json.loads((BASE/'runs/M399-tail-chain-board-01/BOARD_RESULT.json').read_text(encoding='utf-8'))
    for key in ('chain_scope','chain_runtime_evidence','chain_call_delta','last31_chains','chain_numerical_pass'):r.pop(key,None)
    pin=json.loads((PKG/'TAIL_LAYER_PREREQUISITE.json').read_text(encoding='utf-8'));f=pin['reference_manifest']['fixtures']
    result=dict(families=pin['expected_families'],key=pin['expected_key'],value=pin['expected_value'],
                attended_full=f['attended_full']['tensor'],hidden_tail=f['hidden_tail']['tensor'],final_norm=f['final_norm']['tensor'],
                full_QKV_KV_SHA_equal=True,full_attention_and_tail_tensors_bitwise_equal=True,last_layer=35,original_tokens=159,tail_start=128,tail_tokens=31,grouped_attention_calls=1,LM_head_executed=False)
    counts=dict(logical_calls=8,host_calls=8,stage_bytes=53624832,scale_retry_count=0,pipeline_retry_launches=0,logical_expected_macros=81920000,expected_macros=81920000)
    r.update(status='PASS_M400_TAIL_LAYER_NUMERICAL',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),gate_level='sealed-DMA-isolated-layer35-fullAttention-last31',
             logical_calls=8,host_calls=8,fpga_transactions=9,isolated_layer_calls=1,chain_prerequisite_sha256=pin['chain_raw_sha256'],
             layer_numerical_pass=True,layer_result=result,transactions=pin['expected_transactions'],layer_call_delta=counts,
             layer_runtime_evidence=counts|dict(scale_attempts=pin['expected_scale_attempts']),
             layer_scope=dict(closed=True,retained=False,invoked=True,reference_sha256=pin['raw_sha256'],reference_files_checked=11,
                              reference_maps_released=True,binding_callback_removed=True,original_family_restored=True,family_rows=pin['expected_families'],layer_result=result,
                              extra_DMA=0,parser_workers=1,PS_prefetch=False,SiLU_workspace=False,candidate_full_model_executed=False,performance_pass=False))
    return r


def collector_tests():
    r=synthetic_layer();assert decode(export(r))[2]==r
    assert decode(export(dict(r,status='FAIL_UNSAFE_RETAINED',gate_return_code=1,errors=['EXPLICIT_FAKE_FAILURE'])))[2]['gate_return_code']==1
    bad=[]
    def mutate(key,value):
        q=copy.deepcopy(r);q[key]=value;bad.append(export(q))
    for key,value in [('manifest_sha256','0'*64),('case','A1'),('build_id','0'),('gate_level','wrong'),('gate_return_code',True),('memory_capacity_proven',True),
                      ('performance_pass',True),('formal_promotion_allowed',True),('errors',['error']),('unsafe_buffers_retained',True),('safe_buffers_released',False),
                      ('numerical_pass',False),('released_buffers',r['allocated_buffers']),('original_buffer_release_count',6),('model_forward_calls',1),('vision_forward_calls',1),
                      ('blocked_inference_attempts',['head']),('transactions',[]),('fpga_transactions',8),('logical_calls',7),('host_calls',7),('stable_overlay_reloaded',False),
                      ('boot_unchanged',False),('cmdline_unchanged',False),('patch_registry_cleared',False),('original_reference_sha256','bad'),('chain_prerequisite_sha256','bad'),
                      ('ps_prefetch_enabled',True),('worker_started',True),('scope_weakref_dead',False),('silu_workspace_enabled',True),('candidate_full_model_executed',True),
                      ('layer_numerical_pass',False),('isolated_layer_calls',2),('fixed_video_diagnostic_pass',True),('candidate_numerical_pass',True),('reference_capture_pass',True),
                      ('original_parser_workers',2),('extra_pynq_allocations',1),('diagnostic_ps_growth_limit_bytes',64<<20),('diagnostic_ps_available_margin_bytes',1),('additional_cma_requests_allowed',True)]:mutate(key,value)
    for key,value in [('closed',False),('retained',True),('invoked',False),('reference_maps_released',False),('binding_callback_removed',False),('original_family_restored',False),
                      ('reference_sha256','bad'),('reference_files_checked',10),('extra_DMA',1),('parser_workers',2),('PS_prefetch',True),('SiLU_workspace',True),('candidate_full_model_executed',True),('performance_pass',True)]:
        q=copy.deepcopy(r);q['layer_scope'][key]=value;bad.append(export(q))
    for key,value in [('last_layer',0),('original_tokens',31),('tail_start',0),('tail_tokens',32),('grouped_attention_calls',0),('LM_head_executed',True),('full_QKV_KV_SHA_equal',False),('full_attention_and_tail_tensors_bitwise_equal',False),('key',{}),('value',{}),('attended_full',{}),('hidden_tail',{}),('final_norm',{}),('families',[])]:
        q=copy.deepcopy(r);q['layer_result'][key]=value;bad.append(export(q))
    for place in ('layer_call_delta','layer_runtime_evidence'):
        for key,value in [('logical_calls',7),('host_calls',7),('stage_bytes',0),('scale_retry_count',1),('pipeline_retry_launches',1),('logical_expected_macros',0),('expected_macros',0)]:
            q=copy.deepcopy(r);q[place]=dict(q[place]);q[place][key]=value;bad.append(export(q))
    for key,value in [('input_bytes',0),('output_bytes',0),('chain_index',0),('method','head-original-execute')]:
        q=copy.deepcopy(r);q['transactions'][0][key]=value;bad.append(export(q))
    q=copy.deepcopy(r);q['layer_runtime_evidence']['scale_attempts']=[];bad.append(export(q))
    q=copy.deepcopy(r);q['layer_scope']['family_rows']=[];bad.append(export(q))
    q=copy.deepcopy(r)
    for place in ('layer_call_delta','layer_runtime_evidence'):q[place]['logical_expected_macros']=q[place]['expected_macros']=100
    bad.append(export(q))
    for kind in ('busy','monitor','memory','counter'):
        q=copy.deepcopy(r)
        if kind=='busy':q['final_snapshot']['mm2s_idle']=False;q['final_snapshot']['mm2s_dmasr']=4096
        elif kind=='monitor':q['sampled_memory']['observer_stopped']=False
        elif kind=='memory':q['stage_memory'][0]['admission']['observed_rss_growth_bytes']=1025<<20
        elif kind=='counter':q['stage_memory'][-1]['cma_counts']['reserved:alloc_pages_success']+=1
        bad.append(export(q))
    text=export(r);chunks=[s for s in text.splitlines(True) if 'RESULT_CHUNK' in s]
    bad.extend([text.replace(chunks[1],''),text+chunks[0],text.replace('RESULT_CHUNK=1/','RESULT_CHUNK=0/'),text.replace('export_rc=0','export_rc=1'),text.replace('M400_SAVED_GATE_RC=0','M400_SAVED_GATE_RC=1'),text.replace('M400_RESULT_SHA256=','M400_RESULT_SHA256=0')])
    for log in bad:
        try:decode(log)
        except (ValueError,KeyError,TypeError):pass
        else:raise AssertionError('Invalid saved layer metadata accepted')
    return len(bad)


def assembly_tests():
    spec=importlib.util.spec_from_file_location('actual_m400_assembly',PKG/'m400_assemble.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    assert mod.OLD.as_posix()=='/home/ubuntu/m399_tail_chain_candidate_01' and mod.OLD_SHA==sha(OLD/'PACKAGE_MANIFEST.json')
    assert "$remote='/home/ubuntu/m399_tail_chain_candidate_01'" in (HERE/'m399_control.ps1').read_text(encoding='utf-8-sig')
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'));old={f['path']:f for f in json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']}
    delta=[f['path'] for f in m['files'] if old.get(f['path'])!=f];root=ROOT/'tmp/m400/assembly-tests';root.mkdir(parents=True,exist_ok=True)
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
    p=subprocess.run([str(PS),'-NoProfile','-File',str(HERE/'m400_control.ps1'),'-Mode','List'],capture_output=True,text=True,encoding='utf-8',check=True)
    assert json.loads(p.stdout)==['PACKAGE_MANIFEST.json']+delta
    return len(delta)


def main():
    assert sha(PKG/'m400_tail_layer_scope.py')==sha(HERE/'m400_tail_layer_scope.py')
    assert sha(PKG/'m400_tail_layer_gate.py')==sha(ROOT/'tmp/m400/layer-draft/m400_tail_layer_gate.py')
    negative=collector_tests();delta=assembly_tests()
    p=subprocess.run([str(PS),'-NoProfile','-File',str(HERE/'m400_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8',check=True)
    assert 'M400_CONTROL_SELF_TEST_PASS' in p.stdout
    names=['m400_support.py','m400_control.ps1','m400_collect.py','m400_workflow.py','m400_prepare.py','m400_tail_layer_scope.py','test_m400_tail_layer_scope.py','test_m400_gate_region.py']
    value=dict(status='PASS_OFFLINE_LAST_LAYER_TAIL_CONTROL_RECOVERY',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),component_checks=7,actual_gate_region_checks=4,
               component_result='Direct command exit0: Ran7 tests in2.237s OK; actual NumPy full Attention/RMS/RoPE/SiLU, explicit fake Linear and memory. Same SHA reused without rerun.',
               gate_region_result='Direct command exit0: Ran4 tests in0.042s OK; actual generated region, explicit fake scope/DMA counters. Same SHA reused without rerun.',
               collector_negative_checks=negative,actual_assembly_checks=8,delta_files=delta,actual_prior_remote_verified=True,failed_gate_still_collected=True,
               source_sha256={n:sha(HERE/n) for n in names},synthetic_DMA_counter_metadata_explicit=True,board_run=False,layer_numerical_pass=False,full_model=False,performance_pass=False)
    out=BASE/'runs/M400-tail-layer-support-01/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    sync('latest_m400_tail_layer_support',dict(status=value['status'],manifest_sha256=value['manifest_sha256'],result=out.relative_to(ROOT).as_posix(),sha256=h),
         f'## M400 末层组合控制/回收支持（2026-10-04）\n\nSHA `{h}`；7项真实冻结loop/原PS数学/真实尺寸NPY和4项实际gate region检查通过，复用同SHA，不重跑。{negative}收集负例、8实际assembly、PS List/SelfTest通过；原chain远程根由实际M399控制/传输确定。Linear/DMA/内存/回收计数明确替身，尚无本级上板或性能。下一步同COM3 sudo后一次独立layer35门禁，已有run/result仅收集，失败停单层级；原生产政策/稳定回滚保持。')
    print(json.dumps(dict(status=value['status'],collector_negative_checks=negative,assembly_checks=8,delta_files=delta,result_sha256=h)))


if __name__=='__main__':main()
