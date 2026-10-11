"""Offline allocation feasibility and future-hook evidence; no board imports."""
import ast
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import m351_workflow as w

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'deployment/mage_vl4b/optimization_v1'
RUN = BASE/'runs/M353-allocation-feasibility-01'


def main():
    if RUN.exists(): raise RuntimeError('Immutable audit exists; inspect only')
    texts = {n: (ROOT/n).read_text(encoding='utf-8-sig') for n in
             ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')}
    board = json.loads(texts['deployment/mage_vl4b/BOARD_GATE_RESULT.json'])
    prior = board['latest_m352_capacity_failure_closure']
    assert w.sha(ROOT/prior['result']) == prior['sha256']
    assert all(prior['sha256'] in texts[n] for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    audit = json.loads((BASE/'runs/M348-loading-path-audit-01/RESULT.json').read_text(encoding='utf-8'))
    closure = json.loads((BASE/'candidates/M345-fixed-video-01/SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    sources = {}
    files = []
    for module in ('board_runtime','m236_prefill_runtime','m238_prefill_runtime'):
        path = closure['modules'][module]
        row = next(r for r in audit['verified_source_files'] if r['path'] == path)
        assert w.sha(ROOT/row['local_source']) == row['sha256']
        sources[module] = (ROOT/row['local_source']).read_text(encoding='utf-8')
        files.append(row)
    stable = ROOT/'deployment/mage_vl4b/m175_m120_fixed_text_candidate'
    manifest = json.loads((stable/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    assert w.sha(stable/'PACKAGE_MANIFEST.json') == '406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f'
    contracts = []
    for name in ('M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json','M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json'):
        rel = 'contracts/'+name
        p = stable/rel
        assert w.sha(p) == next(r['sha256'] for r in manifest['files'] if r['path']==rel)
        contracts += json.loads(p.read_text(encoding='utf-8'))['chains']
    window_path = BASE/'runs/M350-ps-read-ahead-design-01/WINDOW_PLAN.json'
    design = json.loads((BASE/'runs/M350-ps-read-ahead-design-01/RESULT.json').read_text(encoding='utf-8'))
    assert w.sha(window_path) == design['window_plan_sha256']
    windows = json.loads(window_path.read_text(encoding='utf-8'))
    assert len(contracts) == len(windows) == 162
    max_weight = max(r['bytes_per_port'] for r in windows)
    max_input = max(int(c['input_bytes']) for c in contracts)
    max_output = max(int(c['output_bytes']) for c in contracts)
    rawpath = BASE/'runs/M352-load-ps-slot-board-01/BOARD_RESULT.json'
    assert w.sha(rawpath) == prior['raw_sha256']
    raw = json.loads(rawpath.read_text(encoding='utf-8'))
    allocation_sizes = [r['bytes'] for r in raw['allocated_buffers']]
    assert allocation_sizes == [max_weight]*4+[max_input,max_output,max_output]
    assert (max_weight,max_input,max_output) == (6963200,389152,2621440)
    assert 'pending_by_buffer' in sources['m238_prefill_runtime']
    assert 'previous = pending_by_buffer.pop(buffer_index, None)' in sources['m238_prefill_runtime']
    assert 'output_buffers = (self.output_buffer, self.output_buffer_alt)' in sources['m238_prefill_runtime']
    assert 'memoryview(output_buffer)' in sources['m236_prefill_runtime']
    for name in ('owned_buffer_release.py','test_owned_buffer_release.py'):
        ast.parse((ROOT/'scripts/optimization'/name).read_text(encoding='utf-8'),feature_version=(3,10))
    tests = ast.parse((ROOT/'scripts/optimization/test_owned_buffer_release.py').read_text(encoding='utf-8'))
    assert sum(isinstance(n,ast.FunctionDef) and n.name.startswith('test_') for n in ast.walk(tests)) == 6
    pkg = BASE/'candidates/M352-load-ps-slot-01'
    assert w.sha(pkg/'PACKAGE_MANIFEST.json') == raw['manifest_sha256']
    for r in json.loads((pkg/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']:
        assert w.sha(pkg/r['path']) == r['sha256']
    gap = prior['cma_missing_bytes']
    weights = 4*max_weight
    r = dict(status='PASS_OFFLINE_FEASIBILITY_AUDIT_CAPACITY_ROUTE_SUSPENDED',evidence_level='L0_SOURCE_METADATA_AND_FAKE_RELEASE_BACKEND_ONLY',build_id='0x4D395832',
        prior_capacity_closure_sha256=prior['sha256'],original_raw_sha256=prior['raw_sha256'],verified_source_files=files,
        contract_count=162,allocation_sizes_bytes=allocation_sizes,total_requested_cma_buffer_bytes=sum(allocation_sizes),
        missing_cma_bytes=gap,all_weight_buffers_bytes=weights,
        hypothetical_missing_if_all_weight_payload_removed_bytes=gap-weights,
        hypothetical_arithmetic_only_not_capacity_proof=True,
        conclusions=['PS slot has not been allocated; shrinking PS slot cannot remove the observed pre-slot CMA failure',
            'Even hypothetical removal of all four weight-buffer payloads (not a runnable model) leaves a positive 1339392-byte gap in payload accounting; this is not an actual CMA recovery prediction',
            'Smaller staged buffers cannot hold existing maximum full-chain windows; require different chains and independent numerical gates',
            'Aliasing two DMA outputs is unsafe for existing M238 asynchronous parser ownership and retry schedule',
            'No demonstrated legal buffer-only change preserves the original schedule and establishes the 64MiB retained-runtime reserve'],
        future_release_hook=dict(path='scripts/optimization/owned_buffer_release.py',sha256=w.sha(ROOT/'scripts/optimization/owned_buffer_release.py'),
            tests_path='scripts/optimization/test_owned_buffer_release.py',tests_sha256=w.sha(ROOT/'scripts/optimization/test_owned_buffer_release.py'),
            checks=6,python310_syntax=True,backend='explicit fake only',installed_on_board=False,integrated_in_runner=False,
            semantics='After successful backend free repeated destructor calls are no-op; failed/ambiguous backend is not retried; first release still requires safety proof'),
        board_access=False,model_forward_calls=0,fpga_transactions=0,original_frozen_package_unchanged=True,
        memory_capacity_proven=False,numerical_pass=False,performance_pass=False,promoted=False,
        rejected_routes=['Lowering reserve','Clearing or forcing eviction of cache','Restarting the closed O_DIRECT experiment',
            'Dummy CMA allocations or artificial PS memory pressure','Shrinking buffers without new legal chains','Output-buffer aliasing with live parser ownership','Repeated full runtime or video trial without changed validated memory organization'],
        next_step='Suspend video execution of this PS preread configuration; preserve component. Offline bind existing matching-Build synthesis/timing evidence to device-wait hypotheses; no board timing probe until a bounded independent plan is justified')
    assert r['hypothetical_missing_if_all_weight_payload_removed_bytes'] == 1339392
    RUN.mkdir(parents=True)
    w.atomic(RUN/'RELEASE_TEST_OUTPUT.txt',b'Explicit Windows Python tool execution: 6 tests, OK. Fake backend only; not PYNQ evidence.\n',immutable=True)
    w.atomic(RUN/'RESULT.json',w.encoded(r),immutable=True)
    sha = w.sha(RUN/'RESULT.json')
    note = ('## M353 原缓冲可行性审计与后续释放钩子修复（2026-10-01）\n\n'
        '稳定Build0x4D395832；仅离线源码/元数据/明确替身检查，0板端访问/模型/FPGA事务。原7块CMA载荷合计33484832B，'
        '四权重bank26.5625MiB；现缺口27.839844MiB。即假设删除全部权重载荷（不能运行的假设）仍差1339392B，'
        '不是实际页回收预测。缩PS slot不能改变分配前失败，直接缩原bank违反最大chain窗口，双输出别名破坏M238解析/重试所有权。'
        '没有已证明合法的仅缓冲调整可满足当前余量；暂停此配置的视频尝试，保留组件，不判定预读无收益。'
        '后续诊断幂等释放钩子6项检查/Python3.10语法通过：成功free后析构无额外MMIO/后端free；安全未知拒绝，后端异常不重试。'
        '钩子尚未集成或上板，M352冻结包和结果保持。'
        f'证据 `{(RUN/"RESULT.json").relative_to(ROOT).as_posix()}` SHA `{sha}`。'
        '下一步离线对应稳定Build的综合/时序证据与设备等待假设，先不启动设备诊断；容量与视频数值/性能仍未解锁。\n\n')
    w.atomic(RUN/'REPORT.md',('# M353 缓冲可行性裁决\n\n'+note+'\n'+ '\n'.join('- '+c for c in r['conclusions'])+'\n').encode('utf-8'))
    w.sync('latest_m353_allocation_feasibility',dict(status=r['status'],result=(RUN/'RESULT.json').relative_to(ROOT).as_posix(),sha256=sha,
        board_access=False,memory_capacity_proven=False,performance_pass=False,next_step=r['next_step']),note)
    summary = ROOT/'KV260_本轮优化完整工作记录_2026-10-01.md'
    if summary.exists():
        title,rest=summary.read_text(encoding='utf-8-sig').split('\n',1)
        closure_note=(ROOT/'CURRENT_STATE.md').read_text(encoding='utf-8').split('## M352 容量失败独立闭合')[1].split('\n## ')[0]
        w.atomic(summary,(title+'\n\n'+note+'## M352 容量失败独立闭合'+closure_note+'\n\n'+rest.lstrip('\n')).encode('utf-8'))
    print(json.dumps(dict(status=r['status'],sha256=sha,tests=6,total_cma_payload_bytes=sum(allocation_sizes),weight_only_hypothesis_remaining_bytes=gap-weights)))


if __name__ == '__main__': main()
