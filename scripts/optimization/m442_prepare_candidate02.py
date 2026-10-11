"""Freeze the independently opted-in parser candidate; no board access."""
import ast
import gzip
import json
from pathlib import Path
import subprocess
import sys
from m441_host_io08 import atomic
from m351_workflow import sha, encoded, sync
import m442_verify_parser06 as verification

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'
PKG = BASE / 'candidates/M442-direct-output-parser-02'
RUN = BASE / 'runs/M442-direct-output-parser-preparation-02'


def main():
    if PKG.exists() or RUN.exists():
        raise RuntimeError('Existing candidate/preparation; inspect saved bytes only')
    selected_path = BASE / 'runs/M442-direct-output-parser-offline-06/RESULT.json'
    selected = json.loads(selected_path.read_bytes())
    assert sha(HERE / 'm442_output_parser06.py') == selected['candidate_sha256']
    assert selected['status'] == 'PASS_OFFLINE_DIRECT_OUTPUT_PARSER'
    closure_path = BASE / 'candidates/M441-complete-request-performance-17/SOURCE_CLOSURE.json'
    closure = json.loads(closure_path.read_bytes())
    packets = verification.actual_packets()
    PKG.mkdir(parents=True)
    RUN.mkdir(parents=True)
    names = ('m442_output_parser06.py', 'm442_runtime_adapter02.py', 'm442_verify_integration02.py',
             'm442_verify_parser06.py', 'm441_host_io08.py')
    for name in names:
        raw = (HERE / name).read_bytes()
        ast.parse(raw, feature_version=(3, 10))
        atomic(PKG / name, raw, immutable=True)
    sources = {}
    for module in ('m231_prefill_runtime', 'm236_prefill_runtime', 'm238_prefill_runtime'):
        source = ROOT / closure['modules'][module]
        expected = next(row for row in closure['files'] if row['path'] == source.relative_to(ROOT).as_posix())
        assert sha(source) == expected['sha256']
        sources[source.name] = sha(source)
        atomic(PKG / source.name, source.read_bytes(), immutable=True)
    entries = []
    for name, chain, payload, identity in packets:
        filename = name + '_actual_output.bin.gz'
        atomic(PKG / filename, gzip.compress(payload, mtime=0), immutable=True)
        entries.append(dict(name=name, chain=chain, payload=filename, identity=identity))
    plan = dict(schema='m442-independent-output-parser-v1', build_id='0x4D343431',
                default_enabled=False, candidate_sha256=selected['candidate_sha256'],
                baseline_sources=sources, source_closure_sha256=sha(closure_path),
                selected_numerical_evidence_sha256=sha(selected_path), actual_packets=entries,
                input_math_and_dma_contract_unchanged=True, parser_workers=1,
                lm_head_and_vision_parser_changed=False, full_fp32_intermediate_arrays=0,
                board_operations_allowed_now=False,
                next_level='A53 parser component before isolated candidate chain/layer/text/video/full request',
                future_performance_sampling='Fixed 4 preconditioning ABBA plus 8 formal ABBABAAB; no dropping or added samples',
                future_performance_verdict='Both balanced groups positive and paired 95% lower bound positive; natural I/O')
    atomic(PKG / 'PLAN.json', encoded(plan), immutable=True)
    result_path = RUN / 'INTEGRATION_RESULT.json'
    execution = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(HERE / 'm442_verify_integration02.py'),
                                str(PKG), str(result_path)], capture_output=True, encoding='utf-8')
    atomic(RUN / 'INTEGRATION_LOG.txt', (execution.stdout + execution.stderr).encode(), immutable=True)
    if execution.returncode:
        atomic(RUN / 'FAILURE.json', encoded(dict(status='FAIL_OFFLINE_M442_INTEGRATION',
                return_code=execution.returncode, log_sha256=sha(RUN/'INTEGRATION_LOG.txt'))), immutable=True)
        raise RuntimeError(execution.stdout + execution.stderr)
    integration = json.loads(result_path.read_bytes())
    assert integration['status'] == 'PASS_OFFLINE_M442_PARSER_AND_ACTUAL_SCHEDULER'
    rows = [dict(path=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG / 'SHA256SUMS', ''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode(), immutable=True)
    rows.append(dict(path='SHA256SUMS', bytes=(PKG/'SHA256SUMS').stat().st_size, sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG / 'PACKAGE_MANIFEST.json', encoded(dict(schema='m442-frozen-parser-candidate', files=rows,
           file_count=len(rows), total_bytes=sum(r['bytes'] for r in rows))), immutable=True)
    assert {p.name for p in PKG.iterdir()} == {r['path'] for r in rows} | {'PACKAGE_MANIFEST.json'}
    attempts = []
    for number in range(1, 7):
        path = BASE / f'runs/M442-direct-output-parser-offline-{number:02d}/RESULT.json'
        r = json.loads(path.read_bytes())
        attempts.append(dict(version=number, result=path.relative_to(ROOT).as_posix(), sha256=sha(path),
            numerical_pass=True, local_timings=[{k:v for k,v in t.items() if not isinstance(v,list)} for t in r['timings']],
            disposition='SELECTED_FOR_OFFLINE_INTEGRATION_NOT_BOARD_GAIN' if number == 6 else 'NOT_SELECTED_LOCAL_COST_OR_REGRESSION'))
    result = dict(status='PASS_OFFLINE_M442_CANDIDATE_READY_BOARD_DEFERRED_BY_USER',
        build_id='0x4D343431', evidence_scope='Offline CPU parser and scheduler fixtures only',
        candidate_sha256=selected['candidate_sha256'], integration_sha256=sha(result_path),
        manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'), file_count=len(rows), total_bytes=sum(r['bytes'] for r in rows),
        board=False, full_request_speedup_proven=False, production_changed=False,
        full_fp32_intermediate_arrays=0, actual_packet_comparisons=integration['actual_packet_comparisons'],
        all_fp16_bits_shifts=11, partial_strided_checks=integration['partial_strided_checks'],
        pipeline_cases=len(integration['pipeline_checks']), parser_workers=1,
        lm_head_and_vision_parser_changed=False, attempts=attempts,
        board_deferred_reason='User: 我现在不方便上板',
        next_step='When user resumes board testing: A53 component gate, then candidate-scoped numerical gates and fixed full-request A/B')
    atomic(RUN / 'RESULT.json', encoded(result), immutable=True)
    digest = sha(RUN/'RESULT.json')
    note = (f'## M442融合输出解析器离线候选完成（2026-10-10）\n\n'
            f'证据 `{(RUN/"RESULT.json").relative_to(ROOT).as_posix()}` SHA {digest}；'
            f'候选 {selected["candidate_sha256"]}，包 {result["manifest_sha256"]}。'
            'FP16零复制视图直接融合转换/重排/倍率恢复到最终FP32切片，0完整FP32中间数组；'
            '99真实已保存RTL包逐位比较、65536半精度位型×11倍率、81部分行/步长/哨兵检查；'
            '实际M238/M236调度方法在明确CPU硬件替身下6组159-token/尾31/重试/双输出owner复用通过，单parser不改。'
            '版本01–04本地成本/回归未选；05完整down块持平，06将完整描述符合并为单次融合调用；非A53或约95秒完整请求收益证据。'
            'Build0x4D343431/200–100MHz原证据复用，不改LM head/视觉解析、PL/稳定源/服务/回滚。'
            '用户明确暂不方便上板，0COM3/网络/板端动作；下一步等用户恢复板测后先A53组件，再本候选数值门禁与固定完整请求A/B。')
    sync('latest_m442_parser_candidate_offline', dict(status=result['status'], result=(RUN/'RESULT.json').relative_to(ROOT).as_posix(),
         sha256=digest, manifest_sha256=result['manifest_sha256'], board=False, performance_pass=False), note)
    report = '# M442输出解析候选\n\n' + note + '\n\n'
    report += '改变：融合转换、重排和缩放；保留最终FP32结果和有限值检查。NumPy内部可能使用小工作缓冲，并非零分配。\n\n'
    report += '接入：`make_candidate_runtime_class(M238PrefillRuntime)`只返回独立子类；不会替换已加载类或修改基线源码。'
    report += '当前覆盖language_family_many，LM head/视觉另一解析路径保持。禁止把本机比例套到完整请求。\n\n'
    report += '|保存真实包|原解析 ms|新解析 ms|本机耗时下降|\n|---|---:|---:|---:|\n'
    for t in integration['timings']:
        report += f'|{t["name"]}/{t["tokens"]} tokens|{t["baseline_median_ms"]:.5f}|{t["candidate_median_ms"]:.5f}|{100*(1-t["candidate_median_ms"]/t["baseline_median_ms"]):.2f}%|\n'
    report += '\n上表Windows NumPy短测20平衡对，159行数组的完整32及尾31切片；仅解析、所有样本保留，不是A53或完整请求裁决。\n'
    report += '\n历史05在159行布局下完整down块0.289→0.29185ms基本持平，未作为完整请求提速；06每个完整描述符仅一次融合ufunc。旧01–05原字节和旧候选包01保留。\n'
    atomic(RUN / 'REPORT.md', report.encode('utf-8'), immutable=True)
    print(json.dumps(dict(status=result['status'], result_sha256=digest, manifest_sha256=result['manifest_sha256'],
                         integration=integration['status'], files=len(rows), bytes=result['total_bytes'])))


if __name__ == '__main__':
    main()
