"""Verify independent diagnostic policy, frozen source scope and saved-byte failure paths."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types
import symtable
import m351_workflow as w
import m365_stage_policy as p
import m365_collect as c
from m343_layer_scope import derive

def main():
    pkg=c.PKG;manifest=json.loads((pkg/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    assert {x.name for x in pkg.iterdir()}=={x['path'] for x in manifest['files']}|{'PACKAGE_MANIFEST.json'}
    for x in manifest['files']:assert (pkg/x['path']).stat().st_size==x['bytes'] and w.sha(pkg/x['path'])==x['sha256']
    trees={x.stem:ast.parse(x.read_text(encoding='utf-8'),feature_version=(3,10)) for x in pkg.glob('*.py')}
    closure=json.loads((pkg/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers'};missing=[]
    for module,t in trees.items():
        for n in ast.walk(t):
            names=[a.name.split('.')[0] for a in n.names] if isinstance(n,ast.Import) else ([n.module.split('.')[0]] if isinstance(n,ast.ImportFrom) and n.module else [])
            missing.extend((module,name) for name in names if name not in trees and name not in allowed)
    assert not missing,missing
    root=w.ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    for row in closure['files']:assert w.sha(root/row['path'])==row['sha256']
    assert derive((root/closure['modules']['m241_video_language_runtime']).read_bytes())==(pkg/'frozen_one_layer.py').read_text(encoding='utf-8')
    hardware=json.loads((pkg/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))
    assert hardware['status']=='PASS_ALL_NEW_CIRCUIT_PREREQUISITES'
    for row in hardware['prerequisites']:assert w.sha(w.ROOT/row['path'])==row['sha256']
    prior=json.loads((pkg/'M357_COMPARE_PREREQUISITE.json').read_text(encoding='utf-8'));assert prior['status']=='PASS_M357_COMPARE'
    source=(pkg/'m365_staged_layer_gate.py').read_text(encoding='utf-8')
    # Allocator is called by engine.load before the layer block; SHAPES must
    # resolve to the already imported module global, never an unbound cell.
    main_symbols=next(t for t in symtable.symtable(source,'gate','exec').get_children() if t.get_name()=='main')
    allocator_symbols=next(t for t in main_symbols.get_children() if t.get_name()=='tracked_allocate')
    assert allocator_symbols.lookup('SHAPES').is_global()
    assert 'SHAPES' not in main_symbols.get_identifiers()
    old_source=(w.BASE/'candidates/M365-staged-layer-02/m365_staged_layer_gate.py').read_text(encoding='utf-8')
    old_symbols=next(t for t in symtable.symtable(old_source,'old_gate','exec').get_children() if t.get_name()=='main')
    assert old_symbols.lookup('SHAPES').is_local()
    assert next(t for t in old_symbols.get_children() if t.get_name()=='tracked_allocate').lookup('SHAPES').is_free()
    assert "BLOCKED_BOARD_METHODS = ('lm_head',)" in source and "for name in ('prefill','decode')" in source
    assert "if index>=7: raise RuntimeError('Allocator sealed" in source
    assert "policy.seal(allocations,int(TARGET_BUILD,16))" in source and "policy.wrap_launch" in source
    assert source.index('policy.seal(allocations')<source.index('runtime.dma.recvchannel.transfer')<source.index('one_layer(model,hidden.copy())')
    assert 'unsafe = unsafe or not initialized' in source and 'OwnedBufferRelease(original_free,release_proven' in source
    assert 'while True: time.sleep(30)' in source and "result['memory_capacity_proven']=False" in source
    assert 'vision.tower.forward' in source and "engine.stream = forbid" in source
    checked=0
    counts={'reserved:alloc_pages_success':131469,'reserved:alloc_pages_fail':0}
    m={'system_bytes':{'CmaFree':0,'MemAvailable':320<<20},'process_bytes':{'VmRSS':400<<20,'VmHWM':400<<20}}
    decision=p.assess(m,400<<20,counts,counts,sealed=True,buffer_bytes=p.SHAPES);assert decision['production_64mib_would_admit'] is False;checked+=1
    for mutate in ('low_available','rss_growth','counts_change','bad_geometry','unsealed','invalid_stat'):
        mm=json.loads(json.dumps(m));cc=dict(counts);bb=list(p.SHAPES);sealed=True
        if mutate=='low_available':mm['system_bytes']['MemAvailable']-=1
        if mutate=='rss_growth':mm['process_bytes']['VmRSS']+=(256<<20)+1
        if mutate=='counts_change':cc['reserved:alloc_pages_success']+=1
        if mutate=='bad_geometry':bb[-1]+=1
        if mutate=='unsealed':sealed=False
        if mutate=='invalid_stat':mm['system_bytes']['CmaFree']=True
        try:p.assess(mm,400<<20,cc,counts,sealed=sealed,buffer_bytes=bb)
        except (MemoryError,RuntimeError):checked+=1
        else:raise AssertionError('Invalid policy input accepted:'+mutate)
    snapshot=dict(ap_ctrl=4,ap_return=0,mm2s_dmasr=0,s2mm_dmasr=0,mm2s_error=False,s2mm_error=False,kernel_read_error='',return_read_error='',dma_read_error='')
    rt=types.SimpleNamespace(kernel=object(),dma=object());base=types.SimpleNamespace(transaction_snapshot=lambda *a:dict(snapshot));result={}
    policy=p.StagePolicy(result,lambda:rt,base,snapshot=lambda:m,counters=lambda:counts)
    policy.seal([types.SimpleNamespace(nbytes=n) for n in p.SHAPES],0x4d333537)
    assert policy.safe();checked+=1
    policy.ever=True;assert not policy.safe();checked+=1
    snapshot.update(ap_return=0x4d333537,mm2s_dmasr=4098,s2mm_dmasr=4098);policy.completed=True;assert policy.safe();checked+=1
    policy.active=True;assert not policy.safe();policy.active=False;checked+=1
    chain=dict(layer=0,family='q',chain_index=0,input_bytes=1,output_bytes=1)
    payload=object();calls=[]
    assert policy.wrap_launch(lambda ch:calls.append(ch) or payload,'fake')(chain) is payload and calls==[chain] and policy.safe();checked+=1
    fault=RuntimeError('expected native failure')
    def fail(ch):raise fault
    try:policy.wrap_launch(fail,'fake')(chain)
    except RuntimeError as e:assert e is fault and policy.active and not policy.safe();checked+=1
    else:raise AssertionError('Active fault swallowed')
    policy.active=False
    for ch in (dict(chain,layer=1),dict(chain,family='lm_head')):
        try:policy.wrap_launch(lambda ch:None,'fake')(ch)
        except RuntimeError:checked+=1
        else:raise AssertionError('Layer scope escaped')
    policy.stop_reason='monitor stop'
    try:policy.capture('safe boundary',True)
    except RuntimeError:checked+=1
    else:raise AssertionError('Monitor stop ignored')
    policy.stop_sampling();assert result['sampled_memory']['observer_stopped'];checked+=1
    r=dict(status='FAIL',case='B1',build_id='0x4D333537',gate_level='independent-single-layer-capacity-diagnostic',manifest_sha256=w.sha(pkg/'PACKAGE_MANIFEST.json'),gate_return_code=1,errors=['expected'],memory_capacity_proven=False,performance_pass=False,formal_promotion_allowed=False)
    def log(rr):
        raw=w.encoded(rr);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
        return 'M365_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM365_SAVED_GATE_RC='+str(rr['gate_return_code'])+'\n'+''.join(f'M365_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(b).decode()+'\n' for i,b in enumerate(parts))+f'M365_DONE case=B1 gate_rc={rr["gate_return_code"]} export_rc=0\n'
    good=log(r);assert c.decode(good)[2]==r
    bads=[good+good,good.replace('CHUNK=0/','CHUNK=1/'),good.replace('export_rc=0','export_rc=1'),good.replace('SAVED_GATE_RC=1','SAVED_GATE_RC=0'),log(dict(r,memory_capacity_proven=True)),log(dict(r,case='A1')),log(dict(r,manifest_sha256='0'*64)),log(dict(r,errors=[]))]
    for bad in bads:
        try:c.decode(bad)
        except (ValueError,KeyError):pass
        else:raise AssertionError('Broken evidence accepted')
    # Exercise the actual controller's deliberate-failure collection branch.
    pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    control=subprocess.run([pwsh,'-NoProfile','-File',str(w.HERE/'m365_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    assert control.returncode==0 and 'M365_CONTROL_SELFTEST_PASS' in control.stdout,control.stdout+control.stderr
    rule='''# M365 独立分阶段容量诊断准入规则

生产入口及原64 MiB CMA门槛保持。独立入口默认关闭，首次只候选Build0x4D333537的一层，完整原runtime对象与35项完整SHA保留。输入为已通过M343的159行重复文本embedding，不称为实际159-token视频。

## 准入

- 同终端授权/root、固定环境、稳定与候选逐文件SHA、原CSim/header/最大FIFO/背压/timeout/整机时序证据闭合。
- 七块真实缓冲按原几何逐块分配：四权重6963200B、一输入389152B、双输出2621440B。每次只在CmaFree至少当前请求4096B取整时尝试分配；失败记录当前请求及返回，不能伪称迁移一定失败。
- 所有七块真实分配成功后封锁后续PYNQ.allocate及runtime捕获的allocator。原单层五family、T32、重试、解析复用它们，因此诊断的后续显式CMA请求预算为0。记录原64MiB门槛会否放行，不自动把低CmaFree当实际分配失败。
- 保留完整runtime时普通MemAvailable需至少256MiB监控RSS增长预算+64MiB余量。这是保守实验预算，未认证Torch/原生库总峰值；本次不执行视觉forward或LM head。
- 首次同Overlay合法最小事务完成、完整4096B输出/Build/两DMA及AP_IDLE核对后才进入layer0。初始DMASR0只为从未提交生命周期。

## 停止与回收

- layer固定159×2560、严格q/kv/attention_out/gate_up/mlp_down次序，禁止layer>0、LMhead、视觉与整模型入口。
- 每family前后、每真实提交及完成时检查剩余普通内存预算。20ms观察RSS/CMA/MemAvailable及已有CMA API计数；RSS增长>256MiB、预算不足、计数意外变化/统计不可读、soft120s期限即锁存停止请求。全局CMA计数变化不能归因本进程，所以保守停止并记录unknown。
- 观察器只能请求下一安全边界停止，不能中断活动DMA。单次事务仍按原10s等待；异常、活动/未知DMA或观察器未结束保留缓冲、进程与锁，禁止timeout kill/reset后回收。
- 原pack/parse执行器的with上下文先退出并等待worker，然后按幂等OwnedBufferRelease严格逆序各释放一次。数值不一致时仍只在已证明AP_IDLE、两DMA无错/idle、Build匹配后回收；否则保留。
- 原M241逐句layer loop与数学不改，核对已通过稳定参考的全部family/hidden/K/V字节SHA和重试身份。关闭后仅重载稳定Overlay、不提交恢复事务，DMASR0不称 completed-idle。

## 可声明范围

PASS仅证明这一独立完整对象保留+单层输入路径在观察到的内存条件下数值/退出通过；不能解锁生产64MiB政策、完整文本/视频容量或性能。20ms采样可能漏短峰，VmHWM含整个加载进程，不能称精确单层峰值。固定文本与真实159视频必须分别论证预算/峰值/额外申请及数值，再冻结独立包并同步前级后执行。
'''
    out=w.BASE/'runs/M365-staged-layer-support-02';w.atomic(out/'RULES.md',rule.encode('utf-8'),immutable=True)
    rr=dict(status='PASS_OFFLINE_INDEPENDENT_STAGE_RULES_AND_SUPPORT',manifest_sha256=w.sha(pkg/'PACKAGE_MANIFEST.json'),policy_checks=checked,collector_negative_checks=len(bads),control_failure_collected=True,recursive_import_missing=missing,python310_syntax=True,original_layer_source_loop_unchanged=True,hardware_prerequisites_same_sha=True,seven_requested_buffers=p.SHAPES,additional_explicit_cma_after_seal_bytes=0,production_cma_reserve_bytes=64<<20,diagnostic_ps_growth_limit_bytes=p.PS_GROWTH_LIMIT,diagnostic_ps_available_margin_bytes=p.PS_AVAILABLE_MARGIN,native_peak_certified=False,production_changed=False,board_executed=False,numerical_pass=False,performance_pass=False,rules_sha256=w.sha(out/'RULES.md'),allocator_shapes_global_scope_verified=True,rejected_draft='01 unsafe flag/count fixed in02; 02 late local SHAPES import shadows global and would reject constructor.02 uploaded only, never run.03 removes shadow and preserves02 bytes.',next_step='One same COM3 authorized staged-layer diagnostic only; collect/sync and adjudicate before any full-model expansion')
    w.atomic(out/'RESULT.json',w.encoded(rr),immutable=True);digest=w.sha(out/'RESULT.json')
    w.sync('latest_m365_stage_support',dict(status=rr['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=digest,manifest_sha256=rr['manifest_sha256'],board_executed=False),f'## M365 独立单层诊断03作用域修复\n\n02包只传输未执行；复核发现main中延后局部import令构造回调SHAPES未绑定，03移除遮蔽；符号表验证旧局部/新全局，其余{checked}政策、8回收负例、故意失败收集、同SHA硬件闭包与原层循环通过。原02字节保留，0Overlay/forward/FPGA；生产64MiB和独立PS预算不改。证据SHA `{digest}`。下一步只传新03包并首次单层，不运行02。')
    print(json.dumps(rr))

if __name__=='__main__':main()
