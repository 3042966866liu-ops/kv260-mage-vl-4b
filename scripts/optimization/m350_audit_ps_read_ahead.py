"""Freeze a design audit only: no model imports, asset data reads or board calls."""
import ast
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'
RUN = BASE / 'runs/M350-ps-read-ahead-design-01'
DESIGN = BASE / 'M350_PS_READ_AHEAD_DESIGN.md'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def encoded(value): return (json.dumps(value, ensure_ascii=True, indent=2) + '\n').encode('utf-8')
def atomic(path, raw):
    temp = path.with_name(path.name + '.tmp')
    temp.write_bytes(raw)
    os.replace(temp, path)
def calls(node, name):
    return [n for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == name]
def method(tree, cls, name):
    return next(n for c in tree.body if isinstance(c, ast.ClassDef) and c.name == cls for n in c.body if isinstance(n, ast.FunctionDef) and n.name == name)

def main():
    if RUN.exists(): raise RuntimeError('Immutable design result exists; inspect only')
    recovery = {}
    texts = {}
    for name in ('CURRENT_STATE.md', 'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md', 'docsMILESTONES.md', 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        p = ROOT / name
        texts[name] = p.read_text(encoding='utf-8-sig')
        recovery[name] = dict(sha256=sha(p), bytes=p.stat().st_size, lines=len(texts[name].splitlines()))
    b = json.loads(texts['deployment/mage_vl4b/BOARD_GATE_RESULT.json'])
    prior = b['latest_m349_route_closure']
    assert prior['route_closed'] and sha(ROOT / prior['result']) == prior['sha256']
    assert all(prior['sha256'] in texts[n] for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
    audit_path = BASE / 'runs/M348-loading-path-audit-01/RESULT.json'
    assert sha(audit_path) == b['latest_m348_loading_path_audit']['sha256']
    audit = json.loads(audit_path.read_text(encoding='utf-8'))
    frozen = {row['path']: row for row in audit['verified_source_files']}
    modules = ('board_runtime', 'm238_prefill_runtime', 'm236_prefill_runtime', 'm230_prefill_runtime', 'm241_video_language_runtime')
    closure = json.loads((BASE / 'candidates/M345-fixed-video-01/SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    verified = []
    trees, sources = {}, {}
    for name in modules:
        rel = closure['modules'][name]
        row = frozen[rel]
        assert sha(ROOT / row['local_source']) == row['sha256']
        sources[name] = (ROOT / row['local_source']).read_text(encoding='utf-8')
        trees[name] = ast.parse(sources[name])
        verified.append(row)
    original = next(n for n in trees['board_runtime'].body if isinstance(n, ast.FunctionDef) and n.name == 'chain_window')
    namespace = {'VerifiedLayout': SimpleNamespace}
    exec(ast.get_source_segment(sources['board_runtime'], original), namespace)
    window = namespace['chain_window']
    stable = ROOT / 'deployment/mage_vl4b/m175_m120_fixed_text_candidate'
    manifest = json.loads((stable / 'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    assert sha(stable / 'PACKAGE_MANIFEST.json') == '406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f'
    members = {row['path']: row for row in manifest['files']}
    records = []
    contracts = []
    for kind, filename, layout_dir in (
        ('language', 'M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json', 'language_fourport'),
        ('head', 'M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json', 'lmhead_fourport')):
        rel = 'contracts/' + filename
        p = stable / rel
        assert sha(p) == members[rel]['sha256']
        contract = json.loads(p.read_text(encoding='utf-8'))
        lp = ROOT / 'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/external_assets/weights' / layout_dir / 'SIXPORT_LAYOUT_MANIFEST.json'
        assert sha(lp) == contract['source_manifest_sha256']
        layout = SimpleNamespace(manifest=json.loads(lp.read_text(encoding='utf-8')))
        assert len(layout.manifest['files']) == 4
        contracts.extend([dict(path=p.relative_to(ROOT).as_posix(), sha256=sha(p)), dict(path=lp.relative_to(ROOT).as_posix(), sha256=sha(lp))])
        for chain in contract['chains']:
            words, size = window(layout, chain)
            assert words >= 0 and size > 0 and size % 16 == 0
            assert all(words * 16 + size <= row['bytes'] for row in layout.manifest['files'])
            records.append(dict(kind=kind, chain_index=chain['chain_index'], layer=chain.get('layer'), family=chain.get('family', 'lm_head'),
                base_words=words, bytes_per_port=size, payload_bytes=4 * size,
                chain_sha256=hashlib.sha256(json.dumps(chain, sort_keys=True, separators=(',', ':')).encode()).hexdigest()))
    family_order = [(layer, family) for layer in range(36) for family in
        (('q', 'kv', 'attention_out', 'gate_up', 'mlp_down') if layer < 10 else ('qkv', 'attention_out', 'gate_up', 'mlp_down'))]
    assert [(r['layer'], r['family']) for r in records if r['kind'] == 'language'] == family_order
    assert len(records) == 162 and len(family_order) == 154
    maximum = max(r['bytes_per_port'] for r in records)
    total = sum(r['payload_bytes'] for r in records)
    assert maximum == 6963200 and total == 2034890752
    fn = method(trees['m238_prefill_runtime'], 'M238PrefillRuntime', 'language_family_many')
    stage = calls(fn, '_stage'); launch = calls(fn, '_launch_prepacked'); resolve = calls(fn, '_resolve_pending')
    assert len(stage) == 1 and len(launch) == 1 and len(resolve) == 2
    assert stage[0].lineno < launch[0].lineno < max(n.lineno for n in resolve)
    assert any(isinstance(n, ast.For) and n.lineno > launch[0].lineno and calls(n, '_resolve_pending') for n in ast.walk(fn))
    retry = method(trees['m236_prefill_runtime'], 'M236PrefillRuntime', '_resolve_pending')
    assert not calls(retry, '_stage') and calls(retry, '_launch_once')
    assert any(isinstance(n, ast.Name) and n.id == 'buffers' for n in ast.walk(retry))
    copy = next(n for n in trees['board_runtime'].body if isinstance(n, ast.FunctionDef) and n.name == 'copy_window_to_buffer')
    assert len(calls(copy, 'sync_to_device')) == 1
    assert not calls(copy, 'posix_fadvise')
    stages = method(trees['board_runtime'], 'M120BoardRuntime', '_stage')
    assert not calls(stages, 'allocate')
    # SOURCE order and exact metadata checks, not tests of a yet-unwritten component.
    checks = ['prior route closure SHA and synchronized records', 'five exact frozen runtime sources',
        'stable package manifest identity', 'contract file identities', 'layout identities and shard count',
        'exact 154-family order and eight heads', 'all 162 offsets/lengths inside all shards',
        'exact total staged bytes and maximum window', 'M238 stage-before-launch and final pending drain',
        'M236 retry reuses buffers without restaging', 'original copy sync and no cache eviction',
        'original stage has no additional allocator call']
    RUN.mkdir(parents=True)
    atomic(RUN / 'WINDOW_PLAN.json', encoded(records))
    r = dict(status='PASS_OFFLINE_PS_READ_AHEAD_DESIGN_AUDIT', evidence_level='L0_SOURCE_AND_METADATA_DESIGN_ONLY',
        build_id='0x4D395832', recovery_read=recovery, prior_closure_sha256=prior['sha256'],
        verified_source_files=verified, contract_and_layout_files=contracts, source_checks=checks,
        chain_count=len(records), language_count=154, head_count=8, maximum_bytes_per_port=maximum,
        planned_ps_payload_bytes=4 * maximum, planned_extra_pynq_allocations=0,
        stage_bytes=total, window_plan_sha256=sha(RUN / 'WINDOW_PLAN.json'), design_sha256=sha(DESIGN),
        implementation_complete=False, component_tests_completed=False, board_run=False,
        rejected_attempts=['Initial development artifact layout SHA differed from frozen contract; audit stopped before evidence writes. Selected same-SHA release-staging v7 manifests, no original asset or board change', 'Initial AST check examined only function-body loops and missed final drain nested inside With. Corrected recursive AST inspection before evidence writes; runtime unchanged'],
        real_weight_data_read=False, overlay_loaded=False, fpga_transactions=0,
        memory_capacity_proven=False, numerical_pass=False, performance_pass=False, formal_promotion_allowed=False,
        next_step='Implement default-disabled PS read-ahead component and independent offline correctness/lifecycle tests only; no board/model execution')
    atomic(RUN / 'RESULT.json', encoded(r))
    digest = sha(RUN / 'RESULT.json')
    b['latest_m350_ps_read_ahead_design'] = dict(status=r['status'], result=(RUN / 'RESULT.json').relative_to(ROOT).as_posix(), sha256=digest,
        design=DESIGN.relative_to(ROOT).as_posix(), design_sha256=sha(DESIGN), evidence_level=r['evidence_level'],
        implementation_complete=False, board_run=False, performance_pass=False, next_step=r['next_step'])
    atomic(ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json', encoded(b))
    note = ('## M350 普通PS内存预读设计与原调度审计通过（2026-10-01）\n\n'
        '按用户新重点：用较低专用CMA需求覆盖权重读取等待。5份实际解析runtime源码同M348 SHA，12项源码/元数据检查通过；'
        '原154语言family+8 head、162窗口、2034890752B暂存及最大6963200B/port均核对。'
        '设计采用一个四端口普通PS slot（载荷上限27852800B/26.5625MiB），后台readinto，'
        '原family及重试完成后前景复制同步到原四CMA缓冲；规划额外PYNQ分配0。'
        '普通页/页缓存仍可能影响CMA，非零内存压力保证；原双bank90.5625MiB门槛不改，独立方案保留64MiB CMA及普通内存余量。'
        '仅L0设计审计，没有组件实现/组件测试、真实权重数据、上板/Overlay/模型或容量/数值/性能/晋级PASS。'
        f'证据 `{(RUN / "RESULT.json").relative_to(ROOT).as_posix()}` SHA `{digest}`，设计 `{DESIGN.relative_to(ROOT).as_posix()}`。'
        '下一步仅实现默认关闭组件及独立离线生命周期/字节检查。稳定Build0x4D395832、源/服务/回滚/boot/DTB/CMA保持；O_DIRECT路线已结束。\n\n')
    for name in ('CURRENT_STATE.md', 'docsMILESTONES.md'):
        title, rest = texts[name].split('\n', 1)
        atomic(ROOT / name, (title + '\n\n' + note + rest.lstrip('\n')).encode('utf-8'))
    atomic(RUN / 'REPORT.md', ('# M350 离线设计审计\n\n' + note + '源码检查：\n\n' + '\n'.join('- ' + c for c in checks) + '\n').encode('utf-8'))
    assert all(digest in (ROOT / n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
    assert json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))['latest_m350_ps_read_ahead_design']['sha256'] == digest
    print(json.dumps(dict(status=r['status'], sha256=digest, source_checks=len(checks), ps_payload_bytes=4 * maximum, board_run=False)))

if __name__ == '__main__': main()
