"""Freeze a narrow video wait contract from synchronized existing evidence only."""
import ast
from collections import Counter, defaultdict
import json
from pathlib import Path
from m351_workflow import ROOT, HERE, BASE, sha, atomic, encoded, sync

OUT = BASE / 'runs/M375-video-wait-plan-01'
PKG = BASE / 'candidates/M369-light-video-01'


def main():
    if OUT.exists():
        raise RuntimeError('Immutable plan exists; inspect it instead of repeating')
    board = json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8-sig'))
    prior = {}
    for key in ('latest_m374_layer_wait_closure', 'latest_m373_future_wait_closure',
                'latest_m371_candidate_profile_closure', 'latest_m369_light_video_closure'):
        row = board[key]
        assert sha(ROOT/row['result']) == row['sha256']
        assert all(row['sha256'] in (ROOT/name).read_text(encoding='utf-8-sig')
                   for name in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
        prior[key] = row['sha256']
    assert board['latest_m374_layer_wait_closure']['status'] == 'PASS_SINGLE_LAYER_ACTUAL_WAIT_OBSERVED'
    manifest_sha = sha(PKG/'PACKAGE_MANIFEST.json')
    assert manifest_sha == 'dc22fc6c4e8718832877640f7cd768dda12bf63c8e057239ad1fa902295fdd73'
    manifest = json.loads((PKG/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    for row in manifest['files']:
        assert sha(PKG/row['path']) == row['sha256']
    expected = json.loads((PKG/'VIDEO_EXPECTED.json').read_text(encoding='utf-8'))['baseline']
    groups = defaultdict(list)
    for row in expected['scale_attempts']:
        if row['layer'] is not None:
            groups[(row['layer'], row['family'], row['chain_index'])].append(row)
    assert len(groups) == 154
    assert all(len(rows) == 5 for rows in groups.values())
    assert set(k[0] for k in groups) == set(range(36))
    assert expected['logical_calls'] == 778 and expected['host_calls'] == 781
    assert sum(len(r['attempted_shifts'])-1 for rows in groups.values() for r in rows) == 3
    # Verify retries parse synchronously: they must not be falsely counted as Futures.
    source_closure = json.loads((PKG/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    release = ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    source_paths = {r['module']: r['path'] for r in source_closure['files'] if 'module' in r}
    if 'm236_prefill_runtime' not in source_paths:
        source_paths = {Path(r['path']).stem: r['path'] for r in source_closure['files']}
    p = release/source_paths['m236_prefill_runtime']
    text = p.read_text(encoding='utf-8')
    node = next(n for n in ast.walk(ast.parse(text)) if isinstance(n, ast.FunctionDef) and n.name == '_resolve_pending')
    calls = [ast.unparse(n.func) for n in ast.walk(node) if isinstance(n, ast.Call)]
    assert calls.count('pending.future.result') == 1
    assert calls.count('self._parse_buffer') == 1 and calls.count('self._launch_once') == 1
    sources = {n: sha(PKG/n) for n in ('VIDEO_EXPECTED.json', 'VISUAL_EXPECTED.json',
                                     'm369_trials.py', 'm369_light_video_gate.py', 'm369_light_policy.py')}
    sources['m372_future_wait.py'] = sha(HERE/'m372_future_wait.py')
    contract = [dict(layer=layer, family=family, chain_index=chain,
                     pack_token_order=[0,32,64,96,128], parse_token_order=[0,32,64,128,96])
                for layer,family,chain in groups]
    result = dict(status='PLAN_ONLY_NARROW_FIXED_VIDEO_FUTURE_WAIT', build_id='0x4D333537',
        prior_sha256=prior, source_sha256=sources, base_manifest_sha256=manifest_sha,
        language_family_count=154, family_counts=dict(Counter(k[1] for k in groups)),
        expected_pack_results=770, expected_parse_results=770, synchronous_retries=3,
        expected_logical_calls=778, expected_physical_calls=781, legal_minimal_calls=1,
        result_record_bound=4096, trace_event_bound=4096,
        trace_event_upper_bound=1+154+2*(770+770), family_contract=contract,
        frames='Original four source frames; original last-frame two views only', input_tokens=159,
        diagnostic_request_count=1, additional_dma_allocations=0, new_workers=0, ps_prefetch_enabled=False,
        production_policy_changed=False, original_reference_reused=True,
        gate_preparation_complete=False, board_run=False, numerical_pass=False, performance_pass=False,
        next_step='Implement default-disabled video wrapper, independent bounded trace validator, and frozen-call success/retry/failure tests; then freeze a new package and collector/control evidence before one board request.')
    assert result['trace_event_upper_bound'] == 3235 < result['trace_event_bound']
    report = '''# M375 固定视频实际等待诊断规格

目标只回答：候选核的语言 Prefill 中，主线程等权重打包和输出解析的实际时间各是多少，发生在哪些层、family 和输出槽复用边界。复用 M373/M374 已验证的原 Future.result/Condition.wait 钩子；不重新执行 M371 的全面画像。

沿用 M369 同输入和数值参考、原完整 runtime 构造、稀疏分阶段容量规则、原七块 DMA、合法最小事务及退出恢复。仅一次候选 B 请求，不启用 PS 权重预读，不增加 worker、CMA bank 或模型张量持有。预处理、视觉特征、159-token 输入、语言输出、151936 logits、72 份 KV、最终判断和完整事务合同在计时后保持逐位核对。

已从原参考提取 154 个语言 family：q/kv 各10，qkv26，attention_out/gate_up/mlp_down 各36。每个 family 有5个 T32块，pack 与 parse 各770次 result。不能把单层的五 family 简单乘36。LM head另8次逻辑调用；三次同步缩放重试由原执行器保持，不新增 Future result，物理总781，再加一次合法最小事务。

pack顺序0、32、64、96、128；parse按原双输出槽回收顺序0、32、64、128、96。单个请求trace仅包含 Prefill 根、154 family、1540 result和至多1540 Condition.wait，最大3235事件，4096硬上限；记录只含标识和时间，不保存历史Future、输入或输出数组。必须逐层/chain独立验证身份、顺序、计时嵌套及主线程独占闭合，拒绝缺失、重复、越界、未恢复绑定和带异常的PASS。

使用新目录、新默认关闭runner和显式开关。完整来源/同SHA硬件证据、递归依赖、Python3.10、实际冻结调用的成功/同步重试/异常恢复、收集正例及破损负例通过后才可上传。COM3确认shell及同终端sudo，manifest-first分块不超过1800B，板端全部SHA/bash-n及固定环境通过后仅执行一次。保存结果或运行日志存在时只能收集；主gate rc不得被导出覆盖。活动DMA或worker故障保留缓冲及进程，不能超时kill回收。raw原子SHA与BOARD/CURRENT/docs同步后才能裁决。

报告分别给出 result总墙钟、Condition.wait墙钟、已就绪比例，按layer/family与复用/结尾拆分。Condition.wait包含唤醒调度且嵌套在result墙钟中，不能相加；同步重试解析和LM head不在此钩子覆盖范围。此次诊断带观察开销，不用于新增性能百分比，M369约40.81%的原独立性能结论保持。解析暴露等待较大才讨论解析方案；较小则优先评估已有普通PS内存预读的独立准入，不直接改曾退化的M332。

当前仅规格冻结，尚未实现视频适配器、测试包或上板。
'''
    atomic(OUT/'PLAN.md', report.encode('utf-8'), immutable=True)
    result['plan_sha256'] = sha(OUT/'PLAN.md')
    atomic(OUT/'RESULT.json', encoded(result), immutable=True)
    digest = sha(OUT/'RESULT.json')
    sync('latest_m375_video_wait_plan', dict(status=result['status'],
        result=(OUT/'RESULT.json').relative_to(ROOT).as_posix(), sha256=digest,
        board_run=False, performance_pass=False),
        f'## M375 固定视频窄等待诊断规格（2026-10-03）\n\nBuild0x4D333537；M374单层已闭合，进一步只观察原固定159视频Future实际等待。原参考154 family/pack770/parse770、3同步重试、778逻辑/781物理另1minimal，q/kv各10、qkv26而非36层都五family；最大3235 trace事件、上限4096，0新增DMA/worker/PS预读。原数学/输入/容量策略和M369数值参考保持；不重跑M371全面画像。规格SHA {digest}，PLAN SHA {result["plan_sha256"]}。仅离线规格、视频适配/收集控制未准备，未上板。下一步默认关闭适配器及严格独立验证/故障测试。')
    print(json.dumps(dict(status=result['status'], sha256=digest,
                         family_count=154, pack_results=770, parse_results=770, trace_bound=4096)))


if __name__ == '__main__':
    main()
