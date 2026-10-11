"""Strict M406 receipts, original-byte collection and exclusive cost table."""
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync
from m406_prepare import PKG


def transfer(folder=ROOT / 'tmp/m406', save=True):
    manifest = json.loads((PKG / 'PACKAGE_MANIFEST.json').read_bytes())
    receipts = []
    for name in ['PACKAGE_MANIFEST.json'] + [r['path'] for r in manifest['files']]:
        prefix = 'upload_' + name.replace('.', '_')
        final = folder / (prefix + '_final.log')
        text = final.read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in text or sha(PKG / name) not in text:
            raise RuntimeError('Final SHA receipt differs: ' + name)
        size = (PKG / name).stat().st_size
        count = (size + 899) // 900
        chunks = sorted(folder.glob(prefix + '_chunk_*.log'))
        if len(chunks) != count:
            raise RuntimeError('Chunk receipt count differs')
        for i, path in enumerate(chunks, 1):
            if not re.search(r'M212_CHUNK_PASS\s+' + str(i) + r'\s+' + str(count) + r'\s+' + str(min(i*900, size)) + r'\s', path.read_text(encoding='utf-8-sig')):
                raise RuntimeError('Chunk receipt sequence differs')
        receipts.append(dict(path=name, sha256=sha(PKG/name), receipt_sha256=sha(final), chunks=count))
    syntax = folder / 'syntax.log'
    if '__M406_SYNTAX_RC_0__' not in syntax.read_text(encoding='utf-8-sig'):
        raise RuntimeError('Runner syntax receipt absent')
    value = dict(status='PASS_M406_MANIFEST_FIRST_TRANSFER', manifest_sha256=sha(PKG / 'PACKAGE_MANIFEST.json'),
                 files=receipts, syntax_sha256=sha(syntax), observation_started=False)
    if save:
        out = BASE / 'runs/M406-vision-transfer-01/RESULT.json'
        atomic(out, encoded(value), immutable=True)
        digest = sha(out)
        sync('latest_m406_vision_transfer', dict(status=value['status'],sha256=digest,
             result=out.relative_to(ROOT).as_posix(), manifest_sha256=value['manifest_sha256']),
             f'## M406 PS视觉观察传输（2026-10-05）\n\nSHA {digest}；manifest-first/900B所有回执和完整SHA/root bash-n核对；尚未执行。下一步仅原PS视觉预热+观察一次，无语言/Overlay/DMA/FPGA。')
        print('M406_TRANSFER_SYNC', digest)
    return value


def decode(text):
    hashes = re.findall(r'(?m)^M406_RESULT_SHA256=([0-9a-f]{64})\s*$', text)
    chunks = re.findall(r'(?m)^M406_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$', text)
    if len(hashes) != 1 or not chunks or len(chunks) != int(chunks[0][1]):
        raise ValueError('Missing/duplicate original result')
    parts = []
    for i, (index, total, data) in enumerate(chunks):
        part = base64.b64decode(data, validate=True)
        if int(index) != i or int(total) != len(chunks) or not 0 < len(part) <= 900:
            raise ValueError('Chunk sequence/size differs')
        parts.append(part)
    raw = b''.join(parts)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != hashes[0]:
        raise ValueError('Original byte SHA differs')
    r = json.loads(raw)
    if r['manifest_sha256'] != sha(PKG / 'PACKAGE_MANIFEST.json') or r['gate_level'] != 'PS-only-fixed-input-visual-cost-observation':
        raise ValueError('Package or scope differs')
    for k in ('overlay_loaded', 'cache_policy_changed', 'thread_settings_changed', 'performance_pass', 'formal_promotion_allowed'):
        if r[k] is not False: raise ValueError('Evidence scope differs')
    for k in ('dma_allocations', 'language_forward_calls', 'fpga_transactions'):
        if type(r[k]) is not int or r[k] != 0: raise ValueError('Unexpected hardware/language work')
    if type(r['gate_return_code']) is not int or r['gate_return_code'] not in (0, 1):
        raise ValueError('Wrong original gate rc')
    done = re.findall(r'M406_DONE gate_rc=(\d+) export_rc=(\d+)', text)
    if done and done != [(str(r['gate_return_code']), '0')]:
        raise ValueError('Gate/export rc differs')
    if r['status'] == 'PASS_PS_VISUAL_COST_OBSERVATION':
        if r['gate_return_code'] or r['errors'] or r['visual_forward_calls'] != 2:
            raise ValueError('Incomplete PASS')
        for k in ('numerical_pass','component_pass','bindings_restored','visual_owner_closed','no_pynq_import'):
            if r[k] is not True: raise ValueError('Missing numerical/lifecycle proof')
        if r['visual'] != json.loads((PKG / 'EXPECTED.json').read_bytes())['visual']:
            raise ValueError('Original visual output differs')
        if len(r['component']['real_torch_fixture_cases']) != 8 or not r['component']['exception_propagated'] or not r['component']['bindings_restored']:
            raise ValueError('Actual Torch component incomplete')
        if r['backend_before'] != r['backend_after'] or r['backend_before']['settings_changed']:
            raise ValueError('Backend settings drift')
        if not r['cpu_observation']['worker_joined'] or not r['cpu_observation']['intervals']:
            raise ValueError('CPU observation incomplete')
        rows = r['costs']['rows']
        roots = [x for x in rows if x['category'] == 'vision_total']
        if len(roots) != 1 or sum(x['exclusive_ns'] for x in rows) != roots[0]['inclusive_ns'] or r['costs']['exclusive_sum_ns'] != roots[0]['inclusive_ns']:
            raise ValueError('Exclusive accounting does not explain visual wall time')
        if not 0 < roots[0]['inclusive_ns'] <= 90e9 or not 0 < r['elapsed_s_diagnostic_not_performance'] <= 600:
            raise ValueError('Observation budget exceeded')
        for x in rows:
            if not 0 <= x['exclusive_ns'] <= x['inclusive_ns'] or x['calls'] < 1:
                raise ValueError('Invalid cost counter')
        gemms = [x for x in rows if x['category'] == 'linear_gemm']
        if len(gemms) != 98 or sum(x['calls'] for x in gemms) != 98 or len({x['name'] for x in gemms}) != 98:
            raise ValueError('Linear coverage incomplete')
        if sum(x['calls'] for x in rows if x['category'] == 'encoder_layer_other') != 24:
            raise ValueError('Layer coverage incomplete')
        before, after = r['before_cache'], r['after_cache']
        for key, expected in (('decode_calls',98),('cache_hits',26),('cache_misses',0),('uncached_decode_calls',72)):
            if after[key] - before[key] != expected: raise ValueError('Original decoder coverage differs')
        if before['cache_bytes'] != after['cache_bytes'] or before['cache_bytes'] != 66699264:
            raise ValueError('Cache capacity changed')
        if not r['native_cpu_operators'] or len(r['native_cpu_operators']) > 400:
            raise ValueError('Native dispatcher report incomplete')
    elif r['status'] == 'FAIL_PS_VISUAL_COST_OBSERVATION':
        if r['gate_return_code'] != 1 or not r['errors']: raise ValueError('Failure lacks original error')
    else:
        raise ValueError('Unknown observation status')
    return digest, raw, r, len(chunks)


def report(r):
    if r['gate_return_code']:
        return '# PS视觉观察未完成\n\n原错误和返回码保留；只在本级修复，不重跑语言请求。\n\n' + json.dumps(r['errors'],ensure_ascii=False,indent=2) + '\n'
    categories = {}
    linear = {}
    for row in r['costs']['rows']:
        categories[row['category']] = categories.get(row['category'], 0) + row['exclusive_ns']
        if row['category'].startswith('linear_'):
            name = row['name']
            group = 'QKV' if name.endswith('.qkv') else '输出投影' if name.endswith('.proj') else 'MLP fc1' if name.endswith('.fc1') else 'MLP fc2' if name.endswith('.fc2') else 'Merger'
            bucket = linear.setdefault(group, {})
            bucket[row['category']] = bucket.get(row['category'], 0) + row['exclusive_ns']
    lines = ['# 固定输入PS视觉成本观察', '', '只运行原视觉缓存预热一次及观察一次；没有语言前向、Overlay、DMA或FPGA事务。'
             '计时带观察器和native profiler，不能作为正常请求提速成绩。', '',
             f'观察视觉总时间 **{r["costs"]["vision_wall_ns"]/1e9:.6f}s**；视觉输出与冻结SHA逐字节一致，绑定恢复、采样线程退出及原视觉owner关闭通过。', '',
             '| Linear类别 | 权重恢复s | 操作数转换s | GEMM s | 输出转换s |',
             '| --- | --- | --- | --- | --- |']
    for group, values in linear.items():
        times = [values.get(k, 0)/1e9 for k in ('linear_weight_restore','linear_operand_conversion','linear_gemm','linear_output_conversion')]
        lines.append('| '+group+' | '+' | '.join(f'{x:.6f}' for x in times)+' |')
    lines += ['', '以下为排他分区，合计严格等于同一次视觉墙钟时间；Attention已扣除QKV/proj、转换及其计时的子算子。', '',
              '| 排他成本 | 秒 |', '| --- | --- |']
    for k, v in categories.items(): lines.append(f'| {k} | {v/1e9:.6f} |')
    windows = r['costs']['gemm_windows']
    wall = sum(x['end_ns']-x['start_ns'] for x in windows)
    cpu = sum(x['process_cpu_ns'] for x in windows)
    lines += ['', f'GEMM窗口累计进程CPU时间/墙钟={cpu/wall:.3f}；这是本进程含采样线程的平均CPU使用规模，不能单凭线程设置断言四核满载。'
              '逐核100ms窗口记录为系统范围利用率，需要结合本进程持久线程CPU增量及GEMM窗口；它不能排除其他进程影响。', '',
              '实际Torch/并行设置：', '', '```json',json.dumps(r['backend_before'],ensure_ascii=False,indent=2),'```', '',
              f'视觉Attention实现：{r["attention_implementations"]}。若SDPA融合路径没有经过Python matmul/softmax，相关时间留在attention_other；'
              'native CPU operator报告提供实际aten分派及CPU时间，但其时间不能直接加到墙钟表。', '',
              '98个Linear/24层完整覆盖，26项cache命中和72次未缓存解码保持。成本表是本次输入定位；下一步从实际最大成本选一处候选，保持输入、精度政策与当前语言核。', '']
    return '\n'.join(lines)


def collect(path, out=None, sync_function=sync):
    digest, raw, r, chunks = decode(Path(path).read_text(encoding='utf-8-sig'))
    out = out or BASE / 'runs/M406-vision-cost-board-01/BOARD_RESULT.json'
    atomic(out, raw, immutable=True)
    atomic(out.with_name('REPORT.md'), report(r).encode('utf-8'), immutable=True)
    sync_function('latest_m406_vision_cost_board',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=digest,
        numerical_pass=r['numerical_pass'],performance_pass=False,manifest_sha256=r['manifest_sha256']),
        f'## M406 PS视觉成本观察结果（2026-10-05）\n\n原SHA {digest}，{chunks}个≤900B严格回收；{r["status"]}，原rc{r["gate_return_code"]}。'
        '仅PS原固定输入视觉预热/观察，无语言/Overlay/DMA/FPGA；计时带观察开销，不能作为新提速。原M403裁决/硬件40.81%保持。下一步离线解释本次排他成本和CPU执行方式，只选一处候选。')
    print('M406_SAVED_RAW_SYNC',digest,r['status'])
    return r


if __name__ == '__main__':
    if sys.argv[1:] == ['transfer']: transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect': collect(ROOT / sys.argv[2])
    else: raise SystemExit('transfer | collect log')
