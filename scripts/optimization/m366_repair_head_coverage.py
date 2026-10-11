"""Prepare a new immutable fixed-text attempt after saved accounting failure."""
import ast
import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import time
import types
import numpy as np
import m351_workflow as w
from m366_head_observer import bind

OLD=w.BASE/'candidates/M366-staged-text-02'
PKG=w.BASE/'candidates/M366-staged-text-03'
OUT=w.BASE/'runs/M366-staged-text-support-03'


def checks(closure):
    release=w.ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    path=release/closure['modules']['m230_prefill_runtime']
    tree=ast.parse(path.read_text(encoding='utf-8'))
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='M230PrefillRuntime')
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_execute')
    policy_spec=importlib.util.spec_from_file_location('m366_test_policy',OLD/'m366_stage_policy.py')
    p=importlib.util.module_from_spec(policy_spec);policy_spec.loader.exec_module(p)
    results=[]

    def case(observed=True,mode='ok',index=0):
        trace=[];counter=[0]
        snapshot=dict(ap_ctrl=4,ap_return=0x4d333537,mm2s_dmasr=4098,s2mm_dmasr=4098,mm2s_idle=True,s2mm_idle=True,mm2s_error=False,s2mm_error=False,kernel_read_error='',return_read_error='',dma_read_error='')
        mem={'system_bytes':{'CmaFree':17<<20,'MemAvailable':320<<20},'process_bytes':{'VmRSS':400<<20,'VmHWM':400<<20}}
        counts={'reserved:alloc_pages_success':0,'reserved:alloc_pages_fail':0}
        def wait(*args):
            trace.append('wait')
            if mode=='timeout':raise TimeoutError('fixture timeout; no completion')
            if mode=='bad-completion':return dict(snapshot,ap_return=0x1234)
            return dict(snapshot)
        def parse(*a,**k):
            counter[0]+=1;trace.append('parse')
            return {'lm_head':np.full((1,1),np.nan if counter[0]==1 else 2,np.float32)}
        base=types.SimpleNamespace(MIN_ACTIVATION_SCALE_SHIFT=5,BUILD_ID=0x4d333537,REG_AP_CTRL=0,pack_chain_input=lambda *a,**k:b'1234',wait_transaction=wait,parse_chain_output=parse,transaction_snapshot=lambda *a:dict(snapshot))
        namespace=dict(__name__='m366_frozen_executor_fixture',np=np,time=time,base=base)
        exec(compile(ast.Module(body=[copy.deepcopy(method)],type_ignores=[]),str(path),'exec'),namespace)
        class Buffer(np.ndarray):
            def __new__(cls):return np.zeros(8,np.uint8).view(cls)
            def sync_to_device(self):trace.append('input_sync')
            def sync_from_device(self):trace.append('output_sync')
        def transfer(label):
            def call(*a,**k):
                trace.append(label)
                if mode=='send-error' and label=='send':raise RuntimeError('fixture send failure')
            return call
        rt=types.SimpleNamespace(input_buffer=Buffer(),output_buffer=Buffer(),kernel=types.SimpleNamespace(write=lambda *a:trace.append('start')),dma=types.SimpleNamespace(recvchannel=types.SimpleNamespace(transfer=transfer('recv')),sendchannel=types.SimpleNamespace(transfer=transfer('send'))),host_calls=0,expected_macros=0,logical_calls=0,logical_expected_macros=0,scale_retry_count=0,scale_shift_counts={'5':0,'6':0},scale_attempts=[],_initial_scale_shift=lambda v:6,_record_phase=lambda *a:None,_program_static_registers=lambda *a:None,_written_outputs_finite=lambda ch,out:bool(np.isfinite(out['lm_head']).all()))
        original=types.MethodType(namespace['_execute'],rt)
        chains=[dict(chain_index=i,input_bytes=4,output_bytes=4,expected_macros=1) for i in range(8)]
        result={};policy=p.StagePolicy(result,lambda:rt,base,snapshot=lambda:mem,counters=lambda:counts)
        policy.seal([types.SimpleNamespace(nbytes=n) for n in p.SHAPES],0x4d333537)
        policy.ever=policy.completed=True
        function,proof=bind(original,policy,chains)
        if mode=='pre-stop':mem['system_bytes']['MemAvailable']=1
        chain=copy.deepcopy(chains[index])
        if mode=='identity':chain['expected_macros']=2
        caught=None;answer=None
        try:answer=(function if observed else original)(chain,np.ones((1,1),np.float32),[],0)
        except (RuntimeError,TimeoutError,MemoryError) as e:caught=type(e).__name__
        return dict(trace=trace,host_calls=rt.host_calls,retries=rt.scale_retry_count,attempts=rt.scale_attempts,output=None if answer is None else answer['lm_head'].tolist(),transactions=result.get('transactions',[]),active=policy.active,completed=policy.completed,caught=caught,proof=proof)
    original=case(False)
    for i in range(8):
        observed=case(index=i)
        if i==0:
            for key in ('trace','host_calls','retries','attempts','output'):assert observed[key]==original[key],key
        assert observed['host_calls']==len(observed['transactions'])==2 and observed['retries']==1
        assert all(t['chain_index']==i and t['family']=='lm_head' for t in observed['transactions'])
        assert not observed['active'] and observed['completed'] and observed['caught'] is None
        results.append('real-frozen-M230-head-path-chain-'+str(i)+'-two-attempts-counted')
    for mode in ('timeout','send-error','bad-completion'):
        r=case(mode=mode);assert r['caught'] and r['active'] and not r['completed']
        results.append(mode+'-retains-active-state')
    for mode in ('pre-stop','identity'):
        r=case(mode=mode);assert r['caught'] and not r['active'] and not {'recv','send','start','wait'}.intersection(r['trace'])
        results.append(mode+'-no-DMA-submitted')
    assert original['host_calls']==2 and original['transactions']==[]
    results.append('old-observer-omission-reproduced-on-real-frozen-method')
    return results,w.sha(path)


def main():
    if PKG.exists() or OUT.exists():raise RuntimeError('Immutable repair exists')
    raw=w.BASE/'runs/M366-staged-text-board-01/BOARD_RESULT.json'
    r=json.loads(raw.read_text(encoding='utf-8'))
    assert w.sha(raw)=='70c31ca1b1f3e0f80e20e29b94f4d5a201fc43c9597fcac6768cf0ac95d025d1'
    assert r['errors']==['RuntimeError: Physical launch accounting differs'] and all(r['exact_comparison'].values())
    assert len(r['transactions'])==157 and r['layer_result']['host_calls']==165 and len(r['released_buffers'])==7
    assert r['safe_buffers_released'] and not r['unsafe_buffers_retained'] and r['stable_overlay_reloaded']
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert w.sha(raw) in (w.ROOT/name).read_text(encoding='utf-8')
    closure=json.loads((OLD/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    tests,source_sha=checks(closure)
    PKG.mkdir()
    for path in OLD.iterdir():
        if path.name not in ('PACKAGE_MANIFEST.json','SHA256SUMS'):shutil.copyfile(path,PKG/path.name)
    shutil.copyfile(w.HERE/'m366_head_observer.py',PKG/'m366_head_observer.py')
    gate=(PKG/'m366_staged_text_gate.py').read_text(encoding='utf-8').replace('m366_staged_text_01','m366_staged_text_02')
    needle="        expected=json.loads((HERE/'LAYER_EXPECTED.json').read_text(encoding='utf-8'))"
    assert gate.count(needle)==1
    gate=gate.replace(needle,"        from m366_head_observer import bind as bind_head\n        observed_head,proof=bind_head(runtime._execute,policy,runtime.head_contract.chains)\n        if proof['original_module']!='m230_prefill_runtime' or proof['original_function']!='M230PrefillRuntime._execute':raise RuntimeError('Actual head executor identity differs')\n        result['head_observer_proof']=proof\n        patch(runtime,'_execute',observed_head)\n"+needle)
    w.atomic(PKG/'m366_staged_text_gate.py',gate.encode('utf-8'))
    for name in ('m366_export_result.py','run_m366_staged_text.sh'):
        w.atomic(PKG/name,(PKG/name).read_text(encoding='utf-8').replace('m366_staged_text_01','m366_staged_text_02').encode('utf-8'))
    assembler=(PKG/'m366_assemble.py').read_text(encoding='utf-8').replace('/home/ubuntu/m363_common_load_observer_01','/home/ubuntu/m366_staged_text_candidate_02').replace('006dff41790e8adda44c85a3b93383b93e7089243a6079f88de397f2a48e6b74',w.sha(OLD/'PACKAGE_MANIFEST.json'))
    w.atomic(PKG/'m366_assemble.py',assembler.encode('utf-8'))
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(PKG.iterdir())]
    w.atomic(PKG/'SHA256SUMS',''.join(x['sha256']+'  '+x['path']+'\n' for x in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=w.sha(PKG/'SHA256SUMS')))
    w.atomic(PKG/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='m366-independent-fixed-text-capacity-v1',files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))))
    trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')}
    allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers'}
    missing=[]
    for module,tree in trees.items():
        for n in ast.walk(tree):
            names=[a.name.split('.')[0] for a in n.names] if isinstance(n,ast.Import) else ([n.module.split('.')[0]] if isinstance(n,ast.ImportFrom) and n.module else [])
            missing.extend((module,name) for name in names if name not in trees and name not in allowed)
    assert not missing,missing
    release=w.ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    for row in closure['files']:assert w.sha(release/row['path'])==row['sha256']
    hw=json.loads((PKG/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))
    assert hw['status']=='PASS_ALL_NEW_CIRCUIT_PREREQUISITES'
    for row in hw['prerequisites']:assert w.sha(w.ROOT/row['path'])==row['sha256']
    control=(w.HERE/'m366_control.ps1').read_text(encoding='utf-8').replace('M366-staged-text-02','M366-staged-text-03').replace('M366-staged-text-support-02','M366-staged-text-support-03').replace('M366-staged-text-transfer-01','M366-staged-text-transfer-02').replace('m366_staged_text_candidate_02','m366_staged_text_candidate_03').replace('tmp/m366/','tmp/m36603/').replace('m366_transfer_receipt.py','m36603_transfer_receipt.py').replace('m366_collect.py','m36603_collect.py').replace('candidates/M363-common-load-observer-01','candidates/M366-staged-text-02')
    w.atomic(w.HERE/'m36603_control.ps1',control.encode('utf-8'))
    collect=(w.HERE/'m366_collect.py').read_text(encoding='utf-8').replace('M366-staged-text-02','M366-staged-text-03').replace('M366-staged-text-board-01','M366-staged-text-board-02').replace('独立单层容量诊断','独立固定文本容量诊断').replace('先单层解读','先固定文本解读')
    needle="        if r['fpga_transactions']!=1+r['layer_result']['host_calls']"
    assert collect.count(needle)==1
    collect=collect.replace(needle,"        if not r['head_observer_proof']['removed_observation_calls_ast_equals_original'] or len([t for t in r['transactions'] if t['method']=='head-original-execute'])!=8:raise ValueError('Head physical coverage differs')\n"+needle)
    w.atomic(w.HERE/'m36603_collect.py',collect.encode('utf-8'))
    receipt=(w.HERE/'m366_transfer_receipt.py').read_text(encoding='utf-8').replace('from m366_collect','from m36603_collect').replace('tmp/m366/','tmp/m36603/').replace('M366-staged-text-transfer-01','M366-staged-text-transfer-02').replace('已冻结M363','已冻结M366-02')
    w.atomic(w.HERE/'m36603_transfer_receipt.py',receipt.encode('utf-8'))
    interpretation=(w.HERE/'m366_interpret.py').read_text(encoding='utf-8').replace('M366-staged-text-board-01','M366-staged-text-board-02').replace('M366-staged-text-closure-01','M366-staged-text-closure-02')
    w.atomic(w.HERE/'m36603_interpret.py',interpretation.encode('utf-8'))
    ps='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    c=subprocess.run([ps,'-NoProfile','-File',str(w.HERE/'m36603_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    assert c.returncode==0 and 'M366_CONTROL_SELFTEST_PASS' in c.stdout,c.stdout+c.stderr
    spec=importlib.util.spec_from_file_location('m36603_collector_test',w.HERE/'m36603_collect.py');collector=importlib.util.module_from_spec(spec);spec.loader.exec_module(collector)
    try:collector.decode((w.ROOT/'tmp/m366/run.log').read_text(encoding='utf-8-sig'))
    except ValueError:pass
    else:raise AssertionError('Old accounting failure accepted as new package')
    recovery={}
    for name in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        content=(w.ROOT/name).read_text(encoding='utf-8-sig');recovery[name]=dict(sha256=w.sha(w.ROOT/name),lines=len(content.splitlines()),bytes=(w.ROOT/name).stat().st_size)
    result=dict(status='PASS_OFFLINE_FIXED_TEXT_SCOPE_BUDGET_AND_SUPPORT',manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),prior_failure_sha256=w.sha(raw),unchanged_numeric_comparison=all(r['exact_comparison'].values()),old_observed_physical=157,old_runtime_physical=165,missing_head_physical=8,head_actual_source_sha256=source_sha,head_observer_checks=tests,algorithm_AST_unchanged_after_removing_two_observation_calls=True,full_source_closure_sha_verified=True,source_closure_missing=missing,same_sha_hardware_evidence=True,python310_syntax=True,control_failure_collected=True,old_result_rejected=True,recovery_read=recovery,production_policy_changed=False,board_executed=False,performance_pass=False)
    w.atomic(OUT/'RESULT.json',w.encoded(result),immutable=True);digest=w.sha(OUT/'RESULT.json')
    note=f'## M366 固定文本03补齐head物理观察\n\n首次原rc1，完整数值SHA一致但157观察/165真实调用，8个head走冻结M230._execute而绕过语言_launch观察器；原结果不晋级。03只为原方法每次retry的recv前/计数后加入两观察调用，移除调用AST完全等于冻结原方法，8真实源码chain夹具/重试及活动故障保留/提交前停止共14项通过；旧raw/包保持，生产门槛/数学/电路不改。原SHA `{w.sha(raw)}`，支持SHA `{digest}`。下一步仅新03包一次同级固定文本，不进入视频。'
    w.sync('latest_m366_stage_support',dict(status=result['status'],sha256=digest,result=(OUT/'RESULT.json').relative_to(w.ROOT).as_posix(),manifest_sha256=result['manifest_sha256']),note)
    review=w.ROOT/'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md'
    addition='\n\n## M366 固定文本物理观察遗漏（2026-10-02）\n\n首次完整文本已运行，但门禁仅包住语言_launch_prepacked/_launch_once。实际LM head继承冻结M230._execute，在原循环中直接提交DMA，8次物理调用没有观察记录；数值全SHA相同不能覆盖准入/生命周期观察遗漏，必须FAIL，不准晋级。旧raw SHA `'+w.sha(raw)+'`，安全释放/稳定恢复完成。03修复只对冻结实际方法每次重试边界加入观察，移除新增两调用后AST严格相同；必须用实际冻结执行器的重试、超时/提交故障及提交前停止验证覆盖，不得以人为带family的scope fake通过替代真实dispatch覆盖。原数学/源码/硬件不改，保留首次证据，重新验证仅固定文本级。\n'
    w.atomic(review,review.read_bytes()+addition.encode('utf-8'))
    print(json.dumps(result))


if __name__=='__main__':main()
