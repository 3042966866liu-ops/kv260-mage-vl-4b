"""Offline PS-slot review and Future-wait observation readiness, no board I/O."""
import ast
import hashlib
import json
from pathlib import Path
import platform
import sys

import m351_workflow as w
from m372_future_wait import FutureWaitObserver, PINNED

OUT = w.BASE / 'runs/M372-prefetch-and-future-review-01'
SOURCE_ROOT = w.ROOT / 'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
PREREQUISITES = {
    'latest_m350_ps_read_ahead_design': '087bd3fe93ef78d33e306f4b431937da01266b37a46995cd5a8b557e9719c256',
    'latest_m351_ps_component_board': '6274767c15ac4ea5c81e6289ef4f90d6cd7cd32c5735b5617e6c3a450cf8ef41',
    'latest_m352_capacity_failure_closure': '12b752069e7f1c59cd191ce42ca053541f58886ae7b3e32fa9327c047afaf61d',
    'latest_m371_candidate_profile_closure': '6e95781383547a83648939d1a73f4818e0c326fd088b48875fc02ac2035b5bbe',
}


def calls(node, name):
    return [n for n in ast.walk(node) if isinstance(n, ast.Call)
            and ((isinstance(n.func, ast.Attribute) and n.func.attr == name)
                 or (isinstance(n.func, ast.Name) and n.func.id == name))]


def main():
    recovery = {}
    texts = {}
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md', 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md',
                 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        texts[name] = (w.ROOT / name).read_text(encoding='utf-8-sig')
        recovery[name] = dict(sha256=w.sha(w.ROOT / name), chars=len(texts[name]))
    board = json.loads(texts['deployment/mage_vl4b/BOARD_GATE_RESULT.json'])
    priors = {}
    for key, expected in PREREQUISITES.items():
        row = board[key]
        assert row['sha256'] == expected and w.sha(w.ROOT / row['result']) == expected
        assert all(expected in texts[n] for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
        priors[key] = json.loads((w.ROOT / row['result']).read_text(encoding='utf-8'))
    pkg = w.BASE / 'candidates/M351-ps-read-component-01'
    component = pkg / 'ps_read_ahead.py'
    manifest = json.loads((pkg / 'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    member = next(x for x in manifest['files'] if x['path'] == 'ps_read_ahead.py')
    assert w.sha(component) == member['sha256'] == w.sha(w.HERE / 'ps_read_ahead.py')
    source = component.read_text(encoding='utf-8')
    tree = ast.parse(source)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'PSReadAheadSession')
    methods = {n.name:n for n in cls.body if isinstance(n, ast.FunctionDef)}
    assert len(calls(methods['__enter__'], 'bytearray')) == 1
    assert 'self.slot = [bytearray(self.maximum) for _ in range(4)]' in source
    assert not calls(tree,'allocate') and not calls(tree,'tobytes') and not calls(tree,'mmap')
    read = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name == 'read_exact_into')
    assert len(calls(read,'readinto')) == 1 and not calls(read,'read')
    assert len(calls(methods['_read'],'memoryview')) == 1 and len(calls(methods['stage'],'frombuffer')) == 1
    assert 'ThreadPoolExecutor(max_workers=1' in source
    assert min(n.lineno for n in calls(methods['stage'],'_submit')) > max(n.lineno for n in calls(methods['stage'],'sync_to_device'))
    close = methods['close']
    assert min(n.lineno for n in calls(close,'clear')) > max(n.lineno for n in calls(close,'shutdown'))
    assert 'if not self.future.done():' in source and 'raise RetainedPSResourcesError' in source
    assert 'if row[\'CmaFree\'] < RESERVE' in source
    checks = ['same-SHA M351 component remains unchanged', 'four fixed bytearrays; one ordinary PS slot',
              'zero explicit extra DMA allocator/mmap/tobytes calls', 'unbuffered readinto and transient memoryviews',
              'one prefetch executor; metadata-only completed Future', 'all four copies/syncs before next submission',
              'timeout preserves running worker, slot and original owner', 'worker drain/device safety before slot clear',
              'inherited stage binding restored and runtime owner removed on safe close',
              'original 64MiB memory gate remains unchanged']
    closure = json.loads((w.BASE / 'candidates/M371-candidate-prefill-profile-01/SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    frozen_files = {x['path']:x['sha256'] for x in closure['files']}
    verified = []
    for module in ('board_runtime','m238_prefill_runtime','m236_prefill_runtime','m230_prefill_runtime'):
        relative = closure['modules'][module]
        path = SOURCE_ROOT / relative
        assert w.sha(path) == frozen_files[relative]
        verified.append(dict(module=module,path=path.relative_to(w.ROOT).as_posix(),sha256=w.sha(path)))
    plan_path = w.BASE / 'runs/M350-ps-read-ahead-design-01/WINDOW_PLAN.json'
    design = priors['latest_m350_ps_read_ahead_design']
    assert w.sha(plan_path) == design['window_plan_sha256']
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    assert len(plan) == 162 and sum(x['payload_bytes'] for x in plan) == 2034890752
    assert max(x['bytes_per_port'] for x in plan) == 6963200
    for name in ('m372_future_wait.py','test_m372_future_wait.py'):
        ast.parse((w.HERE/name).read_text(encoding='utf-8'), feature_version=(3,10))
    # Final 17-test run was observed immediately before this immutable audit.
    test_receipt = json.loads((w.ROOT / 'tmp/m372/test-receipt.json').read_text(encoding='utf-8'))
    assert test_receipt['exit_code'] == 0 and test_receipt['tests_run'] == 17
    assert all(w.sha(w.HERE/n) == digest for n,digest in test_receipt['source_sha256'].items())
    observer = FutureWaitObserver(type('NoTrace', (), {})())
    raw_path = w.BASE / 'runs/M371-candidate-profile-board-01/BOARD_RESULT.json'
    raw = json.loads(raw_path.read_text(encoding='utf-8'))
    summary = json.loads((raw_path.parent/'PROFILE_SUMMARY.json').read_text(encoding='utf-8'))
    profile_closure = priors['latest_m371_candidate_profile_closure']
    assert w.sha(raw_path) == profile_closure['raw_sha256']
    result = dict(status='PASS_OFFLINE_PS_SLOT_REVIEW_AND_FUTURE_OBSERVER_READY',
        evidence_level='L0_NEW_AUDIT_AND_OBSERVER_CHECKS_WITH_PRIOR_BOARD_EVIDENCE',
        stable_build_id='0x4D395832', target_build_id='0x4D333537', recovery_read=recovery,
        prior_evidence_sha256=PREREQUISITES, component_sha256=w.sha(component),
        verified_source_files=verified, source_checks=checks,
        ps_budget=dict(payload_bytes=27852800, payload_mib=26.5625, ports=4,
            bytes_per_port=6963200, extra_pynq_allocation_calls=0, additional_workers=1,
            full_window_copies_explicit_in_candidate=0, source_read_into_existing_slot=True,
            foreground_copy_and_sync_remain=True, file_cache_growth_bounded=False,
            native_rss_peak_proven=False, metadata_and_thread_overhead_measured=False),
        schedule=dict(language_families=154, heads=8, stages=162, staged_bytes=2034890752,
            slot_overwrite_after_all_four_sync=True, old_weights_retained_through_all_t32_and_retries=True,
            live_worker_timeout_retains_resources=True,
            completed_session_still_references_runtime_and_layouts_until_caller_drops_session=True),
        previous_slot_rejection_before_allocation=True,
        current_loaded_cma_bytes=raw['loaded_capacity']['cma_free_bytes'],
        existing_component_cma_threshold_bytes=64<<20,
        unchanged_component_would_admit_current_load=False,
        candidate_admission_resolved=False, ps_prefetch_enabled=False,
        future_observer=dict(pinned_method_sha256=PINNED,
            host_future_result_sha256=observer.future_result_source_sha256,
            python=platform.python_version(), tests=test_receipt,
            inherited_and_owned_binding_restoration=True, numerical_and_retry_order_cpu_checks=True,
            result_payload_retained=False, actual_condition_wait_measured_in_cpu_tests=True,
            board_python310_condition_wait_support_proven=False,
            whole_future_result_is_not_pure_wait=True,
            expected_fixed159_pack_results=770, expected_fixed159_parse_results=770,
            expected_parse_buffer_reuse_boundaries=462, expected_parse_family_tail_boundaries=308),
        existing_trace=dict(raw_sha256=profile_closure['raw_sha256'],
            worker_parse_s=summary['background_exclusive_s_do_not_add']['_parse_into_and_check'],
            main_family_self_s=summary['main_exclusive_s']['language_family'],
            temporal_overlap_s=profile_closure['family_self_overlap_with_worker_parse_s'],
            actual_parse_future_condition_wait_s=None,
            cannot_infer_condition_wait_from_temporal_overlap=True),
        rejected_attempts=['Initial local source pins used AST segment indentation rather than inspect normalized function source. Four CPU tests rejected before any runtime patch. Pins corrected from the exact frozen function source; final 17 checks passed. No upload/board action.'],
        source_sha256={n:w.sha(w.HERE/n) for n in ('m372_future_wait.py','test_m372_future_wait.py','m372_audit.py')},
        new_board_run=False, overlay_loaded=False, numerical_pass=False, performance_pass=False,
        stable_service_changed=False, production_policy_changed=False, formal_promotion_allowed=False,
        next_step='Prepare one no-Overlay board Future/Condition capability fixture first; independently justify sealed-DMA PS-slot admission and worker lifecycle before any model binding. Do not rerun M332 or enable prefetch automatically.')
    assert result['current_loaded_cma_bytes'] < result['existing_component_cma_threshold_bytes']
    w.atomic(OUT/'RESULT.json', w.encoded(result), immutable=True)
    report = '''# M372：普通PS预读复盘与输出Future等待观察

本次完成离线复盘和观察器检查，没有新上板、模型推理或提速成绩。候选核仍为0x4D333537，稳定回滚为0x4D395832；已有M369固定视频请求收益保持。原M350/M351组件与稳定运行源码均未修改。

## 普通PS预读：内存和所有权

| 项目 | 核查结果 |
|---|---|
| 新增用户载荷 | 一个四端口slot，共27,852,800B / 26.5625 MiB |
| 额外专用CMA申请 | 组件显式0次；原七块DMA仍复用 |
| 读取副本 | 无缓冲readinto直接写slot；memoryview/np.frombuffer是视图，源代码未构造第二份完整窗口 |
| 原始临时块 | 原read函数每端口返回一个最多6,963,200B块；不能据此把该值直接从新增RSS预算中扣除 |
| 前景保留成本 | 等待READY、四端口复制及sync_to_device仍必需 |
| 并行线程 | 新增一个权重读取worker，原M238的pack/parse worker仍存在，竞争尚未实测 |
| 未纳入载荷的成本 | Python/计划/文件/线程元数据、线程栈、原生临时对象及系统文件缓存；零额外allocate不等于零内存压力 |
| 读取计划 | 154语言family+8个LM head，共162窗口；2,034,890,752B，原顺序/offset/size不变 |

第一次窗口等待没有前序PL工作可隐藏。四端口全部复制和同步成功后，才向唯一worker提交下一窗口；当前原CMA权重保留至所有T32、输出解析和缩放重试完成。任何复制/同步失败禁止下一次PL提交，不静默回退。

超时且worker尚未结束时保留slot、session、原runtime、DMA缓冲和进程；不能取消后释放或kill/reset。正常退出先确认worker/fd/view都结束以及设备安全，再恢复原_stage绑定、解绑runtime owner并清slot。**closed session本身仍引用runtime和layout**：外层应仅保留纯元数据record，并在安全释放后丢弃session/future/executor引用，避免沿用M370历史诊断owner保留模式；组件不能自行关闭共享layout。

stage_ms当前记录后台read_work+前景copy/sync，不是暴露在主线程的等待。判断收益应使用独立foreground_wait/copy/sync和完整请求计时；后台工作时长不能当作节省量。每个阶段的chain metadata SHA、文件身份和容量检查也有成本，不把26.88秒全部视为可隐藏。

## 接入裁决

M351的28项真实板端CPU fixture检查已PASS；它使用明确fake MMIO/缓冲/容量，未证明实际模型预读。M352在slot分配前因64MiB CMA政策拒绝，worker没有启动。当前M371构造后CMA32.617188MiB，运行期间100ms采样最低1.992188MiB；原封锁新增DMA的固定诊断可以完成，但**未证明再增加PS slot也能完成**。

原组件_memory仍要求CMA≥64MiB，按原规则会拒绝这次加载状态。本次不修改它。接入前必须独立冻结新准入规则：七块原缓冲实际成功/地址范围有效、额外DMA申请封锁、同Overlay合法最小事务、slot真实分配触页后的PS增长和MemAvailable、视觉及每次提交的复查、worker活动故障保留和安全退出。规则须明确原生/缓存压力和停止条件；不能以普通可用内存很多或额外allocate为0直接认定容量已成立，也不能把旧政策拒绝当作预读无收益。

## 输出解析：观测真正的等待

已有33.663709秒是后台解析调用墙钟，很多与主线程重叠，不是33.66秒主线程阻塞。在M371现有trace中，相关解析future等待若发生会落在language_family主线程self15.070836秒中；12.203979秒与后台解析在时间上重合，仍不能证明全部是future阻塞。

新增默认关闭观察器只替换冻结M238 language_family_many中pack_future.result()、M236 _resolve_pending中pending.future.result()这两处调用。经规范化源SHA和撤销插桩后的AST对比，其他原语句不变。每次记录：

- result调用前是否ready、整个result调用墙钟、原异常。
- **该result实际进入Condition.wait的次数及等待墙钟**；只有这一层进入等待才证明调用阻塞，而不是依靠ready快照猜测。
- layer/family/chain/token_start；固定159路径预期770个pack result、770个parse result。parse边界中462个缓冲复用、308个family末尾drain，计数不是阻塞次数。

Condition.wait时间包含被唤醒后的调度，不是纯CPU停顿周期。它嵌套在future.result span中，主线程独占统计不得重复相加。钩子只临时替换单个Future的condition.wait，不修改全局Future/ThreadPoolExecutor；原返回、异常、取消和timeout=None语义保持，finally恢复实例原绑定，不保存Future或结果张量。

17项本机检查PASS：真实Future未就绪等待/完成即返、ready竞态、异常/取消、等待中断、记录上限、源码漂移、默认关闭、原绑定恢复、不留结果引用，以及执行**实际冻结M238/M236方法**的159-token五块输出/重试一致性和完整trace闭合。PL、输入/输出缓冲和解析内容为明确CPU替身，这不证明板端等待秒数；Python3.10语法通过也不等于板端private Condition实现已验证。

## 下一具体步骤

先准备无Overlay的板端Future/Condition小组件，验证实际Python3.10调用与恢复；通过并同步后，将观察器用于已通过数值的代表family或固定159诊断，保持原解析、输入策略和核。与此同时独立论证PS-slot准入与生命周期，再决定是否绑定模型。只观察result/等待，不重做已退化的M332解析策略，不自动运行视频或启用预读。
'''
    report += '\n原证据SHA：\n\n' + '\n'.join(f'- {k}: `{v}`' for k,v in PREREQUISITES.items()) + '\n'
    w.atomic(OUT/'REPORT.md', report.encode('utf-8'), immutable=True)
    digest = w.sha(OUT/'RESULT.json')
    w.sync('latest_m372_prefetch_future_review', dict(status=result['status'],sha256=digest,
        result=(OUT/'RESULT.json').relative_to(w.ROOT).as_posix(),board_run=False,
        candidate_admission_resolved=False,performance_pass=False,formal_promotion_allowed=False),
        f'## M372 普通PS预读与输出future等待复盘（2026-10-03）\n\n候选0x4D333537/稳定0x4D395832；M350/M351原组件保持，一slot26.5625MiB、额外DMA申请0、后台readinto且四复制同步后才覆写，临时视图无第二完整窗口；native/线程/页缓存压力未证。safe close后外层仍须丢弃session对runtime/layout引用。原64MiB组件规则拒绝M371构造CMA32.617188MiB，未接入预读，不下调门槛。默认关闭future观察器在两处实际冻结result调用记录真正Condition.wait，17项真实Future/实际冻结159调度与重试、恢复/引用/trace闭合本机PASS，仅CPU替身，板端3.10能力及主线程阻塞秒数未证；初始缩进源SHA误差先拒绝、修正后通过。证据SHA `{digest}`。0新上板/模型/FPGA；不重做M332，不宣称新增收益。下一步仅无Overlay板端小组件能力，再独立准入论证/代表family等待诊断，不自动视频或启用预读/服务。')
    print(json.dumps(dict(status=result['status'],sha256=digest,checks=len(checks),future_tests=17,board_run=False)))


if __name__ == '__main__': main()
