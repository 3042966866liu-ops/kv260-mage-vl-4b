"""Actual 162-window scope with real self-owned I/O; explicit fake model/MMIO."""
import ast,base64,copy,hashlib,json,os,subprocess,sys,tempfile,textwrap,weakref
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m386_prepare import PKG,OLD,once
def main():
    prep=json.loads((BASE/'runs/M386-ps-text-preparation-01/RESULT.json').read_text(encoding='utf-8'))
    layer_raw=prep['PS_layer_prerequisite_sha256']
    s=(HERE/'m385_control.ps1').read_text(encoding='utf-8').replace('M385','M386').replace('m385','m386').replace('M386-ps-layer-02','M386-ps-text-01').replace('M386-ps-layer','M386-ps-text').replace('m386_ps_layer','m386_ps_text').replace('latest_m386_ps_layer','latest_m386_ps_text').replace('ENABLE_PS_LAYER','ENABLE_PS_TEXT').replace('candidates/M384-ps-chain-01','candidates/M385-ps-layer-02')
    atomic(HERE/'m386_control.ps1',s.encode('utf-8'))
    s=(HERE/'m385_workflow.py').read_text(encoding='utf-8').replace('M385','M386').replace('m385','m386').replace('M386-ps-layer-02','M386-ps-text-01').replace('M386-ps-layer','M386-ps-text').replace('latest_m386_ps_layer','latest_m386_ps_text').replace('candidates/M384-ps-chain-01','candidates/M385-ps-layer-02').replace('31载荷','30载荷').replace('精确M384','精确M385').replace('单层五窗口','固定文本162窗口').replace('单层完整数值','固定文本完整数值')
    atomic(HERE/'m386_workflow.py',s.encode('utf-8'))
    s=(HERE/'m385_collect.py').read_text(encoding='utf-8').replace('M385','M386').replace('M386-ps-layer-02','M386-ps-text-01').replace('M386-ps-layer','M386-ps-text').replace('latest_m385_ps_layer','latest_m386_ps_text').replace('m365_stage_policy','m366_stage_policy').replace('PASS_M386_PS_LAYER_NUMERICAL','PASS_M386_PS_TEXT_NUMERICAL').replace('sealed-DMA-PS-single-layer-numerical','sealed-DMA-PS-fixed-text-numerical').replace('chain_prerequisite_sha256','PS_layer_prerequisite_sha256').replace('31121b29b1a1fbcd6f578bc2f984b0bbca4a12420fdf3fc0481fd7eb16df2277',layer_raw).replace('stages=5,submissions=5','stages=162,submissions=162').replace("len(p['independent_memory_checks'])<9","len(p['independent_memory_checks'])<166")
    s=once(s,'from m366_stage_policy import assess,SHAPES',"sys.path.insert(0,str(w.BASE/'candidates/M386-ps-text-01'))\nfrom m366_stage_policy import assess,SHAPES")
    s=once(s,"        if r['fpga_transactions']!=1+r['layer_result']['host_calls']", "        proof=r['head_observer_proof']\n        if not proof['removed_observation_calls_ast_equals_original'] or proof['inserted_observation_calls']!=2 or not proof['every_retry_physical_boundary'] or proof['exact_frozen_head_chains']!=8 or len([t for t in r['transactions'] if t['method']=='head-original-execute'])!=8:raise ValueError('Original head physical coverage differs')\n        if r['fpga_transactions']!=1+r['layer_result']['host_calls']")
    s=s.replace('只layer0/159重复文本embedding和五窗口PS预读，原单parser','原30Token/36层/完整head与162窗口PS预读，原单parser').replace('下一步仅本级数值和生命周期闭合，之后准备固定文本','下一步仅本级数值和生命周期闭合，之后独立论证159视频预算').replace('M386 独立单层容量诊断','M386 PS固定文本数值门禁')
    atomic(HERE/'m386_collect.py',s.encode('utf-8'))
    ctl=subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoProfile','-File',str(HERE/'m386_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    assert ctl.returncode==0 and 'M386_CONTROL_SELF_TEST_PASS' in ctl.stdout,ctl.stdout+ctl.stderr
    # Execute the actual package adapter and actual new scope lines; no test
    # reimplementation of plan assembly. All model/math/MMIO/memory are doubles.
    sys.path.insert(0,str(PKG))
    import ps_read_ahead as component
    from ps_read_ahead import RetainedPSResourcesError
    from test_ps_read_ahead import Buffer,SAFE
    from test_m382_ps_slot import memory
    from m366_stage_policy import FAMILIES,SHAPES,assess
    namespace={};exec(compile((PKG/'m386_text_ps_read.py').read_text(encoding='utf-8'),'actual-frozen-text-adapter','exec'),namespace)
    TextPSReadSession=namespace['TextPSReadSession']
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);layouts=[]
        for kind in ('language','head'):
            folder=root/kind;folder.mkdir()
            for port in range(4):(folder/f'weights{port}.bin').write_bytes(bytes(range(256))*32)
            layouts.append(SimpleNamespace(root=folder,manifest=dict(files=[dict(path=f'weights{i}.bin',bytes=8192) for i in range(4)])))
        chains={(layer,name):dict(offset=i*16,size=32,descriptors=[i]) for i,(layer,name) in enumerate(FAMILIES)}
        head=[dict(offset=i*16,size=32,descriptors=[200+i]) for i in range(8)]
        runtime=SimpleNamespace(weight_mode='staged-low-cma',maximum_weight_window_bytes=128,staged_buffers=[Buffer(128) for _ in range(4)],kernel=None,dma=None,language_layout=layouts[0],head_layout=layouts[1],head_contract=SimpleNamespace(chains=head),stage_bytes=0,stage_ms=0,_stage=lambda *a:'original',_language_chain=lambda layer,name:chains[(layer,name)])
        before=runtime._stage;current=memory(rss=100<<20);current['system_bytes']['MemAvailable']=1<<30;counts={'success':7}
        policy=SimpleNamespace(sealed=True,baseline_rss=100<<20,initial_counts=counts,buffer_bytes=SHAPES,stop_reason=None,snapshot=lambda:copy.deepcopy(current),counters=lambda:dict(counts))
        def capture(label,check):
            if check:assess(current,policy.baseline_rss,counts,counts,sealed=True,buffer_bytes=SHAPES)
            return copy.deepcopy(current)
        policy.capture=capture;base=SimpleNamespace(chain_window=lambda layout,c:(c['offset']//16,c['size']),transaction_snapshot=lambda *a:dict(SAFE))
        observed=[]
        class Model:
            def prefill(self,hidden):
                for layout,chain in [(runtime.language_layout,chains[x]) for x in FAMILIES]+[(runtime.head_layout,c) for c in head]:
                    runtime._stage(layout,chain)
                    expected=bytes((i%256) for i in range(chain['offset'],chain['offset']+32))
                    assert all(bytes(b.array[:32])==expected for b in runtime.staged_buffers)
                    observed.append((layout,chain))
                return 17,None,None
        source=(PKG/'m386_ps_text_gate.py').read_text(encoding='utf-8');a=source.index('        plan=[(');b=source.index("        policy.capture('after-fixed-text'",a)
        result={};ns=dict(runtime=runtime,base=base,policy=policy,resident=lambda:True,TextPSReadSession=TextPSReadSession,FAMILIES=FAMILIES,weakref=weakref,RetainedPSResourcesError=RetainedPSResourcesError,result=result,model=Model(),hidden=SimpleNamespace(copy=lambda:None),allocations=[None]*7)
        strict=component.file_identity
        if os.name=='nt':
            with patch.object(component,'file_identity',lambda stat:strict(stat)[:4]+strict(stat)[5:]):exec(compile(textwrap.dedent(source[a:b]),'actual-frozen-text-PS-scope','exec'),ns)
        else:exec(compile(textwrap.dedent(source[a:b]),'actual-frozen-text-PS-scope','exec'),ns)
        assert len(observed)==162 and sum(x[0] is runtime.head_layout for x in observed)==8
        assert runtime._stage is before and result['session_weakref_dead'] and not hasattr(runtime,'_m351_ps_owner')
        assert result['ps_session']['component']['stages']==result['ps_session']['component']['submissions']==162
        assert result['ps_session']['component']['total_weight_bytes']==20736
        assert result['ps_session']['slot_release']['all_owner_weakrefs_dead']
    from m386_collect import decode
    row=json.loads((BASE/'runs/M366-staged-text-board-02/BOARD_RESULT.json').read_text(encoding='utf-8'))
    row.update(status='PASS_M386_PS_TEXT_NUMERICAL',gate_level='sealed-DMA-PS-fixed-text-numerical',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),PS_layer_prerequisite_sha256=layer_raw,ps_prefetch_enabled=True,session_weakref_dead=True,patch_registry_cleared=True,worker_started=True,extra_pynq_allocations=0,original_parser_workers=1)
    first=next(x for x in row['stage_memory'] if x['label']=='diagnostic-admission-after-seven-real-buffers')
    checks=[dict(before_payload=False,memory=x['memory'],decision=x['admission'],cma_counts=x['cma_counts']) for x in row['stage_memory'] if x['admission']]
    row['ps_session']=dict(component=dict(status='COMPLETE_COMPONENT_ONLY',stages=162,submissions=162,ps_payload_bytes=27852800,extra_cma_allocation_calls=0,total_weight_bytes=row['layer_result']['stage_bytes'],open_files=0,live_views=0,performance_pass=False,hardware_contract_changed=False),budget_growth_bytes=256<<20,available_margin_bytes=64<<20,budget_baseline_rss=first['memory']['process_bytes']['VmRSS'],independent_memory_checks=checks,slot_release=dict(released_ports=4,bytearrays_sole_owned_before_release=True,all_owner_weakrefs_dead=True,explicit_gc_or_trim=False),production_policy_changed=False,additional_dma_allocations=0,source_component_unchanged=True)
    def export(r):
        raw=encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M386_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM386_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join(f'M386_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(v).decode()+'\n' for i,v in enumerate(parts))+f'M386_DONE case=B1 gate_rc={r["gate_return_code"]} export_rc=0\n'
    assert decode(export(row))[2]==row
    assert decode(export(dict(row,status='FAIL',gate_return_code=1,errors=['deliberate'])))[2]['gate_return_code']==1
    bad=[]
    for k,v in [('PS_layer_prerequisite_sha256','0'*64),('ps_prefetch_enabled',False),('session_weakref_dead',False),('original_parser_workers',2),('extra_pynq_allocations',1),('layer_result',{}),('performance_pass',True),('manifest_sha256','0'*64),('fpga_transactions',0),('safe_buffers_released',False)]:bad.append(dict(row,**{k:v}))
    for k,v in [('budget_growth_bytes',320<<20),('budget_baseline_rss',0),('slot_release',{}),('independent_memory_checks',[])]:
        x=copy.deepcopy(row);x['ps_session'][k]=v;bad.append(x)
    for k,v in [('stages',161),('submissions',163),('total_weight_bytes',0),('open_files',1),('live_views',1)]:
        x=copy.deepcopy(row);x['ps_session']['component'][k]=v;bad.append(x)
    for k,v in [('inserted_observation_calls',1),('every_retry_physical_boundary',False),('removed_observation_calls_ast_equals_original',False),('exact_frozen_head_chains',7)]:
        x=copy.deepcopy(row);x['head_observer_proof'][k]=v;bad.append(x)
    for x in bad:
        try:decode(export(x))
        except (ValueError,RuntimeError,KeyError,MemoryError):pass
        else:raise AssertionError('Invalid text result accepted')
    for log in [export(row)+export(row),export(row).replace('CHUNK=1/','CHUNK=0/'),export(row).replace('export_rc=0','export_rc=1')]:
        try:decode(log)
        except ValueError:pass
        else:raise AssertionError('Invalid raw accepted')
    names=('m386_control.ps1','m386_workflow.py','m386_collect.py','m386_support.py','m386_prepare.py')
    for n in names:
        if n.endswith('.py'):ast.parse((HERE/n).read_text(encoding='utf-8'),feature_version=(3,10))
    r=dict(status='PASS_OFFLINE_PS_FIXED_TEXT_PLAN_CONTROL_RECOVERY',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),actual_frozen162_window_orchestration=True,real_fixture_read_copy_and_weakrefs=True,language_windows=154,head_windows=8,explicit_fake_DMA_model_math_memory=True,Windows_test_only_ctime_adapter=os.name=='nt',strict_Linux_source_identity_unchanged=True,collector_old_text_reference_fixture_only=True,collector_negative_checks=len(bad)+3,controller_failure_collects=True,original_head_executor_observation_reused_same_sha=True,board_run=False,numerical_pass=False,performance_pass=False,source_sha256={n:sha(HERE/n) for n in names})
    p=BASE/'runs/M386-ps-text-support-01/RESULT.json';atomic(p,encoded(r),immutable=True);d=sha(p)
    sync('latest_m386_ps_text_support',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=d,manifest_sha256=r['manifest_sha256']),f'## M386 固定文本PS控制/回收闭合（2026-10-03）\n\n实际冻结154语言＋8head计划编排、真实自有fixture read/copy/slot/session弱引用；模型数学/DMA/内存明确替身，非文本数值证明。原head真实执行器观察同SHA复用，{len(bad)+3}回收负例及控制故意失败收集通过；支持SHA {d}。下一步只一次原30Token完整文本PS数值门禁，容量/生命周期问题停止扩大。')
    print('M386_SUPPORT_PASS',d,len(bad)+3)
if __name__=='__main__':main()
