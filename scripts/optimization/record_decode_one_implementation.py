"""Record completed experimental implementation, never board/performance PASS."""
import json
from pathlib import Path
import shutil
from measurement import sha256, write_json, exclusive_lock

root = Path(__file__).resolve().parents[2]
base = root / 'deployment/mage_vl4b/optimization_v1'
art = base / 'candidates/OP01-decode-one-experimental-artifacts'
pkg = base / 'candidates/OP01-decode-one-minimal-board-01'
out = base / 'runs/OP01-decode-one-experimental-implementation'
if out.exists(): raise RuntimeError('Immutable evidence exists')
if sha256(art / 'ARTIFACT_MANIFEST.json') != '75fbe60f73a18d76074be9c5fd5f7c7fa836d877c4db100b47b98882b947b37c':
    raise RuntimeError('Artifact manifest drift')
if sha256(pkg / 'PACKAGE_MANIFEST.json') != '1fb069ab95552b1c8f20fc8f4129ed10544c1e3e91c5869d7c41472466346442':
    raise RuntimeError('Package manifest drift')
manifest = json.loads((art / 'ARTIFACT_MANIFEST.json').read_text())
package = json.loads((pkg / 'PACKAGE_MANIFEST.json').read_text())
for row in package['files']:
    path = pkg / row['path']
    if path.stat().st_size != row['bytes'] or sha256(path) != row['sha256']:
        raise RuntimeError('New package drift: ' + row['path'])
if list(pkg.rglob('*.pyc')) or list(pkg.rglob('__pycache__')):
    raise RuntimeError('Package bytecode pollution')
resources = {}
for line in (art / 'evidence/impl_utilization.rpt').read_text().splitlines():
    cells = [x.strip() for x in line.split('|')]
    if len(cells) == 8 and cells[1] in ('CLB LUTs', 'CLB Registers', 'Block RAM Tile', 'URAM', 'DSPs'):
        resources[cells[1]] = dict(used=int(cells[2]), available=int(cells[5]), percent=float(cells[6]))
if len(resources) != 5: raise RuntimeError('Resource table mismatch')
record = dict(status='PASS_EXPERIMENTAL_IMPLEMENTATION_ONLY', build_id='0x4F503131',
    timing=manifest['timing'], resources=resources, capacity_status='STOPPED_BY_USER_NOT_PASS',
    formal_promotion_allowed=False, board_deployed=False, performance_pass=False,
    bit_sha256=sha256(art / 'overlay/op01_decode_one.bit'), hwh_sha256=sha256(art / 'overlay/op01_decode_one.hwh'),
    artifact_manifest_sha256=sha256(art / 'ARTIFACT_MANIFEST.json'),
    minimum_package_manifest_sha256=sha256(pkg / 'PACKAGE_MANIFEST.json'),
    build_session=88401, build_exit_code=0, terminal_tool_chunk='34e00a',
    linux_import_and_shell_syntax='PASS (WSL only, not target-board preflight)',
    rejected_attempt='Restricted WSL E_ACCESSDENIED before import; approved normal-tool execution passed',
    next_action='Transfer immutable experimental package through temporary Ethernet/COM3; board environment, zero Build-ID, reference descriptor, stable restore; then chain/layer and same-KV852 paired Decode')
note = '''## Decode-one 实验 bitstream 已完成（2026-09-25 21:33）

原session88401正常退出0；候选0x4F503131生成bitstream，正式WNS +0.168ns、WHS +0.010ns，严重DRC0、路由错误0。
整壳资源LUT40244/117120、FF47228/234240、BRAM70/144、URAM16/64、DSP1070/1248。
制品与最小测试包均已收集、哈希校验；WSL导入和bash语法通过，不代表目标板预检。
证据optimization_v1/runs/OP01-decode-one-experimental-implementation/result.json；报告/源码/状态更新前备份保留。
容量专项仍STOPPED_BY_USER_NOT_PASS，实验例外不授予正式晋级；尚无新核上板、logits或性能结果。
下一步COM3控制+临时网线传包，环境预检→零事务身份→已有参考descriptor→稳定核恢复，再逐级至KV852同条件单步对照。

'''
with exclusive_lock(base / 'evidence.lock'):
    out.mkdir(parents=True)
    shutil.copytree(art, out / 'artifacts_backup')
    shutil.copytree(pkg, out / 'minimum_package_backup')
    before = out / 'state_before_update'; before.mkdir()
    board_path = root / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    for p in (root / 'CURRENT_STATE.md', root / 'docsMILESTONES.md', board_path, base / 'STATE.json'):
        shutil.copy2(p, before / p.name)
    write_json(out / 'result.json', record)
    for p in (root / 'CURRENT_STATE.md', root / 'docsMILESTONES.md'):
        old = p.read_bytes(); split = old.find(b'\n') + 1
        temp = p.with_suffix('.implementation.partial')
        temp.write_bytes(old[:split] + b'\n' + note.encode('utf-8') + old[split:]); temp.replace(p)
    board = json.loads(board_path.read_text(encoding='utf-8-sig'))
    board['latest_decode_one_implementation'] = record; write_json(board_path, board)
    state_path = base / 'STATE.json'; state = json.loads(state_path.read_text(encoding='utf-8-sig'))
    state['results']['decode_one_implementation'] = str((out / 'result.json').relative_to(root))
    state['next_action'] = record['next_action']; write_json(state_path, state)
    write_json(out / 'BACKUP_MANIFEST.json', {p.relative_to(out).as_posix(): sha256(p) for p in out.rglob('*') if p.is_file()})
print(json.dumps(record))
