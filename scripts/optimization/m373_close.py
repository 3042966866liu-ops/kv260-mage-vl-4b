"""Close verified capability evidence and freeze the next bounded diagnostic plan."""
import json
from m351_workflow import ROOT, HERE, BASE, sha, encoded, atomic, sync
from m373_workflow import PKG, RUN, decode

def main():
    log=ROOT/'tmp/m373/component_uart.log'
    digest,raw,row=decode(log.read_text(encoding='utf-8-sig'))
    assert digest=='52d05d3aa2ab204fa53a9281804b5ad76e15fdd92c6376780bf506fe60868067'
    assert (RUN/'BOARD_RESULT.json').read_bytes()==raw
    assert 'M373_DONE gate_rc=0 export_rc=0' in log.read_text(encoding='utf-8-sig')
    assert '__M373_COMPONENT_RC_0__' in log.read_text(encoding='utf-8-sig')
    manifest=json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    assert sha(PKG/'PACKAGE_MANIFEST.json')==row['manifest_sha256']
    for entry in manifest['files']:
        assert sha(PKG/entry['path'])==entry['sha256'] and (PKG/entry['path']).stat().st_size==entry['bytes']
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    assert board['latest_m373_future_wait_board']['sha256']==digest
    assert all(digest in (ROOT/p).read_text(encoding='utf-8-sig') for p in ('CURRENT_STATE.md','docsMILESTONES.md'))
    result=dict(status='PASS_BOARD_FUTURE_CONDITION_CAPABILITY_CLOSED',evidence_level='BOARD_CPU_COMPONENT_ONLY',
        raw_sha256=digest,manifest_sha256=row['manifest_sha256'],log_sha256=sha(log),raw_chunks=6,
        original_gate_rc=0,export_rc=0,tests_run=17,python=row['platform']['python'],numpy=row['numpy_version'],
        frozen_future_source_sha256=row['blocking_probe']['future_result_source_sha256'],
        actual_fixture_wait_observed=True,condition_and_runtime_binding_restored=True,live_workers=0,
        trace_exclusive_closure_ns=0,actual_model_wait_seconds=None,model_forward_calls=0,fpga_transactions=0,
        overlay_loaded=False,ps_prefetch_enabled=False,ps_candidate_admission_resolved=False,
        numerical_pass=False,performance_pass=False,formal_promotion_allowed=False,
        rejected_attempts=['Offline harness initially used a tuple rather than platform.uname named fields. Its mocked success gate was rejected; named-field test environment corrected before upload. Package/observer unchanged; no board retry.'],
        next_step='Freeze one representative layer diagnostic with wait observer, reusing M365 same inputs/math/reference/sealed seven DMA. Do not repeat M371 broad profiling or enable PS prefetch.')
    path=BASE/'runs/M373-future-wait-closure-01/RESULT.json'
    atomic(path,encoded(result),immutable=True);closed=sha(path)
    note=f'## M373 等待钩子板端能力已闭合（2026-10-03）\n\n实际板端 Python3.10.12/NumPy1.26.4，17项 CPU 组件检查通过；真正 Future 内部 Condition.wait、异常/取消/重试与绑定恢复通过，工作线程0、trace 闭合误差0。原 gate/export rc0，6个900B以内分块原字节 SHA {digest}。原始 {(RUN/"BOARD_RESULT.json").relative_to(ROOT).as_posix()}；闭合 {path.relative_to(ROOT).as_posix()} SHA {closed}。没有 Overlay/真实权重/模型/FPGA，不是模型等待秒数或新增性能收益。主机模拟 uname 类型错误已在上传前修正；未改冻结包、未重跑板端。下一步只准备代表性单层实际等待诊断；PS预读仍关闭，容量准入未解决。'
    sync('latest_m373_future_wait_closure',dict(status=result['status'],result=path.relative_to(ROOT).as_posix(),sha256=closed,raw_sha256=digest,performance_pass=False),note)
    atomic(path.parent/'REPORT.md',('# M373 板端等待钩子能力结果\n\n'+note+'\n').encode('utf-8'),immutable=True)
    layer=board['latest_m365_staged_layer_closure'];assert sha(ROOT/layer['result'])==layer['sha256']
    plan='''# M374 代表性单层实际 Future 等待诊断规格

状态：仅准备规格，尚无新硬件包、上传或实际模型等待数据。

## 要回答的问题

在 M357 并行核上，主线程有多少时间真正进入 pack/parse Future 的 Condition.wait？解析 worker 的累计时间与主线程等待必须分别报告。复用 M365 层0的159个重复固定文本 embedding 输入与完整冻结参考；它不是原159-token视频输入，因此不能外推完整视频等待或提速。

## 输入与运行范围

- 同候选 Build0x4D333537、同 M238/M241 数学/量化/权重/缩放重试。
- 层0五个 family：q、kv、attention_out、gate_up、mlp_down；覆盖 Q/W4 与 MLP 代表链。
- 原参考25逻辑/25物理、0重试、48,381,952B暂存；另一次同Overlay合法最小事务仅作生命周期确认，不算语言调用。
- 原7块 DMA 分配与独立 M365 sealed-allocator/普通PS预算、物理事务检查、失败保留和安全释放规则。无新增 DMA、无PS预读 slot、无新worker、无视觉/LMhead/多层forward。
- 保留原生产准入；诊断通过也不授予长期服务准入。

## 只加入观察

先核对 M373 原始/闭合、M365 单层参考和同SHA硬件证据。M372 observe_runtime 默认关闭，显式启用后仅替换冻结方法中的两处 Future.result 调用；source SHA失败时尚未绑定。原 Future 异常和 timeout=None 不变。

每个family用独立 trace span。pack/parse结果各25条，T32 start=0/32/64/96/128；每family3次复用边界、2次结尾，共15/10。记录 ready_before、真实 Condition.wait 次数/时间、result总时间、chain/family/start。ready_before=False不自动证明阻塞。

为避免采集函数误归因，family计时只包住原调用，内存检查、输入/输出哈希置于计时外；观察器的常规纳秒计时开销属于诊断。绑定在成功/异常时按 owned/inherited 属性恢复，核对没有遗留实例方法。完整输出、K/V、family输入输出、重试顺序、调用和字节必须等于原参考。

## 汇总与停止条件

Condition.wait时间是主线程等待墙钟，含唤醒/调度，不是纯CPU停顿或可完全消除的收益。它是result总时间的子项，不能叠加；worker解析累计也不能加进主线程墙钟。核对所有父子span、主线程exclusive闭合、按family/复用或结尾分组；不得只凭时间重叠推定阻塞。

失败停在单层，不扩固定视频，不kill/reset释放活跃DMA。收集失败只补取已保存字节；原始atomic SHA及BOARD/CURRENT/docs三同步后裁决。单层通过再决定一次窄范围固定视频等待观测；不重复M371全面画像，不启动M332方案，不启动预取或性能对照。
'''
    directory=BASE/'runs/M374-layer-future-wait-plan-01'
    atomic(directory/'PLAN.md',plan.encode('utf-8'),immutable=True)
    pending=dict(status='PLAN_ONLY_REPRESENTATIVE_LAYER_WAIT_DIAGNOSTIC',prior_m373_closure_sha256=closed,
        prior_m365_layer_closure_sha256=layer['sha256'],plan_sha256=sha(directory/'PLAN.md'),target_build_id='0x4D333537',
        expected_families=5,expected_logical_calls=25,expected_pack_results=25,expected_parse_results=25,
        hardware_package_ready=False,board_run=False,actual_model_wait_s=None,ps_prefetch_enabled=False,performance_pass=False)
    atomic(directory/'RESULT.json',encoded(pending),immutable=True);pd=sha(directory/'RESULT.json')
    sync('latest_m374_layer_wait_plan',dict(status=pending['status'],result=(directory/'RESULT.json').relative_to(ROOT).as_posix(),sha256=pd),
        f'## M374 代表性层0等待诊断范围已冻结（2026-10-03）\n\n仅规格，包尚未实现/上传/执行；复用 M365 同输入、5family/25逻辑、sealed七DMA及完整数值参考，M373板端等待能力为前提，计时仅围原family调用。记录真正Condition.wait、result总时间及复用/结尾边界，不能将worker累计解析时间当阻塞或收益。规格 {(directory/"PLAN.md").relative_to(ROOT).as_posix()}；结果 SHA {pd}。下一步准备隔离单层观察包和实际冻结方法检查，原生产/预取关闭状态保持。')
    print('M373_CLOSED_AND_M374_SCOPED',closed,pd)

if __name__=='__main__':main()
