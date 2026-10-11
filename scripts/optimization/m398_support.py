"""Offline control/recovery tests. Metadata and DMA remain explicit fakes."""
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
from m398_collect import PKG,decode
from m398_reference_capture import SHAPES,PAYLOAD_BYTES
OLD=BASE/'candidates/M387-ps-video-01'
PS=Path(r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe')

def export(r):
    raw=encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    return 'M398_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM398_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M398_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode('ascii')+'\n' for i,p in enumerate(parts))+'M398_DONE case=B1 gate_rc='+str(r['gate_return_code'])+' export_rc=0\n'

def synthetic_reference():
    r=json.loads((BASE/'runs/M394-silu-video-board-01/BOARD_RESULT.json').read_text(encoding='utf-8'))
    expected=json.loads((PKG/'VIDEO_EXPECTED.json').read_text(encoding='utf-8'))['baseline']
    fixtures={}
    for name,shape in SHAPES.items():
        size=4
        for d in shape:size*=d
        tensor=dict(shape=list(shape),dtype='float32',bytes=size,sha256='a'*64)
        if name=='logits':tensor=copy.deepcopy(expected['logits'])
        if name=='attended_full':tensor=copy.deepcopy(expected['families'][-3]['input'])
        fixtures[name]=dict(path='/home/ubuntu/m398_tail_reference_01/B1/'+name+'.npy',file_bytes=size+128,file_sha256='b'*64,tensor=tensor,
                            original_token_start=128 if name.endswith('_tail') else 158 if name in ('final_norm','logits') else 0)
    r.update(status='PASS_M398_ORIGINAL_TAIL_REFERENCE',gate_level='sealed-DMA-original-fixed159-tail-reference',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
             tail_capture_prerequisite_sha256='17817f223700a901e924af4c01dd30b1497b1052c6df03acd9bbfef5e4b96250',
             ps_prefetch_enabled=False,worker_started=False,scope_weakref_dead=True,silu_workspace_enabled=False,tail_candidate_executed=False,
             candidate_numerical_pass=False,reference_capture_pass=True,reference_capture=dict(fixtures=fixtures,file_count=12,payload_bytes=PAYLOAD_BYTES,
             file_bytes=sum(f['file_bytes'] for f in fixtures.values()),file_budget_bytes=16<<20,last_families=['attention_out','gate_up','mlp_down'],
             steps=['full-attention','full-hidden','original-final-norm'],closed=True,retained=False,binding_callback_removed=True,
             additional_dma_allocations=0,source_hooks=3,removed_hooks_ast_equals_original=True,candidate_tail_not_executed=True))
    r.pop('silu_scope',None);r.pop('silu_text_prerequisite_sha256',None)
    return r

def collector_tests():
    r=synthetic_reference();assert decode(export(r))[2]==r
    failed=dict(r,status='FAIL_UNSAFE_RETAINED',gate_return_code=1,errors=['EXPLICIT_FAKE_CONSUMER_ERROR'])
    assert decode(export(failed))[2]==failed
    bad=[]
    for key,value in [('manifest_sha256','0'*64),('case','A1'),('build_id','0'),('gate_level','wrong'),('gate_return_code',True),
                      ('memory_capacity_proven',True),('performance_pass',True),('formal_promotion_allowed',True),('errors',['error']),
                      ('unsafe_buffers_retained',True),('safe_buffers_released',False),('numerical_pass',False),('released_buffers',r['allocated_buffers']),
                      ('original_buffer_release_count',6),('model_forward_calls',2),('video_result',{}),('blocked_inference_attempts',['head']),
                      ('transactions',[]),('fpga_transactions',25),('stable_overlay_reloaded',False),('boot_unchanged',False),('patch_registry_cleared',False),
                      ('tail_capture_prerequisite_sha256','bad'),('ps_prefetch_enabled',True),('worker_started',True),('scope_weakref_dead',False),
                      ('silu_workspace_enabled',True),('tail_candidate_executed',True),('candidate_numerical_pass',True),('reference_capture_pass',False),
                      ('original_parser_workers',2),('extra_pynq_allocations',1),('diagnostic_ps_growth_limit_bytes',64<<20),
                      ('diagnostic_ps_available_margin_bytes',1),('additional_cma_requests_allowed',True),('visual_features',{}),
                      ('prompt_token_ids',[]),('vision_forward_calls',0),('candidate_semantic',{}),('decoder',{}),('same_loading_path_video_sha256','bad'),('preprocessed',{}),('events',[])]:
        q=copy.deepcopy(r);q[key]=value;bad.append(export(q))
    for key,value in [('closed',False),('retained',True),('binding_callback_removed',False),('additional_dma_allocations',1),('source_hooks',2),
                      ('removed_hooks_ast_equals_original',False),('candidate_tail_not_executed',False),('file_count',11),('payload_bytes',0),
                      ('file_budget_bytes',1),('file_bytes',0),('last_families',[]),('steps',[])]:
        q=copy.deepcopy(r);q['reference_capture'][key]=value;bad.append(export(q))
    for key,value in [('path','/wrong/gate_tail.npy'),('file_sha256','bad'),('file_bytes',0),('original_token_start',0)]:
        q=copy.deepcopy(r);q['reference_capture']['fixtures']['gate_tail'][key]=value;bad.append(export(q))
    for key,value in [('shape',[1,9728]),('dtype','float64'),('bytes',0),('sha256','bad')]:
        q=copy.deepcopy(r);q['reference_capture']['fixtures']['gate_tail']['tensor'][key]=value;bad.append(export(q))
    for name in ('attended_full','logits'):
        q=copy.deepcopy(r);q['reference_capture']['fixtures'][name]['tensor']['sha256']='c'*64;bad.append(export(q))
    q=copy.deepcopy(r);del q['reference_capture']['fixtures']['hidden_tail'];bad.append(export(q))
    q=copy.deepcopy(r);q['head_observer_proof']['every_retry_physical_boundary']=False;bad.append(export(q))
    for kind in ('busy','monitor','memory','counter'):
        q=copy.deepcopy(r)
        if kind=='busy':q['final_snapshot']['mm2s_idle']=False;q['final_snapshot']['mm2s_dmasr']=4096
        elif kind=='monitor':q['sampled_memory']['observer_stopped']=False
        elif kind=='memory':q['stage_memory'][0]['admission']['observed_rss_growth_bytes']=1025<<20
        elif kind=='counter':q['stage_memory'][-1]['cma_counts']['reserved:alloc_pages_success']+=1
        bad.append(export(q))
    text=export(r);chunks=[s for s in text.splitlines(True) if 'RESULT_CHUNK' in s]
    bad.extend([text.replace(chunks[1],''),text+chunks[0],text.replace('RESULT_CHUNK=1/','RESULT_CHUNK=0/'),text.replace('export_rc=0','export_rc=1'),
                text.replace('M398_SAVED_GATE_RC=0','M398_SAVED_GATE_RC=1'),text.replace('M398_RESULT_SHA256=','M398_RESULT_SHA256=0')])
    for log in bad:
        try:decode(log)
        except (ValueError,KeyError,TypeError):pass
        else:raise AssertionError('Invalid metadata accepted')
    return len(bad)

def assembly_tests():
    spec=importlib.util.spec_from_file_location('actual_m398_assembly',PKG/'m398_assemble.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    assert mod.OLD.as_posix()=='/home/ubuntu/m387_ps_video_candidate_01' and mod.OLD_SHA==sha(OLD/'PACKAGE_MANIFEST.json')
    assert "$remote='/home/ubuntu/m387_ps_video_candidate_01'" in (HERE/'m387_control_recovered_02.ps1').read_text(encoding='utf-8-sig')
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'));old={r['path']:r for r in json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']}
    delta=[r['path'] for r in m['files'] if old.get(r['path'])!=r]
    root=ROOT/'tmp/m398/assembly-tests';root.mkdir(parents=True,exist_ok=True)
    for kind in ('good','old_manifest','source','missing','extra','count','bytes','traversal'):
        with tempfile.TemporaryDirectory(dir=root) as d:
            base=Path(d).resolve();assert base.parent==root.resolve();prior=base/'old';dest=base/'new';prior.mkdir();dest.mkdir()
            for p in OLD.iterdir():
                if p.is_file():(prior/p.name).write_bytes(p.read_bytes())
            for name in ['PACKAGE_MANIFEST.json']+delta:(dest/name).write_bytes((PKG/name).read_bytes())
            mm=copy.deepcopy(m)
            if kind=='old_manifest':(prior/'PACKAGE_MANIFEST.json').write_bytes(b'bad')
            elif kind=='source':(prior/next(r['path'] for r in m['files'] if r['path'] not in delta)).write_bytes(b'bad')
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
    p=subprocess.run([str(PS),'-NoProfile','-File',str(HERE/'m398_control.ps1'),'-Mode','List'],capture_output=True,text=True,encoding='utf-8',check=True)
    assert json.loads(p.stdout)==['PACKAGE_MANIFEST.json']+delta
    return len(delta)

def main():
    assert sha(HERE/'m398_reference_capture.py')==sha(PKG/'m398_reference_capture.py')
    assert sha(ROOT/'tmp/m398/capture-draft/m398_tail_reference_gate.py')==sha(PKG/'m398_tail_reference_gate.py')
    log=ROOT/'tmp/m398/frozen-wrapper-tests.log'
    if not log.exists():
        p=subprocess.run([sys.executable,'-X','utf8','-B',str(HERE/'test_m398_gate_wrapper.py')],capture_output=True,text=True,encoding='utf-8')
        atomic(log,(p.stdout+p.stderr).encode('utf-8'),immutable=True);assert p.returncode==0
    content=log.read_text(encoding='utf-8');assert 'Ran 4 tests' in content and content.rstrip().endswith('OK')
    negative=collector_tests();delta=assembly_tests()
    p=subprocess.run([str(PS),'-NoProfile','-File',str(HERE/'m398_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8',check=True)
    assert 'M398_CONTROL_SELF_TEST_PASS' in p.stdout
    names=['m398_support.py','m398_control.ps1','m398_collect.py','m398_workflow.py','test_m398_reference_capture.py','test_m398_gate_wrapper.py','m398_reference_capture.py','m398_prepare.py','m398_generate_collector.py']
    value=dict(status='PASS_OFFLINE_ORIGINAL_TAIL_CAPTURE_CONTROL_RECOVERY',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
               actual_frozen_wrapper_tests=4,component_tests_previously_passed=6,collector_negative_checks=negative,actual_assembly_checks=8,delta_files=delta,
               actual_PS_list_and_prior_remote=True,failed_gate_still_collected=True,source_sha256={n:sha(HERE/n) for n in names},test_log_sha256=sha(log),
               metadata_DMA_attention_memory_fakes_explicit=True,board_run=False,candidate_tail_executed=False,candidate_numerical_pass=False,performance_pass=False,
               rejected_status_draft_sha256=sha(ROOT/'tmp/m398/rejected_status_draft.py'),
               rejected_host_paths='Host-only copied silu-video path labels corrected to frozen tail-reference before upload; immutable payload unchanged.')
    out=BASE/'runs/M398-tail-reference-support-01/RESULT.json';atomic(out,encoded(value),immutable=True);d=sha(out)
    sync('latest_m398_tail_reference_support',dict(status=value['status'],manifest_sha256=value['manifest_sha256'],result=out.relative_to(ROOT).as_posix(),sha256=d),
         f'## M398 原末层参考捕获控制与回收支持（2026-10-04）\n\n4项冻结wrapper检查，复用此前6项同SHA组件检查，{negative}回收负例、8实际assembly、PS List/SelfTest和实际M387目录核对通过，SHA `{d}`。拒绝草稿状态名及host路径复制遗漏已离线纠正，冻结载荷保持。DMA/Attention/内存/合成回收字段明确替身，非上板数值或性能。COM3已确认shell但sudo过期，未上传/执行；等人工恢复后同终端一次sudo核对，原完整159参考捕获一次，候选尾批未运行。')
    print(json.dumps(dict(status=value['status'],collector_negative_checks=negative,assembly_checks=8,delta_files=delta,result_sha256=d)))

if __name__=='__main__':main()
