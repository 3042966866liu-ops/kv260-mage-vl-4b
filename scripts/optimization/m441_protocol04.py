"""Freeze a narrower independent protocol; no tool launch in Prepare."""
import argparse
import ast
import difflib
import json
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

RUN=BASE/'runs/M441-independent-protocol-04'

def evidence(name,expected=None):
    p=BASE/'runs'/name/'RESULT.json';r=json.loads(p.read_bytes());digest=sha(p)
    if expected:assert r['status']==expected
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    assert any(isinstance(v,dict) and v.get('sha256')==digest for v in b.values())
    assert all(digest in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    return p,r

def prepare():
    ev=RUN/'PREPARATION.json';assert not ev.exists()
    refs=[]
    for name,status in [('M441-revision03-interruption-closure-01','INTERRUPTED_HOST_REBOOT_NO_SIMULATION_VERDICT'),
        ('M441-full-numeric-csim-01','PASS_M441_FULL_REAL_WEIGHT_CHAIN_CSIM'),
        ('M441-actual-schedule-queue-guard-01','PASS_M441_ACTUAL_MAC_AND_BOUNDED_QUEUE_STATIC_GUARD'),
        ('M441-long-A-gate_up-zero-02','PASS_M441_COMPLETE_CHAIN_RTL_NUMERIC_AND_PROTOCOL'),
        ('M441-long-B-gate_up-zero-02','PASS_M441_COMPLETE_CHAIN_RTL_NUMERIC_AND_PROTOCOL'),
        ('M441-max-protocol-preparation-01','PREPARED_M441_MAXIMUM_PROTOCOL_NO_EXECUTION')]:
        p,r=evidence(name,status);refs.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),status=r['status']))
    prep=BASE/'runs/M441-record-pipeline-preparation-02/RESULT.json'
    old=BASE/'runs/M439-record-load-preparation-02/RESULT.json'
    pp=json.loads(prep.read_bytes());op=json.loads(old.read_bytes())
    src=ROOT/'tmp/m441_record_pipeline_02/hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp'
    oldsrc=ROOT/'tmp/m439_record_load_02/hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp'
    assert sha(src)==pp['source_sha256'] and sha(oldsrc)==pp['prior_source_sha256']
    assert sha(src)!=sha(oldsrc) and 'DATAFLOW' in src.read_text(encoding='utf-8-sig')
    def rtl(directory):return {p.name:sha(p) for p in directory.glob('*.v')}
    newrtl=rtl(ROOT/'tmp/m441_hls_project_02/hls/syn/verilog')
    oldrtl=rtl(ROOT/'tmp/m439_hls_project_02/hls/syn/verilog')
    identical=sorted(k for k in newrtl.keys()&oldrtl.keys() if newrtl[k]==oldrtl[k])
    changed=sorted(k for k in newrtl.keys()&oldrtl.keys() if newrtl[k]!=oldrtl[k])
    assert changed
    shared={x['path'].split('/hls/',1)[1]:x['sha256'] for x in pp['files'] if '/hls/' in x['path']}
    previous={x['path'].split('/hls/',1)[1]:x['sha256'] for x in op['files'] if '/hls/' in x['path']}
    inherited=[k for k in shared.keys()&previous.keys() if shared[k]==previous[k]]
    for x in pp['files']:
        if '/hls/' in x['path']:assert sha(ROOT/x['path'])==x['sha256']
    audit=dict(source_identical=False,RTL_identical=False,source_sha256=sha(src),M439_source_sha256=sha(oldsrc),
        build_M439='0x4D343339',build_M441='0x4D343431',interface_header_unchanged='mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.hpp' in inherited,
        identical_recursive_inputs=sorted(inherited),identical_RTL_modules=identical,changed_RTL_modules=changed,
        new_RTL_modules=sorted(newrtl.keys()-oldrtl.keys()),removed_RTL_modules=sorted(oldrtl.keys()-newrtl.keys()),
        identical_module_reuse_scope='Submodule identity only, not complete-core routed timing or global protocol proof',
        M439_implementation_reuse_allowed=False,M439_Q_candidate_PASS_reuse_allowed=False,
        M441_Q_full_CSim_reuse_allowed=True,M441_Q_RTL_or_board_result_exists=False,
        source_change='Per-shard DATAFLOW producer/consumer and actual FIFO34; arithmetic/outer ABI reference reused',
        new_RTL_SHA=newrtl,M439_RTL_SHA=oldrtl)
    atomic(RUN/'REUSE_AUDIT.json',encoded(audit),immutable=True)
    diff=''.join(difflib.unified_diff(oldsrc.read_text(encoding='utf-8-sig').splitlines(True),src.read_text(encoding='utf-8-sig').splitlines(True),fromfile=str(oldsrc),tofile=str(src)))
    atomic(RUN/'SOURCE_DIFF.patch',diff.encode('utf-8'),immutable=True)
    adapters=[]
    replacements={
        'm441_prepare_long_rtl03.py':[('_03','_04'),('preparation-03','preparation-04'),("observer_revision='03'","observer_revision='04'"),('80000000','12000000'),("family in ('gate_up','mlp_down','q')","family == 'mlp_down'"),('s=instrument(s)','s=instrument(s).replace(\'cyc>80000000\',\'cyc>12000000\')'),('m441_prepare_long_rtl03.py','m441_prepare_long_rtl04.py')],
        'm441_run_long_rtl03.ps1':[('preparation-03','preparation-04'),('_03/verilog','_04/verilog'),("RTL_preparation03","RTL_preparation04"),("observer_revision -ne '03'","observer_revision -ne '04'")],
        'm441_collect_long_rtl03.py':[("revision == '03'","revision == '04'"),("revision=='03'","revision=='04'")],
    }
    # Only path/revision/budget admission changes; retain original collectors,
    # actual-hierarchy bindings, strict output and progress predicates.
    for original,changes in replacements.items():
        source=HERE/original; text=source.read_text(encoding='utf-8-sig')
        # Generator import and observer SHA refer to the frozen03 helper.
        if original.startswith('m441_prepare'):
            changes=[(a,b) for a,b in changes if a!='_03']+[('m441_long_{variant}_{family}_03','m441_long_{variant}_{family}_04')]
        for before,after in changes:
            assert before in text,(original,before)
            text=text.replace(before,after)
        name=original.replace('03.','04.');target=HERE/name
        if target.suffix=='.py':ast.parse(text,feature_version=(3,10))
        atomic(target,text.encode('utf-8'),immutable=True)
        adapters.append(dict(parent=source.relative_to(ROOT).as_posix(),parent_sha256=sha(source),
            path=target.relative_to(ROOT).as_posix(),sha256=sha(target),replacements=changes))
    protocol='''# M441 独立04验证协议（2026-10-08，启动前冻结）

旧Random02 FAIL和Random03主机重启中断保留。本协议不声称完成旧六组完整Random；DUT仍为M441 0x4D343431，不加入下一条预取或修改MAC。旧gate_up Zero完整A/B同SHA复用。

| 目的 | 固定步骤 | 接受证据与停止条件 |
| --- | --- | --- |
| 完整W4长链数值及正常协议 | 原真实mlp_down输入/权重，A=M357、B=M441各一次Zero，独立04目录 | 全部40960输出字逐位、Build/keep/strb/TLAST/ap_done/原rc、全部权重地址及MAC次数、B四FIFO34满/背压/排空；固定12M周期、每工具8h；任一失败停同级，无补样本 |
| 有界随机与针对性边界 | 保留原最大夹具10descriptor、512行/shard、327680输出字、FIFO8192与34。独立04副本，随机AR/R/AXIS等待限定0..8、seed441；w0 ARREADY保持10000周期，输出READY保持100000周期，再针对最后TLAST保持128有效周期 | 实际4KiB burst拆分、描述符切换、四分片完成汇合、payload/AR在停顿中稳定、FIFO满/不溢出/排空、完整输出/最终TLAST/done/rc。协议零scale夹具不是模型质量；固定4M周期/4h，不缩小FIFO触发规模。缺失实际覆盖即FAIL或UNPROVEN，不改门槛或加测 |
| 失败返回验证 | 同一个已验证编译snapshot的隔离副本，启动后200周期触发timeout | 必须保存原rc与失败快照；即使xsim rc0也拒绝，不能计数值PASS。工具不自动kill，活动进程保留 |
| 资源/时序 | M441自身同器件/4.8ns/XDC核OOC与后续整壳 | M439 RTL不同不能复用整体实现结果；复用相同约束和报告解析器。资源、setup/hold/pulse、route失败停止；不放宽时钟 |
| 实板W4长链真实性能 | 上述正确性与资源门禁闭合、整壳通过后按Build-ID→单descriptor→同一W4链 | 同输入及权重，暂存/解析在计时外，单链完整事务A/B交错固定次数、记录全部样本。软件仿真墙钟或压力模型周期不是板端性能；通过后才扩大模型范围 |

Q已有M441完整真实权重CSim复用，不无条件重跑。M439的Q候选实板结果不能升级为M441通过；本轮板端目标限定W4，不声明任意W2、模型或视频通过。相同M357基线也必须核对原输入和测量边界后才能复用。

监督器每30秒原子保存PID+创建FILETIME、主机启动估计、最后全局及四端口进度/失败尾段；每项原日志、原rc先保存并同步三记录再启动后级。重启/身份不符/预算到期为中断，保留所有者与日志，不自动从头启动。没有checkpoint，不开发恢复系统。已启动工具独立跑到其固定终点。

执行分段：先完成状态对账和本协议，启动唯一mlp_down Zero A/B阶段；边界夹具必须实现并通过收集负例检查后才能启动，不凭本计划解锁OOC/整壳/上板。未实现步骤明确保持锁定。
'''
    atomic(RUN/'PROTOCOL.md',protocol.encode('utf-8'),immutable=True)
    files=[dict(path=(HERE/n).relative_to(ROOT).as_posix(),sha256=sha(HERE/n)) for n in ['m441_supervisor04.py','m441_protocol04.py','m441_continue04.py',
        'm441_observer03.py','m441_progress03.py','m351_workflow.py','m441_continue_offline.py','m438_prepare.py','m439_prepare_rtl.py','m357_uvm_log_evidence.py','m356_collect_rtl.py']]
    for a in adapters:files.append(dict(path=a['path'],sha256=a['sha256']))
    r=dict(status='PREPARED_M441_SEPARATE_NUMERIC_BOUNDARY_BOARD_PROTOCOL04',build_id='0x4D343431',board=False,
        prior_refs=refs,reuse_audit_sha256=sha(RUN/'REUSE_AUDIT.json'),protocol_sha256=sha(RUN/'PROTOCOL.md'),
        files=files,adapters=adapters,default_disabled=True,child_wall_budget_s=28800,
        first_stage='mlp_down Zero A/B, each once, parallel simulation after sequential preparation/compile/collection',
        numeric_cycle_budget=12000000,pressure_stage_implemented=False,no_automatic_pressure_OOC_shell_board=True,
        old_6_groups_complete_random=False,old_FAIL_and_interruption_preserved=True,checkpoint_development=False)
    atomic(ev,encoded(r),immutable=True)
    sync('latest_m441_independent_protocol04',dict(status=r['status'],sha256=sha(ev),result=ev.relative_to(ROOT).as_posix(),board=False),
        '## M441 独立04分离验证协议已冻结（2026-10-08）\n\nSHA '+sha(ev)+'；M439/M441实际源与RTL不同，11份递归输入同SHA可复用，整体路由/Q实板不能移植；复用M441 gate_up Zero及三链完整CSim。新协议先mlp_down完整Zero A/B（12M/8h各一次），再最大10descriptor/FIFO8192与34有界随机/AR及尾输出停顿/timeout，最后自身时序和实板W4。旧02 FAIL/03中断及六组未完成保持，不再完整随机长链或新结构。压力步骤尚未实现，不凭计划解锁后级；监督每30s保存身份/主机启动/全局四端口进度，无checkpoint开发。')
    print(r['status'],sha(ev))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['Prepare']);ap.parse_args();prepare()
