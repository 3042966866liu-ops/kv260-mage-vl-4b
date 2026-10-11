"""Close existing RSS evidence; offline object ownership, not native RSS proof."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import types
import weakref

import numpy as np
import m351_workflow as w
from m370_patch_scope import PatchScope

PKG = w.BASE / 'candidates/M369-light-video-01'
OUT = w.BASE / 'runs/M370-rss-and-admission-audit-01'
SOURCE_ROOT = w.ROOT / 'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
RAW_SHA = '0d0b0825f2987db5b76a36c88c215ca6faac1e4d439a922ba8c81fc1674f0628'


def legacy_patch_check():
    source = PKG / 'm369_light_video_gate.py'
    main = next(n for n in ast.parse(source.read_text(encoding='utf-8')).body
                if isinstance(n, ast.FunctionDef) and n.name == 'main')
    fn = next(n for n in main.body if isinstance(n, ast.FunctionDef) and n.name == 'patch')
    env = {'restorations': []}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(fn)], type_ignores=[])), str(source), 'exec'), env)

    class Owner:
        def method(self):
            return 1

    refs = []
    for _ in range(8):
        owner = Owner()
        refs.append(weakref.ref(owner))
        # Exact original registry keeps owner and bound original method alive.
        env['patch'](owner, 'method', lambda: 2)
        del owner
    assert sum(r() is not None for r in refs) == 8
    for owner, name, original in reversed(env['restorations']):
        setattr(owner, name, original)
    del owner, name, original
    assert sum(r() is not None for r in refs) == 8
    return dict(actual_frozen_patch_ast_executed=True,
                owners_retained_before_final_restore=8,
                owners_retained_while_registry_still_present_after_restore=8,
                scope='CPU surrogate owners; no PYNQ/native byte attribution')


def scoped_checks():
    checks = []
    class Owner:
        def method(self):
            return 1
    scope = PatchScope()
    module = types.SimpleNamespace(flag=0)
    scope.patch(module, 'flag', 1)
    refs = []
    for _ in range(8):
        owner = Owner()
        refs.append(weakref.ref(owner))
        scope.patch(owner, 'method', lambda: 2)
        assert owner.method() == 2
        scope.restore_owner(owner, completion_proven=True, release_proven=True)
        assert owner.method() == 1 and 'method' not in vars(owner)
        del owner
    assert all(r() is None for r in refs)
    assert module.flag == 1 and len(scope.entries) == 1
    checks += ['eight completed surrogate owners released by normal references without GC',
               'inherited methods restored without self-bound instance overrides',
               'global patches preserved across per-owner restoration']
    owner = Owner()
    scope.patch(owner, 'method', lambda: 3)
    for a, b in [(False, True), (True, False), (1, True), (True, 1)]:
        try:
            scope.restore_owner(owner, completion_proven=a, release_proven=b)
        except RuntimeError:
            pass
        else:
            raise AssertionError('Unproven safety admitted')
        assert owner.method() == 3 and len(scope.entries) == 2
    checks += ['active/unreleased/nonboolean proof retains hooks and owner']
    scope.restore_owner(owner, completion_proven=True, release_proven=True)
    owner.x = None
    scope.patch(owner, 'x', 4); scope.patch(owner, 'x', 5)
    scope.restore_owner(owner, completion_proven=True, release_proven=True)
    assert owner.x is None
    checks += ['nested overrides restore reverse order and original None']
    scope.restore_all(completion_proven=True, release_proven=True)
    assert module.flag == 0 and not scope.entries
    checks += ['safe final restoration clears registry']
    return checks


def control_checks():
    """Execute original frozen stream harness with one isolated lifetime change."""
    original = (PKG / 'm369_trials.py').read_text(encoding='utf-8')
    revised = original.replace(
        'def run_trials(engine,runtime,policy,base,candidate,here,result,new_board,patch):',
        'def run_trials(engine,runtime,policy,base,candidate,here,result,new_board,patch,restore_trial=None):\n'
        "    if restore_trial is None:raise RuntimeError('M370 isolated cleanup disabled without explicit safe restorer')")
    old = '        del logits,kv,events,e,row,transactions\n'
    new = '        del logits,kv,events,e,row,transactions,head,observed_head\n        restore_trial(runtime,policy)\n'
    assert original.count(old) == 1 and revised.count(old) == 1
    revised = revised.replace(old, new)
    artifact = OUT / 'm370_trials.py'
    w.atomic(artifact, revised.encode('utf-8'), immutable=True)
    ast.parse(revised, feature_version=(3, 10))
    spec = importlib.util.spec_from_file_location('m370_trials_isolated', artifact)
    module = importlib.util.module_from_spec(spec)
    # Dependencies are exact previously frozen diagnostic components.
    sys.path.insert(0, str(PKG))
    spec.loader.exec_module(module)
    previous = sys.modules.get('m369_trials')
    sys.modules['m369_trials'] = module
    try:
        harness = (w.HERE / 'm369_component_checks.py').read_text(encoding='utf-8')
        harness = harness.replace('patches=[]', 'patches=[]; scope_registry=PatchScope(); cleanup_calls=[]')
        oldpatch = 'def patch(obj,name,value):patches.append((obj,name,getattr(obj,name)));setattr(obj,name,value)'
        assert harness.count(oldpatch) == 1
        harness = harness.replace(oldpatch,
            'def patch(obj,name,value):scope_registry.patch(obj,name,value)\n'
            '            def restore_trial(board,policy):\n'
            '                assert board._m368_closed and policy.safe()\n'
            '                assert result["released_buffers"]==list(reversed(board_rows))\n'
            '                assert scope_registry.restore_owner(board,completion_proven=True,release_proven=True)==4\n'
            '                cleanup_calls.append(board.build)')
        harness = harness.replace('trials.run_trials(engine,board,policy,base,root,root,result,new,patch)',
                                  'trials.run_trials(engine,board,policy,base,root,root,result,new,patch,restore_trial)')
        harness = harness.replace("assert kind is None and len(result['samples'])==8 and len(closed)==8",
                                  "assert kind is None and len(result['samples'])==8 and len(closed)==8 and len(cleanup_calls)==8")
        harness = harness.replace('for obj,name,value in reversed(patches):setattr(obj,name,value)',
                                  'scope_registry.restore_all(completion_proven=True,release_proven=True) # test teardown only; active case has fake MMIO')
        env = dict(__name__='m370_actual_control_checks', PatchScope=PatchScope)
        exec(compile(harness, str(w.HERE / 'm369_component_checks.py'), 'exec'), env)
        checked = env['checks']()
        checked += ['per-trial four hooks restored only after completion and exact seven releases',
                    'isolated cleanup parameter required; frozen M369 unchanged']
        return checked, artifact
    finally:
        if previous is None:sys.modules.pop('m369_trials', None)
        else:sys.modules['m369_trials'] = previous
        sys.path.remove(str(PKG))


def main():
    raw_path = w.BASE / 'runs/M369-light-video-board-01/BOARD_RESULT.json'
    assert w.sha(raw_path) == RAW_SHA
    raw = json.loads(raw_path.read_text(encoding='utf-8'))
    assert raw['gate_return_code'] == 0 and raw['all8_requests_completed']
    manifest = json.loads((PKG / 'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    assert w.sha(PKG / 'PACKAGE_MANIFEST.json') == 'dc22fc6c4e8718832877640f7cd768dda12bf63c8e057239ad1fa902295fdd73'
    for row in manifest['files']:
        assert w.sha(PKG / row['path']) == row['sha256']
        assert (PKG / row['path']).stat().st_size == row['bytes']
    closure = json.loads((PKG / 'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    for row in closure['files']:
        assert w.sha(SOURCE_ROOT / row['path']) == row['sha256']
    ownership = legacy_patch_check()
    tests = scoped_checks()
    control, artifact = control_checks()
    samples = []
    for s in raw['samples']:
        assert s['safe_buffers_released'] and s['released_buffers'] == list(reversed(s['allocated_buffers']))
        assert s['before_cache']['cache_bytes'] == s['after_cache']['cache_bytes'] == 66699264
        assert s['before_cache']['cache_entries'] == s['after_cache']['cache_entries'] == 26
        assert s['before_cache']['cache_misses'] == s['after_cache']['cache_misses'] == 26
        samples.append(dict(index=s['index'],variant=s['variant'],
            before=s['before_memory'],after=s['after_memory'],extrema=s['sampled_memory']['extrema'],
            cache_bytes=s['after_cache']['cache_bytes'],cache_entries=26,
            allocated_bytes=sum(a['bytes'] for a in s['allocated_buffers']),
            exact_reverse_release=True,scale_attempts_per_runtime=s['counts']['logical_calls']))
    production = dict(formal_promotion_allowed=False, service_changed=False,
        required_cma_reserve_bytes=64<<20, reserve_policy_changed=False,
        original_loaded_capacity=raw['loaded_capacity'],
        production_threshold_would_admit=raw['production_threshold_would_admit'],
        diagnostic_zero_extra_cma_is_not_production_admission=True,
        long_lived_scale_attempts_bounded=False,
        next_gate='Bounded fixed-input lifecycle observation with weakrefs, per-request tensor bytes, smaps_rollup and completed-request checkpoints; no new circuit or performance rerun. Production review remains separate.')
    assert production['production_threshold_would_admit'] is False
    result = dict(status='PASS_OFFLINE_RSS_OWNERSHIP_AUDIT_PRODUCTION_HELD',
        evidence_level='L0_SOURCE_AND_CPU_OBJECT_CONTROL_WITH_EXISTING_BOARD_RECORDS',
        stable_build_id='0x4D395832', candidate_build_id='0x4D333537',
        raw_sha256=RAW_SHA, verified_frozen_payload_files=len(manifest['files']),
        verified_release_source_files=len(closure['files']),samples=samples,
        final_disposal_snapshot=raw['stages'][-1],legacy_patch_ownership=ownership,
        isolated_scope_checks=tests,actual_stream_control_checks=control,
        isolated_trial_sha256=w.sha(artifact),patch_scope_sha256=w.sha(w.HERE/'m370_patch_scope.py'),
        cached_visual_components_bounded=True,cache_payload_bytes=66699264,
        historical_logits_KV_arrays_in_result=False,
        request_tensor_clear_present=True,
        released_dma_is_not_python_owner_disposal=True,
        released_callback_still_holds_bound_backend_method=True,
        native_RSS_growth_attribution_proven=False,memory_leak_proven=False,
        production=production,board_run=False,overlay_loaded=False,fpga_transactions=0,
        new_numerical_pass=False,new_performance_pass=False,formal_promotion_allowed=False)
    w.atomic(OUT/'RESULT.json',w.encoded(result),immutable=True)
    digest=w.sha(OUT/'RESULT.json')
    report=make_report(result,digest)
    w.atomic(OUT/'REPORT.md',report.encode('utf-8'),immutable=True)
    note=(f'## M370 RSS引用及生产准入核查（2026-10-02）\n\n'
          f'稳定0x4D395832/候选0x4D333537；复用M369原SHA `{RAW_SHA}`，校验{len(manifest["files"])}载荷及{len(closure["files"])}冻结源。视觉26项63.609375MiB未增长；逐轮logits/KV校验后清除。原诊断恢复列表确实保留8个历史运行时；实际patch AST/弱引用证明对象保留，不证明全部native RSS字节归因或泄漏。隔离作用域恢复组件及实际冻结stream显式替身检查通过，未安装或上板。长期scale_attempts无上限，生产64MiB准入仍不满足；当前只完成离线核查，RSS板端闭合/生产准入未通过，不正式接服务。'
          f'证据 `{(OUT/"RESULT.json").relative_to(w.ROOT).as_posix()}` SHA `{digest}`。下一步仅限定生命周期观测，安全完成后清诊断引用并记录weakref/缓存/匿名与文件页；不叠加新优化、不重跑性能、不降低门槛。\n\n')
    w.sync('latest_m370_rss_admission_audit',dict(status=result['status'],sha256=digest,
        result=(OUT/'RESULT.json').relative_to(w.ROOT).as_posix(),raw_sha256=RAW_SHA,
        board_run=False,rss_root_cause_proven=False,memory_leak_proven=False,formal_promotion_allowed=False),note)
    print(json.dumps(dict(status=result['status'],sha256=digest,scope_checks=len(tests),
                         actual_control_checks=len(control),report=str(OUT/'REPORT.md'))))


def make_report(r,digest):
    lines=['# M370 RSS增长与生产准入收尾核查','',
           '## 裁决','',
           '已找到诊断代码保留历史运行时的确定引用路径；尚未证明它解释全部RSS增量，也未证明内存泄漏。当前不接入稳定服务，不增加新优化。',
           '', '## 原板端数据','',
           '991→1127MiB是每轮100ms采样的最大RSS，不是每轮释放后的常驻值。请求前RSS、匿名页也有增长，不能只用最大值认定泄漏。请求后快照位于数值哈希、对象清除和close之前。',
           '', '|轮次|版本|请求前RSS MiB|请求后RSS MiB|采样最大RSS MiB|请求前匿名页 MiB|请求后匿名页 MiB|',
           '|---:|:---:|---:|---:|---:|---:|---:|']
    for s in r['samples']:
        b=s['before']['process_bytes'];a=s['after']['process_bytes']
        lines.append(f'|{s["index"]}|{s["variant"]}|{b["VmRSS"]/2**20:.3f}|{a["VmRSS"]/2**20:.3f}|{s["extrema"]["max_rss"]/2**20:.3f}|{b["RssAnon"]/2**20:.3f}|{a["RssAnon"]/2**20:.3f}|')
    final=r['final_disposal_snapshot']['memory']['process_bytes']
    lines += ['',f'最后安全关闭/PS对象处置快照：RSS {final["VmRSS"]/2**20:.3f}MiB，匿名页 {final["RssAnon"]/2**20:.3f}MiB，文件页 {final["RssFile"]/2**20:.3f}MiB。它处于全局patch恢复之前；没有恢复后的快照或逐轮smaps/native分配追踪。不能将残留匿名RSS等同于活跃张量字节。',
       '', '## 保存和释放路径','',
       '- `m369_trials.py`保存的是张量形状/类型/字节数/SHA，而不是每轮完整张量。`captured.clear()`、`del logits,kv,...`在下轮构造前执行；M241的K/V列表是prefill局部值，未写入模型历史缓存。',
       '- 视觉M261只缓存白名单26项packed codes/scales/qmin，固定66,699,264B（63.609375MiB，64MiB政策内）；八轮cache misses都为26，close清空组件并关闭四个mmap。它不能解释该轮逐次新增缓存。',
       '- 每轮七块CMA共33,484,832B（31.933624MiB），八轮都精确逆序释放。后端释放不等于Python所有者对象立即消失。',
       '- 全局`restorations`列表保存每轮runtime及其绑定的原方法，直到八轮结束。原patch函数AST在CPU上执行，弱引用证明8个历史所有者全部保留；即使恢复方法，只要列表仍在，它们仍保留。普通对象替身测试不证明PYNQ/驱动/匿名堆的实际字节。',
       '- 原恢复会把继承方法写回实例，产生绑定方法→自身引用；`OwnedBufferRelease`在released后仍持有绑定的后端释放方法。物理释放已证明，Python引用及循环回收时机需要独立观测。未为了验证调用GC/trim或清缓存。',
       '- `scale_attempts`保存的是缩放/重试元数据，没有上限。M369每轮新runtime，每个778条；长期服务复用runtime则会累积，不能沿用八轮结果宣称有界。family统计字典键来自固定154个family，KV不是这种永久元数据。',
       '', '## 隔离修正及验证','',
       '新增默认不接生产的`m370_patch_scope.py`，逐轮完成且七块释放确认后恢复该实例的四个诊断hook；继承方法删除实例override，全局patch继续保留。失败/未完成/释放未证明时保留引用。M369冻结包及稳定源码未改。派生`m370_trials.py`只改变清理时机，并要求显式安全restorer；未提供生产/板端自动安装入口。',
       f'CPU对象检查{len(r["isolated_scope_checks"])}项；原冻结stream实际执行控制检查{len(r["actual_stream_control_checks"])}项，覆盖8轮原顺序、完整校验、hash在计时外、正确释放、active DMA替身保留和坏视觉拒绝。模型/MMIO/容量均明确替身；不是新的板端数值、RSS或性能PASS。',
       '', '## 生产准入','',
       f'M369实际完整加载后CmaFree {r["production"]["original_loaded_capacity"]["cma_free_bytes"]/2**20:.6f}MiB，原保留门槛64MiB，`production_threshold_would_admit=false`。七缓冲实际成功后禁止新增CMA的独立诊断政策不能替代原准入。当前候选0x4D333537有固定视频数值及暖缓存完整请求净收益；内存常驻稳定性与正式生产准入仍未通过。',
       '原video_server/m243生产路径复用同一board；长期元数据边界、异常退出引用处置及Web入口候选门禁需在正式接入前核对。当前不改64MiB，不把它描述为代码推导的未来额外CMA需求，也不替换服务/回滚/boot/DTB/CMA。',
       '', '## 一个后续验证','',
       '先为同输入的有界生命周期观察入口增加每轮“哈希后→清张量后→安全close后→恢复该轮hook后”快照；记录weakref存活、当前张量payload、缓存项/bytes、线程数、smaps_rollup匿名/文件页。保持既有核、资产、输入、原计时边界和安全规则；失败保留活动DMA/进程/缓冲。无需再跑8轮性能来补这些检查点。实际RSS字节归因不清时保留UNPROVEN，生产继续关闭。',
       '', '## 证据','',f'原M369 raw SHA：`{RAW_SHA}`。',f'本次RESULT SHA：`{digest}`。',
       f'冻结载荷逐SHA通过{r["verified_frozen_payload_files"]}项；release/source闭包逐SHA通过{r["verified_release_source_files"]}项。',
       f'隔离scope SHA：`{r["patch_scope_sha256"]}`；派生trials SHA：`{r["isolated_trial_sha256"]}`。','']
    return '\n'.join(lines)


if __name__ == '__main__':
    main()
