"""Derive a memory-only conclusion from immutable M346 bytes; no board access."""
import ast
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / 'deployment/mage_vl4b/optimization_v1/runs/M346-load-memory-board-01'
RAW_SHA = 'cc04ea32daba54878a4ac0f63a7cd990db36e67d745c1e696adb806fd60e086a'
NEXT = ('仅准备逐资产哈希读取的有界CMA/RSS/Cached诊断：冻结原preflight源码、文件顺序及SHA，'
        '逐文件观测并定位读取阶段的CMA下降；不加载Overlay、不forward、不清缓存。'
        '完整runtime保留时未达到90.5625MiB门槛，双bank视频数值与性能继续关闭。')


def atomic(path, data):
    part = path.with_name(path.name + '.m346-finalize-part')
    with part.open('wb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(part, path)


def main():
    raw = (RUN / 'BOARD_RESULT.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == RAW_SHA
    result = json.loads(raw)
    assert result['status'] == 'PASS_LOAD_ONLY_DIAGNOSTIC' and not result['errors']
    assert result['safe_buffers_released'] and not result['unsafe_buffers_retained']
    assert result['host_calls'] == result['logical_calls'] == result['model_forward_calls'] == 0
    rows = {x['name']: x['memory'] for x in result['stages']}
    loaded = rows['complete-runtime-loaded-retained']
    gc = rows['retained-runtime-after-PS-GC']
    trim = rows['retained-runtime-after-PS-glibc-trim']
    later = rows['retained-runtime-after-trim-plus-5s']
    before_hash = rows['after-exact-runtime-imports']
    after_hash = rows['after-release-asset-hashes']
    required = 94961664
    assert all(x['system_bytes']['CmaFree'] < required for x in (loaded, gc, trim, later))
    source = ROOT / 'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/scripts/preflight.py'
    closure = json.loads((ROOT / 'deployment/mage_vl4b/optimization_v1/candidates/M346-load-memory-01/SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    identity = next(x for x in closure['files'] if x['path'] == 'scripts/preflight.py')
    source_bytes = source.read_bytes()
    assert len(source_bytes) == identity['bytes'] and hashlib.sha256(source_bytes).hexdigest() == identity['sha256']
    tree = ast.parse(source_bytes.decode('utf-8'))
    digest = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'digest')
    source_lines = source_bytes.decode('utf-8').splitlines()
    interpretation = dict(
        status='LOAD_ONLY_COMPLETE_CMA_THRESHOLD_STILL_FAIL', raw_sha256=RAW_SHA,
        required_cma_free_bytes=required,
        gc_cma_delta_bytes=gc['system_bytes']['CmaFree']-loaded['system_bytes']['CmaFree'],
        trim_rss_released_bytes=loaded['process_bytes']['VmRSS']-trim['process_bytes']['VmRSS'],
        trim_cma_gain_bytes=trim['system_bytes']['CmaFree']-gc['system_bytes']['CmaFree'],
        retained_after_5s_cma_bytes=later['system_bytes']['CmaFree'],
        retained_after_5s_shortfall_bytes=required-later['system_bytes']['CmaFree'],
        asset_hash_phase_cma_drop_bytes=before_hash['system_bytes']['CmaFree']-after_hash['system_bytes']['CmaFree'],
        asset_hash_phase_cached_gain_bytes=after_hash['system_bytes']['Cached']-before_hash['system_bytes']['Cached'],
        causal_limit='Aggregate snapshots associate the drop with asset reads; no per-file page ownership or fragmentation cause proven.',
        source_audit=dict(path=source.relative_to(ROOT).as_posix(), sha256=identity['sha256'],
                          digest_start_line=digest.lineno, digest_end_line=digest.end_lineno,
                          digest_source='\n'.join(source_lines[digest.lineno-1:digest.end_lineno])),
        candidate_state='SUSPENDED_AT_VIDEO_CMA_FAILURE', numerical_pass=False,
        performance_pass=False, formal_promotion_allowed=False, next_step=NEXT,
        rejected_attempts=['Offline generic decode audit rejected base64 serialization; narrowed to that exact receiver before freezing, transfer and board work.'],
    )
    encoded = (json.dumps(interpretation, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    conclusion = RUN / 'INTERPRETATION.json'
    if conclusion.exists():
        assert conclusion.read_bytes() == encoded
    else:
        atomic(conclusion, encoded)
    digest_sha = hashlib.sha256(encoded).hexdigest()
    board_path = ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    board = json.loads(board_path.read_text(encoding='utf-8'))
    assert board['latest_m346_load_memory']['sha256'] == RAW_SHA
    board['latest_m346_load_memory'].update(
        memory_capacity_status=interpretation['status'],
        interpretation_path=conclusion.relative_to(ROOT).as_posix(), interpretation_sha256=digest_sha,
        candidate_state=interpretation['candidate_state'], next_step=NEXT)
    atomic(board_path, (json.dumps(board, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    note = ('## M346 内存结论：trim有效，但双bank容量条件仍失败（2026-10-01）\n\n'
        '稳定Build `0x4D395832`；仅一次原完整runtime加载，0模型forward、0逻辑/物理事务，'
        '7块原DMA缓冲安全释放。原始结果SHA `'+RAW_SHA+'`，解读SHA `'+digest_sha+'`。'
        '加载后CMA39.191406MiB，GC不变；trim释放RSS93.066406MiB，CMA仅增9.269531MiB至48.460938MiB，'
        '5秒保留对象观察48.570312MiB，仍缺41.992188MiB才达原90.5625MiB门槛。'
        '资产哈希阶段CMA降203.40625MiB、Cached增687.328125MiB；原preflight以4MiB块读取哈希，'
        '此为定位线索，尚未证明具体文件、页归属或碎片原因。关闭runtime后95.652344MiB不代表实际运行时容量。'
        '诊断PASS不等于容量、数值、性能或晋级PASS。稳定源/服务/回滚/boot/DTB/CMA配置保持。'
        '离线decode审计曾误拒base64序列化，冻结前仅修正该精确接收者；没有因此重跑硬件。'
        '证据 `'+conclusion.relative_to(ROOT).as_posix()+'`。下一步：'+NEXT+'\n\n')
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md'):
        path = ROOT/name; text = path.read_text(encoding='utf-8')
        if digest_sha not in text:
            heading, rest = text.split('\n', 1)
            atomic(path, (heading+'\n\n'+note+rest.lstrip('\n')).encode('utf-8'))
    labels = [
        ('导入后、资产哈希前', 'after-exact-runtime-imports'),
        ('资产哈希后', 'after-release-asset-hashes'),
        ('DMA缓冲分配后', 'after-original-M238-and-all-DMA-buffer-allocations'),
        ('完整runtime保留', 'complete-runtime-loaded-retained'),
        ('保留runtime + GC', 'retained-runtime-after-PS-GC'),
        ('保留runtime + trim', 'retained-runtime-after-PS-glibc-trim'),
        ('trim后5秒、runtime仍保留', 'retained-runtime-after-trim-plus-5s'),
        ('关闭runtime及安全释放后', 'after-safe-close-and-PS-object-disposal'),
    ]
    table = '| 阶段 | CMA空闲 MiB | 进程RSS MiB | 文件缓存 MiB |\n| --- | ---: | ---: | ---: |\n'
    for label, name in labels:
        m = rows[name]
        table += f"| {label} | {m['system_bytes']['CmaFree']/1048576:.3f} | {m['process_bytes']['VmRSS']/1048576:.3f} | {m['system_bytes']['Cached']/1048576:.3f} |\n"
    report = ('# M346 只加载内存诊断\n\n'
        '已完成诊断；双bank视频候选继续停在CMA失败级。GC无改善，trim确实释放空闲堆页，'
        '但保留真实runtime后仍低于90.5625MiB门槛。未执行模型forward或PL事务。\n\n'+table+'\n'
        '资产哈希前后，CMA下降与文件缓存增长同时出现；这提示应逐文件定位读取影响，'
        '不能据此断言具体页归属或将RSS释放量当成CMA收益。关闭runtime后的容量不能替代运行时门槛。\n\n'
        '初始与末态AP_CTRL=4、两DMA DMASR=0；没有提交过事务，安全释放依据是受拦截的事务入口与原构造函数生命周期。'
        'DMASR=0仍不能当作完成事务后的idle。0错误、0阻止的推理尝试；无kill/reset/drop_caches。\n\n'
        f'原始结果：`BOARD_RESULT.json` SHA `{RAW_SHA}`，9个≤1800B分块严格回收。'
        f'解读：`INTERPRETATION.json` SHA `{digest_sha}`，三份状态记录已同步。\n\n'
        '下一步：'+NEXT+'\n')
    atomic(RUN/'REPORT.md', report.encode('utf-8'))
    assert hashlib.sha256((RUN/'BOARD_RESULT.json').read_bytes()).hexdigest() == RAW_SHA
    assert all(digest_sha in (ROOT/name).read_text(encoding='utf-8') for name in ('CURRENT_STATE.md','docsMILESTONES.md'))
    assert json.loads(board_path.read_text(encoding='utf-8'))['latest_m346_load_memory']['interpretation_sha256'] == digest_sha
    print(json.dumps(dict(synchronization_status='M346_MEMORY_INTERPRETATION_THREE_RECORDS_SYNCHRONIZED', **interpretation), ensure_ascii=False))


if __name__ == '__main__': main()
