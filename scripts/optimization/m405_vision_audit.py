"""Read existing evidence and frozen sources; no model import or board access."""
import hashlib
import json
import re
import statistics
from pathlib import Path

from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync


RAW_SHA = 'f83ba109292b171d94908632a2f69c8d74c1d075b301f66b259629433c4cb321'
AUDIT_SHA = 'e4ed4b37bfa2122e0d9dd5998665767dfd47bf3e346cd312bbd7080d3437ff8e'
OUT = BASE / 'runs/M405-vision-evidence-audit-01'


def identity(path):
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=path.stat().st_size,
                sha256=sha(path))


def main():
    if OUT.exists():
        raise RuntimeError('Audit output already exists; do not replace evidence')
    recovery = {}
    texts = {}
    for name in ('CURRENT_STATE.md', 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md',
                 'docsMILESTONES.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        p = ROOT / name
        texts[name] = p.read_text(encoding='utf-8-sig')
        recovery[name] = dict(identity(p), lines=len(texts[name].splitlines()))
    board = json.loads(texts['deployment/mage_vl4b/BOARD_GATE_RESULT.json'])
    keys = ('latest_m403_tail_performance_board', 'latest_m403_tail_performance_closure',
            'latest_m404_environment_board')
    prior = {}
    for key in keys:
        row = board[key]
        assert sha(ROOT / row['result']) == row['sha256']
        assert all(row['sha256'] in texts[name]
                   for name in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
        prior[key] = row
    assert prior[keys[0]]['sha256'] == RAW_SHA
    raw_path = ROOT / prior[keys[0]]['result']
    raw = json.loads(raw_path.read_text(encoding='utf-8'))
    assert raw['build_id'] == '0x4D333537' and raw['all8_requests_completed']
    assert raw['numerical_pass'] and not raw['performance_pass'] and not raw['errors']
    audit_path = BASE / 'runs/M348-loading-path-audit-01/RESULT.json'
    assert sha(audit_path) == AUDIT_SHA
    audit = json.loads(audit_path.read_text(encoding='utf-8'))
    pkg = BASE / 'candidates/M403-tail-performance-01'
    manifest_path = pkg / 'PACKAGE_MANIFEST.json'
    assert sha(manifest_path) == 'a1bfd96e1324fd86f89f574504c280dd64028f4ef2b54155cbcbd0a00377f1a8'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    id_path = pkg / 'M348_SOURCE_IDENTITIES.json'
    id_row = next(r for r in manifest['files'] if r['path'] == id_path.name)
    assert id_path.stat().st_size == id_row['bytes'] and sha(id_path) == id_row['sha256']
    ids = json.loads(id_path.read_text(encoding='utf-8'))
    assert ids['audit_raw_sha256'] == AUDIT_SHA
    id_map = {r['path']: r for r in ids['files']}
    source_names = ('video_server', 'ps_vision_runtime', 'm207_ps_vision_runtime',
                    'm206_ps_vision_runtime', 'm222_vectorized_w4_runtime',
                    'm258_vectorized_w4_runtime', 'm259_variable_vision_runtime',
                    'm260_cached_w4_runtime', 'm261_budgeted_w4_runtime',
                    'm273_latest_vision_runtime', 'm276_video_runtime')
    sources = []
    source_text = {}
    by_path = {r['path']: r for r in audit['verified_source_files']}
    selected_paths = [audit['module_resolution'][n] for n in source_names]
    selected_paths += audit['dynamic_model_sources']
    for path in selected_paths:
        row = by_path[path]
        p = ROOT / row['local_source']
        assert id_map[path]['sha256'] == row['sha256'] == sha(p)
        assert id_map[path]['bytes'] == row['bytes'] == p.stat().st_size
        source_text[path] = p.read_text(encoding='utf-8-sig')
        sources.append(dict(identity(p), installed_path=path))

    log_path = ROOT / 'tmp/m403/component_uart.log'
    log = log_path.read_text(encoding='utf-8-sig')
    requests = {}
    warm_layers = []
    current = None
    for line in log.splitlines():
        begin = re.fullmatch(r'M403_REQUEST_BEGIN sample=(\d+) variant=([AB])', line.strip())
        if begin:
            assert current is None
            current = int(begin[1])
            assert current not in requests
            requests[current] = dict(variant=begin[2], layers=[], vision_log_ms=None)
        layer = re.search(r'VISION_LAYER_PASS index=(\d+) layer_ms=([\d.]+)', line)
        if layer:
            item = dict(index=int(layer[1]), ms=float(layer[2]))
            (warm_layers if current is None else requests[current]['layers']).append(item)
        vision = re.search(r'VISION_PASS source_frames=(\d+) views=(\d+) frame_size=(\d+) total_ms=([\d.]+)', line)
        if vision and current is not None:
            assert list(map(int, vision.groups()[:3])) == [1, 2, 224]
            assert requests[current]['vision_log_ms'] is None
            requests[current]['vision_log_ms'] = float(vision[4])
        end = re.search(r'M403_REQUEST_COMPLETE sample=(\d+) variant=([AB]) total_ms=([\d.]+)', line)
        if end:
            assert current == int(end[1]) and requests[current]['variant'] == end[2]
            requests[current]['total_log_ms'] = float(end[3])
            current = None
    assert current is None and sorted(requests) == list(range(1, 9))
    assert [x['index'] for x in warm_layers] == list(range(24))
    rows = []
    counter_names = ('decode_calls', 'decode_ms', 'decoded_elements', 'cache_hits',
                     'cache_misses', 'cache_reconstruct_ms', 'uncached_decode_calls')
    for sample in raw['samples']:
        i = sample['index']
        observed = requests[i]
        assert observed['variant'] == sample['variant']
        assert [x['index'] for x in observed['layers']] == list(range(24))
        before, after = sample['before_cache'], sample['after_cache']
        delta = {k: after[k] - before[k] for k in counter_names}
        assert all(v >= 0 for v in delta.values())
        assert delta['decode_calls'] == 98 and delta['decoded_elements'] == 329252864
        assert delta['cache_hits'] == 26 and delta['cache_misses'] == 0
        assert delta['uncached_decode_calls'] == 72
        assert before['cache_entries'] == after['cache_entries'] == 26
        assert before['cache_bytes'] == after['cache_bytes'] == 66699264
        total = sample['timing']['total_ms']
        vision = sample['timing']['stages_ms']['vision']
        assert abs(total - observed['total_log_ms']) < 0.0011
        assert 0 <= vision - observed['vision_log_ms'] < 10
        layers = sum(x['ms'] for x in observed['layers'])
        assert layers < observed['vision_log_ms'] <= vision
        assert 0 < delta['cache_reconstruct_ms'] <= delta['decode_ms'] < vision
        rows.append(dict(index=i, variant=sample['variant'], total_ms=total, vision_ms=vision,
                         layer_sum_ms=layers, outside_layer_timer_ms=vision - layers,
                         decode_total_ms=delta['decode_ms'],
                         cached_restore_ms=delta['cache_reconstruct_ms'],
                         uncached_decode_ms=delta['decode_ms'] - delta['cache_reconstruct_ms'],
                         non_decode_ms=vision - delta['decode_ms'],
                         counter_delta=delta, layers=observed['layers']))
    summary = {k: dict(mean=statistics.mean(r[k] for r in rows),
                      minimum=min(r[k] for r in rows), maximum=max(r[k] for r in rows))
               for k in ('total_ms', 'vision_ms', 'layer_sum_ms', 'outside_layer_timer_ms',
                         'decode_total_ms', 'cached_restore_ms', 'uncached_decode_ms', 'non_decode_ms')}
    summary['decode_fraction_of_vision'] = summary['decode_total_ms']['mean'] / summary['vision_ms']['mean']
    summary['vision_fraction_of_each_request'] = [r['vision_ms'] / r['total_ms'] for r in rows]
    layer_summary = [dict(index=j, mean_ms=statistics.mean(r['layers'][j]['ms'] for r in rows),
                          minimum_ms=min(r['layers'][j]['ms'] for r in rows),
                          maximum_ms=max(r['layers'][j]['ms'] for r in rows)) for j in range(24)]
    layout_path = ROOT / 'deployment/mage_vl4b/m181_m120_video_board_candidate/vision_layout/SIXPORT_LAYOUT_MANIFEST.json'
    layout = json.loads(layout_path.read_text(encoding='utf-8'))
    actual_layout_digests = [e['returned_sha256'] for e in raw['io_events']
                             if e['first_path'].endswith('/vision_layout/SIXPORT_LAYOUT_MANIFEST.json')]
    assert actual_layout_digests and all(v == sha(layout_path) for v in actual_layout_digests)
    modules = layout['modules']
    assert len(modules) == 98
    shapes = {m['module'].removeprefix('model.visual.'): m['shape'] for m in modules}
    expected_shapes = {'self_attn.qkv': [3072, 1024], 'self_attn.proj': [1024, 1024],
                       'mlp.fc1': [4096, 1024], 'mlp.fc2': [1024, 4096]}
    for j in range(24):
        for n, shape in expected_shapes.items():
            assert shapes[f'encoder.layers.{j}.{n}'] == shape
    assert sum(m['shape'][0] * m['shape'][1] for m in modules) == 329252864
    macs = {name: 392 * shape[0] * shape[1] for name, shape in expected_shapes.items()}
    dense = sum(macs.values())
    attn = 2 * 2 * 196 * 196 * 1024
    theoretical = dict(tokens=392, views=2, per_view_tokens=196, hidden=1024, intermediate=4096,
                       linear_MACs_per_layer=macs, attention_QK_and_AV_MACs_per_layer=attn,
                       linear_MAC_fraction_of_these_matmuls=dense / (dense + attn),
                       layer_count=24, full_decoded_FP32_bytes_per_request=329252864 * 4,
                       excludes_merger_embeddings_norm_softmax_GELU_and_conversion=True,
                       estimate_not_wall_time=True)
    old = [ROOT / 'deployment/mage_vl4b/M222_ARM64_DECODER_BOARD_RESULT_02.json',
           ROOT / 'deployment/mage_vl4b/M261_CACHE_BUDGET_OFFLINE_RESULT.json',
           ROOT / 'deployment/mage_vl4b/m277_m276_fixed_window_board_candidate/M261_CACHE_POLICY.json']
    old_ids = [identity(p) for p in old]
    for p in old:
        json.loads(p.read_text(encoding='utf-8-sig'))
    opportunities = Path('C:/Users/30429/Downloads/KV260_后续优化机遇.md')
    opportunities_text = opportunities.read_text(encoding='utf-8-sig')
    assert '视觉' in opportunities_text
    result = dict(status='PASS_OFFLINE_VISION_EXISTING_EVIDENCE_AUDIT', evidence_level='L0-analysis-of-existing-board-records',
                  build_id=raw['build_id'], recovery=recovery, prior_evidence=prior,
                  source_identities=sources, source_identity_manifest=identity(id_path),
                  source_audit=identity(audit_path), current_input_layout=identity(layout_path),
                  opportunities=dict(path=str(opportunities), sha256=sha(opportunities)),
                  log_identity=identity(log_path), raw_identity=identity(raw_path),
                  samples=rows, summary=summary, layer_summary=layer_summary,
                  arithmetic_estimate=theoretical, existing_optimizations=old_ids,
                  script_sha256=sha(HERE / 'm405_vision_audit.py'),
                  new_board_run=False, overlay_loaded=False, model_forward_calls=0, fpga_transactions=0,
                  compute_changed=False, performance_pass=False, formal_promotion_allowed=False,
                  M403_original_verdict_unchanged=True, hardware_40_81_percent_result_unchanged=True,
                  M404_followup='Shelved by user redirect; sensor catalogue remains local only',
                  missing_metrics=['per-Linear FP32 GEMM time', 'operand dtype conversion time',
                                   'Attention versus norm/GELU/residual time', 'effective Torch/BLAS thread settings',
                                   'per-module uncached decode time'],
                  next_step='One bounded PS-only visual-forward observation of decode, conversion, Linear and other layer work; no language forward, Overlay, new DMA, cache-size scan or precision/input change')
    report = render_report(result)
    report_path = OUT / 'REPORT.md'
    atomic(report_path, report.encode('utf-8'), immutable=True)
    result['report'] = identity(report_path)
    out = OUT / 'RESULT.json'
    atomic(out, encoded(result), immutable=True)
    digest = sha(out)
    note = ('## M405 转向视觉阶段：已有证据拆分（2026-10-05）\n\n'
            f'SHA {digest}；Build0x4D333537，原M403八次与216条完整逐层记录复用，13份冻结视觉/调用源码同SHA。'
            f'视觉均值{summary["vision_ms"]["mean"]/1000:.6f}s，权重解码/还原{summary["decode_total_ms"]["mean"]/1000:.6f}s'
            f'（{summary["decode_fraction_of_vision"]*100:.2f}%，含缓存还原，不能相加重复），剩余{summary["non_decode_ms"]["mean"]/1000:.6f}s不是纯GEMM。'
            '现视觉为PS CPU FP32 Linear/原BF16边界，最后帧两224视图/392patch/98视觉token；已有M222解码、M261缓存、M258精度与M273输入方案保持。'
            '用户转向视觉，M404暖请求/温度目录后续搁置，温度目录仅本地未上传。'
            '本步0新上板/Overlay/模型/FPGA，原40.81%与M403裁决保持。'
            '下一步仅准备一次PS视觉窄观察，分开decode/转换/Linear及层内其余工作，再选择一处改动；无新提速或生产晋级。')
    sync('latest_m405_vision_evidence_audit', dict(status=result['status'], result=out.relative_to(ROOT).as_posix(),
         sha256=digest, build_id=raw['build_id'], new_board_run=False, performance_pass=False,
         report=report_path.relative_to(ROOT).as_posix()), note)
    print(json.dumps(dict(status=result['status'], sha256=digest, summary=summary,
                          report=str(report_path)), ensure_ascii=False, indent=2))


def render_report(r):
    s = r['summary']
    lines = ['# 视觉阶段：现有证据拆分与下一步范围', '',
             '2026-10-05。仅离线读取已有原始结果和实际冻结源码；没有重新上板。', '',
             '当前视觉在PS CPU/Torch运行，98个W4 Linear每次先还原为FP32再执行GEMM。语言并行Build0x4D333537不直接加速这一段。'
             '输入保持最后帧的两个224视图、392个patch、98个合并视觉token；不是四帧时序理解。', '',
             '## 已有八次请求能回答什么', '',
             '| 次序 | A/B | 完整请求s | 视觉s | 权重解码/还原s | 其中缓存还原s | 24层合计s | 层计时外s |',
             '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for x in r['samples']:
        lines.append(f'| {x["index"]} | {x["variant"]} | {x["total_ms"]/1000:.3f} | {x["vision_ms"]/1000:.3f} | {x["decode_total_ms"]/1000:.3f} | {x["cached_restore_ms"]/1000:.3f} | {x["layer_sum_ms"]/1000:.3f} | {x["outside_layer_timer_ms"]/1000:.3f} |')
    lines += ['', f'视觉平均 **{s["vision_ms"]["mean"]/1000:.3f}s**，范围{s["vision_ms"]["minimum"]/1000:.3f}—{s["vision_ms"]["maximum"]/1000:.3f}s。'
              '八次均保留，不剔除首次请求；A/B的区别只在语言末层。', '',
              f'权重解码/还原平均 **{s["decode_total_ms"]["mean"]/1000:.3f}s（{s["decode_fraction_of_vision"]*100:.2f}%）**。'
              f'其中26次缓存命中还原{s["cached_restore_ms"]["mean"]/1000:.3f}s，72次未缓存解码{s["uncached_decode_ms"]["mean"]/1000:.3f}s。'
              '源码证明decode_ms已包含cache_reconstruct_ms，二者不能相加。解码包括mmap读取、解包、数组分配和FP32恢复，不是纯磁盘读取。', '',
              f'非解码部分平均 **{s["non_decode_ms"]["mean"]/1000:.3f}s**，包括dtype转换、GEMM、Attention、归一化、GELU、残差、嵌入与merger、检查及进度开销。'
              '现有记录不能把它全部归为计算，或确定某个算子独占多少。', '',
              f'24层合计平均{s["layer_sum_ms"]["mean"]/1000:.3f}s；层计时外平均{s["outside_layer_timer_ms"]["mean"]/1000:.3f}s。'
              '解码包含在层内/merger工作中，不能把这张表各列横向相加。逐层计时包含heartbeat创建/收尾、部分进度通知；层外也不是纯merger。'
              '原日志rss_mib来自ru_maxrss，是进程历史峰值，不能解释为当前占用或泄漏。', '',
              '解析核对了八个BEGIN/COMPLETE、每次0—23完整层序列，以及一次计时外预热的24层，共216条。日志请求总时间与原JSON一致到打印精度；原始结果SHA和BOARD/两份状态记录一致。', '',
              '## 源码与工作量', '',
              '13份实际调用/视觉源码与M403绑定的M348身份逐文件SHA核对。加载链为M273→M261→M259→M258→M222→M207→M90。'
              'M261缓存的是uint8 codes、FP32 scales、int8 qmin，命中仍产生完整FP32权重；每请求98次还原329,252,864个元素（FP32结果累计1256MiB），这不是同时驻留的内存峰值。'
              '前两层保持BF16状态/操作数取整后FP32 GEMM，后22层FP32块；精度边界仍为原政策。', '',
              '实际layout与板端已核对SHA一致：每层qkv=[3072,1024]、proj=[1024,1024]、fc1=[4096,1024]、fc2=[1024,4096]。'
              '源码非Flash路径按两视图各196个token做Attention。按形状估计，四个Linear占这组Linear+QK/AV矩阵乘MAC的'
              f'{r["arithmetic_estimate"]["linear_MAC_fraction_of_these_matmuls"]*100:.2f}%。这是运算量估计，**不是实测时间占比**；不含softmax/归一化/GELU/解码/转换等。', '',
              '## 不重新开展的旧路线', '',
              '- M222向量化W4解码已经实施；旧板端98模块逐位证明仅解码约709s→7.20s，不能当成本轮新增完整请求收益。',
              '- M261已有64MiB选定缓存和96MiB等离线扫描；本轮实际缓存固定26项/66,699,264B。旧host扫描不是KV260性能，不再盲扫容量。',
              '- M258精度政策、M273最后帧两视图224输入已选定。本轮不重新降低分辨率、减少视图或启用旧A8视觉方案。',
              '- 当前语言PS预读、双解析worker、SiLU工作缓冲关闭；不把这些语言候选混入视觉分析。', '',
              '## 下一步只回答一个问题', '',
              '**这约35.5秒里，四种Linear的GEMM占多少，dtype转换、Attention和其余层内工作各占多少？**', '',
              '准备独立默认关闭的PS视觉窄观察入口：复用同输入、同资产、M273/M261精度和缓存；不导入或加载Overlay、不分配DMA、不运行语言模型。'
              '固定一次视觉缓存预热与一次观察，预热另存，不按结果追加请求或调整样本。记录Torch/BLAS版本与实际线程设置、进程I/O及当前RSS/峰值，保持设置原值。', '',
              '用原函数调用前后小型计数器分开store.decode、M207操作数转换、F.linear；层内分Attention（扣除其内部qkv/proj）、norm、MLP（扣除fc1/fc2）和残差/其他工作。'
              '父子区间同时留inclusive/exclusive，避免重复计时；无需每个算子打印或保存历史大张量。98次Linear、24层和两merger完整身份/shape/有限性检查，计时后核对冻结视觉输出SHA。', '',
              '观察器先对实际冻结调用路径做CPU组件检查：完整调用、异常传播、父子不重复、计时外核对、hooks/类方法恢复和不保留张量。'
              'Board执行前确认COM3 shell/同终端sudo与逐载荷SHA；本次尚未实现、上传或执行这个观察入口。', '',
              '得到分项后只选一处：Linear若占主导，先核查实际CPU矩阵乘后端/供给组织；解码或转换暴露明显成本时才改其数组/缓存组织。'
              '线程数、后端、缓存、精度均不能一起改。任何候选先组件逐位与边界检查，再完整视觉特征、视频K/V/logits/判断，最后在匹配缓存条件下比较完整请求。'
              '观察时间带计数器，只用于定位，不作为优化后正常请求性能。', '',
              '## 状态和证据', '',
              '用户已将重点转为视觉，M404暖请求及温度目录后续搁置；只读环境观察原证据保留，sensor catalogue仅本地准备，未上传。'
              '原硬件完整请求约40.81%提速结论、M403末层裁剪“净收益未证明”裁决、生产准入/服务/回滚均保持。没有新增性能或晋级。', '',
              f'- M403原始结果：`{r["raw_identity"]["path"]}`，SHA `{r["raw_identity"]["sha256"]}`。',
              f'- 已有UART日志：`{r["log_identity"]["path"]}`，SHA `{r["log_identity"]["sha256"]}`。',
              '- 本目录RESULT.json保存每请求差分、完整24层统计、源码身份、原记录身份和分析限制；本REPORT与RESULT三记录同步。', '']
    return '\n'.join(lines)


if __name__ == '__main__':
    main()
