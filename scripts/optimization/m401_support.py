"""Test new full Prefill binding and actual fixed-text envelope before upload."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m400_support import export
from m401_collect import decode,PKG,PROOF

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def main():
    # Run changed binding with actual frozen36-layer source and real dimension
    # NumPy/packet tests. Linear, attention, DMA and memory are explicit fakes.
    suite=load('m401_actual_test_suite',HERE/'test_m397_last_layer_tail.py')
    scope=load('m401_actual_scope',PKG/'m401_prefill_tail_scope.py')
    old_scope=suite.LastLayerTailScope;old_error=suite.RetainedTailOwnerError
    suite.LastLayerTailScope=scope.LastLayerTailScope;suite.RetainedTailOwnerError=scope.RetainedTailOwnerError
    old_path=list(__import__('sys').path);__import__('sys').path.insert(0,str(PKG))
    selected=['test_fixed30_has_no_crop_and_same_control','test_real_size_synthetic159_control_and_packet_bits','test_consumer_failure_retains_owner_and_callback','test_unsafe_head_completion_retains_owner','test_wrong_module_dimensions_and_second_binding_refused']
    tests=unittest.TestSuite(suite.Tests(n) for n in selected)
    result=unittest.TextTestRunner(verbosity=1).run(tests)
    assert result.wasSuccessful() and result.testsRun==5
    __import__('sys').path[:]=old_path;suite.LastLayerTailScope=old_scope;suite.RetainedTailOwnerError=old_error
    entry=load('m401_actual_entry',PKG/'m401_text_entry.py')
    source=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/deployment/mage_vl4b/m242_m241_fixed_text_board_candidate/m241_video_language_runtime.py'
    with patch.object(entry,'SOURCE',source):assert entry.precheck(sha(PKG/'PACKAGE_MANIFEST.json'))==PROOF
    with patch.object(entry,'SOURCE',source.with_name('MISSING')),patch.object(entry.importlib.util,'spec_from_file_location',side_effect=AssertionError('Hardware imported before source check')) as blocked,patch.object(entry.sys,'argv',['entry',sha(PKG/'PACKAGE_MANIFEST.json'),'B1','--enable-tail-text']):
        try:entry.main()
        except FileNotFoundError:pass
        else:raise AssertionError('Missing source accepted')
        blocked.assert_not_called()
    original=json.loads((BASE/'runs/M366-staged-text-board-02/BOARD_RESULT.json').read_text(encoding='utf-8'))
    r=copy.deepcopy(original)
    r.update(status='PASS_M401_TAIL_TEXT_NUMERICAL',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),gate_level='sealed-DMA-fixed30-full36-layer-tail-prefill',source_precheck_before_hardware_import=PROOF,
             layer_prerequisite_sha256='bca7bf2b4c6de4a4e861448162ce9a97da32e82fd68bf7af0dcf9c8eedde089c',layer_closure_sha256='64acc9f2174e95c241b26f91cb328f732105d766751c0092d0ce0c8a3d608043',
             tail_scope=dict(plan=dict(tokens=30,tail_start=0,tail_count=30,original_logical=162,logical=162),selected=[dict(layer=35,original_token_start=0,local_token_start=0,token_count=30,original_dma_slot=0,candidate_dma_slot=0)],invoked=True,closed=True,retained=False,binding_callback_removed=True,extra_dma_allocations=0,ps_prefetch=False,parser_workers=1,silu_workspace=False),
             candidate_full_model_executed=True,scope_weakref_dead=True,patch_registry_cleared=True,original_buffer_release_count=7,extra_pynq_allocations=0,ps_prefetch_enabled=False,silu_workspace_enabled=False,original_parser_workers=1,
             diagnostic_ps_growth_limit_bytes=1024<<20,diagnostic_ps_available_margin_bytes=64<<20,additional_cma_requests_allowed=False)
    # Synthetic policy evidence is explicitly constructed; not a board observation.
    for point in r['stage_memory']:
        if point['admission']:
            d=point['admission'];d['required_mem_available_bytes']=(1024<<20)-d['observed_rss_growth_bytes']+(64<<20);d['mem_available_bytes']=max(d['mem_available_bytes'],d['required_mem_available_bytes'])
    def emit(q):return export(q).replace('M400','M401')
    assert decode(emit(r))[2]==r
    negatives=0
    for key,value in [('source_precheck_before_hardware_import',{}),('layer_prerequisite_sha256','bad'),('tail_scope',{}),('scope_weakref_dead',False),('transactions',[]),('extra_pynq_allocations',1),('host_calls',164),('released_buffers',[]),('layer_result',{}),('candidate_full_model_executed',False),('diagnostic_ps_growth_limit_bytes',256<<20),('patch_registry_cleared',False),('stable_bit_sha256','bad')]:
        q=copy.deepcopy(r);q[key]=value
        try:decode(emit(q))
        except (ValueError,KeyError):negatives+=1
        else:raise AssertionError('Bad complete text accepted: '+key)
    fail=dict(r,status='FAIL_UNSAFE_RETAINED',gate_return_code=1,errors=['EXPLICIT_FAKE_FAILURE'])
    assert decode(emit(fail))[2]['gate_return_code']==1
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'));old=BASE/'candidates/M400-tail-layer-02';previous={x['path']:x for x in json.loads((old/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']}
    delta=[x['path'] for x in m['files'] if previous.get(x['path'])!=x]
    assembly=load('actual_m401_assembly',PKG/'m401_assemble.py')
    assert assembly.OLD.as_posix()=='/home/ubuntu/m400_tail_layer_candidate_02' and assembly.OLD_SHA==sha(old/'PACKAGE_MANIFEST.json')
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp/m400') as d:
        assembly.HERE=dest=Path(d);assembly.OLD=old
        for n in ['PACKAGE_MANIFEST.json']+delta:(dest/n).write_bytes((PKG/n).read_bytes())
        assembly.main(sha(dest/'PACKAGE_MANIFEST.json'))
    PS=r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
    for mode in ('SelfTest','List'):
        p=subprocess.run([PS,'-NoProfile','-File',str(HERE/'m401_control.ps1'),'-Mode',mode],capture_output=True,text=True,encoding='utf-8',check=True)
        assert ('M401_CONTROL_SELF_TEST_PASS' in p.stdout) if mode=='SelfTest' else json.loads(p.stdout)==['PACKAGE_MANIFEST.json']+delta
    runner=(PKG/'run_m401_tail_text.sh').read_text(encoding='utf-8');gate=(PKG/'m401_tail_text_gate.py').read_text(encoding='utf-8')
    assert 'm401_text_entry.py' in runner and 'm401_tail_text_gate.py' not in runner
    assert "unsafe=unsafe or layer_scope is not None" in gate and 'del candidate' in gate and 'scope_ref() is not None' in gate
    assert gate.index('SOURCE_PRECHECK_PROOF')<gate.index('EVIDENCE.mkdir')<gate.index('pynq.allocate')
    # Reuse unchanged14 actual head dispatch checks / same source; no hardware rerun.
    assert sha(PKG/'m366_head_observer.py')==sha(BASE/'candidates/M366-staged-text-03/m366_head_observer.py')
    for x in json.loads((PKG/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))['prerequisites']:assert sha(ROOT/x['path'])==x['sha256']
    for n in ('m401_collect.py','m401_support.py','m401_workflow.py','m401_prepare.py'):ast.parse((HERE/n).read_text(encoding='utf-8'),feature_version=(3,10))
    draft=BASE/'runs/M401-tail-text-draft-01/RESULT.json';p=json.loads(draft.read_text(encoding='utf-8'))
    p.update(status='PASS_OFFLINE_M401_FIXED_TEXT_PREPARATION',support_pass=True)
    out=BASE/'runs/M401-tail-text-preparation-01/RESULT.json';atomic(out,encoded(p),immutable=True)
    h=sha(out);sync('latest_m401_tail_text_preparation',dict(status=p['status'],result=out.relative_to(ROOT).as_posix(),sha256=h,manifest_sha256=p['manifest_sha256']),f'## M401 固定文本准备（2026-10-04）\n\nSHA `{h}`，manifest `{p["manifest_sha256"]}`；前级M400单层闭合确认，完整30-token/36层/完整head，162逻辑/165模型物理/3重试加minimal166，154family/151936logits/72KV全SHA核对。新stdlib完整Prefill源码检查先于硬件导入/Overlay/DMA，原七DMA封锁、PS增长1GiB/普通余量64MiB诊断政策复用，生产64MiB保持。新包默认关闭；尚未上传/上板，无视频/性能。')
    names=['m401_collect.py','m401_support.py','m401_workflow.py','m401_control.ps1','m401_prepare.py','m401_prefill_source.py']
    value=dict(status='PASS_OFFLINE_M401_SCOPE_CONTROL_AND_RECOVERY',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),source_sha256={n:sha(HERE/n) for n in names},actual_scope_checks=5,collector_negative_checks=negatives,actual_PS_List_and_SelfTest=True,actual_assembly_pass=True,preentry_actual_package_pass=True,prior_14_head_checks_same_SHA_reused=True,same_SHA_hardware_reused=True,delta_files=delta,explicit_fake_Linear_Attention_DMA_memory=True,board_run=False,performance_pass=False)
    support=BASE/'runs/M401-tail-text-support-01/RESULT.json';atomic(support,encoded(value),immutable=True);h=sha(support)
    sync('latest_m401_tail_text_support',dict(status=value['status'],result=support.relative_to(ROOT).as_posix(),sha256=h,manifest_sha256=value['manifest_sha256']),f'## M401 完整Prefill控制/回收支持（2026-10-04）\n\nSHA `{h}`；实际新绑定5项完整冻结36层/真实尺寸/原PS数学与包字节测试、13项回收拒绝、实际包pre-entry及拒绝前无硬件导入、新源assembly和PS List/SelfTest通过。Linear/Attention/DMA/内存明确替身；原14项head实际执行器/同SHA硬件证据复用。下一步同COM3 sudo及900B上传，一次固定文本；已有run/result只Collect。')
    print(json.dumps(value|{'support_sha256':h}))

if __name__=='__main__':main()
