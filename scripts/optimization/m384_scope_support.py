"""Execute actual new gate scope; explicit fake pack/MMIO/golden/memory only."""
import ast,base64,copy,hashlib,json,os,subprocess,tempfile,textwrap,types,weakref
from pathlib import Path
from unittest.mock import patch
import numpy as np
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m384_prepare import PKG,OLD
from m383_sealed_ps_read import SealedPSReadSession
from m370_patch_scope import PatchScope
from test_m382_ps_slot import memory
from board_safety import safe_to_release
import ps_read_ahead as original
def main():
    pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    p=subprocess.run([pwsh,'-NoProfile','-File',str(HERE/'m384_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8');assert p.returncode==0 and 'M384_CONTROL_SELF_TEST_PASS' in p.stdout,p.stdout+p.stderr
    source=(PKG/'m384_ps_chain_gate.py').read_text(encoding='utf-8');tree=ast.parse(source)
    ns={};node=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='forbid');exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-forbid','exec'),ns)
    class Array(np.ndarray):
        def sync_to_device(self):pass
        def sync_from_device(self):pass
    def array(n):return np.zeros(n,np.uint8).view(Array)
    safe=dict(ap_ctrl=4,ap_return=0x4d333537,mm2s_dmasr=4098,s2mm_dmasr=4098,mm2s_idle=True,s2mm_idle=True,mm2s_error=False,s2mm_error=False,kernel_read_error='',return_read_error='',dma_read_error='')
    candidate=BASE/'candidates/M357-private-activation-01';packet=(candidate/'q_packet.bin').read_bytes();golden=(candidate/'q_golden.bin').read_bytes()
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory);fixture=bytes(range(256))*2880
        for i in range(4):(root/f'weights{i}.bin').write_bytes(fixture)
        layout=types.SimpleNamespace(root=root,manifest=dict(files=[dict(path=f'weights{i}.bin',bytes=len(fixture)) for i in range(4)]))
        buffers=[array(n) for n in [6963200]*4+[389152,2621440,2621440]]
        runtime=types.SimpleNamespace(_m365_closed=False,host_calls=0,logical_calls=0,stage_bytes=0,stage_ms=0,weight_mode='staged-low-cma',maximum_weight_window_bytes=6963200,language_layout=layout,staged_buffers=buffers[:4],input_buffer=buffers[4],output_buffer=buffers[5],output_buffer_alt=buffers[6],kernel=types.SimpleNamespace(write=lambda *a:None),dma=types.SimpleNamespace(sendchannel=types.SimpleNamespace(transfer=lambda *a,**kw:None),recvchannel=types.SimpleNamespace(transfer=lambda *a,**kw:None)),allocate=lambda *a:None)
        def stage(layout,chain):
            for b in runtime.staged_buffers:b[:len(fixture)]=np.frombuffer(fixture,np.uint8)
            runtime.stage_bytes+=4*len(fixture);return runtime.staged_buffers,0
        runtime._stage=stage
        engine=types.SimpleNamespace(board=runtime,language=object(),vision=object(),tokenizer=object())
        policy=types.SimpleNamespace(sealed=True,build=0x4d333537,active=False,ever=True,completed=True,snapshot=lambda:memory(),counters=lambda:{'success':7},safe=lambda:not policy.active,capture=lambda *a:memory(),begin_sampling=lambda:None,stop_sampling=lambda:None)
        def complete(*a):runtime.output_buffer[:len(golden)]=np.frombuffer(golden,np.uint8);return dict(safe)
        base=types.SimpleNamespace(chain_window=lambda *a:(0,len(fixture)),pack_chain_input=lambda *a,**kw:packet,REG_POINTERS=[1,2,3,4],write_u64=lambda *a:None,physical_address=lambda b:id(b),REG_CONFIG=5,REG_AP_CTRL=0,transaction_snapshot=lambda *a:dict(safe),wait_transaction=complete)
        result=dict(released_buffers=[]);blocked=[];registry=PatchScope();pynq=types.SimpleNamespace(allocate=lambda *a:None)
        ns.update(np=np,policy=policy,runtime=runtime,engine=engine,result=result,blocked=blocked,patch=registry.patch,pynq=pynq,initialized=True,allocations=buffers,SHAPES=[int(b.nbytes) for b in buffers],CANDIDATE=candidate,json=json,hashlib=hashlib,base=base,safe_to_release=safe_to_release,SealedPSReadSession=SealedPSReadSession,weakref=weakref,ps_session=None)
        section=source[source.index("        patch(pynq,'allocate',forbid('extra-DMA.pynq.allocate'"):source.index("        result['boot_unchanged']",source.index("        patch(pynq,'allocate',forbid('extra-DMA.pynq.allocate'"))]
        if os.name=='nt':
            strict=original.file_identity
            with patch.object(original,'file_identity',lambda st:strict(st)[:4]+strict(st)[5:]):exec(compile(textwrap.dedent(section),'actual-descriptor-binding-scope','exec'),ns)
        else:exec(compile(textwrap.dedent(section),'actual-descriptor-binding-scope','exec'),ns)
        assert ns['ps_session'] is None and result['session_weakref_dead'] and result['ps_session']['slot_release']['all_owner_weakrefs_dead'] and runtime._stage is stage
        assert not hasattr(runtime,'_m351_ps_owner') and result['stage_pair_bytes']==5898240 and len(result['transactions'])==2
        for f in (runtime.allocate,pynq.allocate):
            try:f(1)
            except RuntimeError:pass
            else:raise AssertionError('Allocation guard accepted')
        blocked.clear();registry.restore_all(completion_proven=True,release_proven=True)
    from m384_collect import decode
    row=json.loads((BASE/'runs/M382-sealed-ps-slot-board-01/BOARD_RESULT.json').read_text(encoding='utf-8'))
    row.update(result,status='PASS_M384_PS_CHAIN_NUMERICAL',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),gate_level='sealed-DMA-PS-single-chain-numerical',numerical_pass=True,fpga_transactions=3,ps_prefetch_enabled=True,worker_started=True,host_calls=0,logical_calls=0,extra_pynq_allocations=0,slot_prerequisite_sha256='178a914e34cf0cb9a74b19853b01ee5f7fd549059b9b7a9a42cc3827332d7a5a',descriptor_prerequisite_sha256='6d1d646117c8945847811fb70cb7e81b3a7792b3ed63ac53f7aeeb91e0973d1a',original_buffer_release_count=7,patch_registry_cleared=True,gate_return_code=0,errors=[],elapsed_s_diagnostic_not_performance=1)
    allocated=json.loads((BASE/'runs/M382-sealed-ps-slot-board-01/BOARD_RESULT.json').read_text(encoding='utf-8'))['allocated_buffers'];row['allocated_buffers']=allocated;row['released_buffers']=list(reversed(allocated));row['final_snapshot']=safe;row['same_overlay_minimal_proof']=dict(full_output_exact=True,output_bytes=4096)
    def export(r):
        raw=encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M384_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM384_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M384_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(v).decode()+'\n' for i,v in enumerate(parts))+f'M384_DONE case=B1 gate_rc={r["gate_return_code"]} export_rc=0\n'
    assert decode(export(row))[2]==row
    assert decode(export(dict(row,status='FAIL',gate_return_code=1,errors=['deliberate failure'])))[2]['gate_return_code']==1
    bad=[]
    for k,v in [('model_forward_calls',1),('memory_capacity_proven',True),('performance_pass',True),('safe_buffers_released',False),('session_weakref_dead',False),('fpga_transactions',2),('original_parser_workers',2),('extra_pynq_allocations',1),('slot_prerequisite_sha256','0'*64),('numerical_pass',False),('released_buffers',[])]:bad.append(dict(row,**{k:v}))
    for k,v in [('stages',2),('submissions',2),('open_files',1),('live_views',1),('total_weight_bytes',1)]:
        x=copy.deepcopy(row);x['ps_session']['component'][k]=v;bad.append(x)
    x=copy.deepcopy(row);x['candidate_chain']['weight_sha256'][0]='0'*64;bad.append(x)
    x=copy.deepcopy(row);x['ps_session']['slot_release']['all_owner_weakrefs_dead']=False;bad.append(x)
    negatives=0
    for r in bad:
        try:decode(export(r))
        except ValueError:negatives+=1
        else:raise AssertionError('Invalid result accepted')
    for log in (export(row)+export(row),export(row).replace('CHUNK=1/','CHUNK=0/'),export(row).replace('export_rc=0','export_rc=1')):
        try:decode(log)
        except ValueError:negatives+=1
        else:raise AssertionError('Invalid bytes accepted')
    for n in ('m384_collect.py','m384_workflow.py','m384_support.py'):ast.parse((HERE/n).read_text(encoding='utf-8'),feature_version=(3,10))
    r=dict(status='PASS_OFFLINE_PS_DESCRIPTOR_CONTROL_RECOVERY',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),actual_frozen_orchestration=True,real_fixture_PS_read_and_copy=True,explicit_fake_pack_MMIO_golden_memory=True,actual_slot_and_session_weakrefs=True,collector_fixture_only=True,collector_negative_checks=negatives,controller_failure_collects=True,board_run=False,numerical_pass=False,performance_pass=False,source_sha256={n:sha(HERE/n) for n in ('m384_control.ps1','m384_workflow.py','m384_collect.py','m384_support.py','m384_scope_support.py','m383_sealed_ps_read.py')})
    out=BASE/'runs/M384-ps-chain-support-01/RESULT.json';atomic(out,encoded(r),immutable=True);digest=sha(out)
    sync('latest_m384_ps_chain_support',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256']),f'## M384 PS完整chain控制/回收支持（2026-10-03）\n\n实际新gate编排配真实fixture读取/复制/slot及session weakref；pack/MMIO/golden/memory明确替身，不冒称板端数值。封锁两分配入口，原_stage/owner恢复，{negatives}项collector负例拒绝，控制失败仍收集。支持 SHA {digest}；下一步同COM3 sudo/完整包SHA后一次本级。')
    print('M384_SUPPORT_PASS',digest,negatives)
if __name__=='__main__':main()
