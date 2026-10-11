"""Archive completed synthesis only; do not turn it into route/board PASS."""
import json
import shutil
from pathlib import Path
from measurement import sha256, write_json, exclusive_lock

root = Path(__file__).resolve().parents[2]
base = root / 'deployment/mage_vl4b/optimization_v1'
project = root / 'tmp/op01_d1_exp'
runs = project / 'op01_d1_exp.runs'
child = runs / 'qwen25_mixed_gs_op01_decode_one_0_0_synth_1'
top = runs / 'synth_1'
out = base / 'runs/OP01-decode-one-shell-synthesis'
if out.exists():
    raise RuntimeError('Immutable synthesis evidence already exists')
for run in (child, top):
    log = (run / 'runme.log').read_text(errors='replace')
    if 'synth_design completed successfully' not in log or 'Exiting Vivado' not in log:
        raise RuntimeError('Synthesis not complete: ' + str(run))
    if len(list(run.glob('*.dcp'))) != 1:
        raise RuntimeError('Missing/ambiguous synthesized checkpoint')
report = child / 'qwen25_mixed_gs_op01_decode_one_0_0_utilization_synth.rpt'
resources = {}
for line in report.read_text().splitlines():
    cells = [x.strip() for x in line.split('|')]
    if len(cells) == 8 and cells[1] in ('CLB LUTs*', 'CLB Registers', 'Block RAM Tile', 'URAM', 'DSPs'):
        resources[cells[1]] = {'used': int(cells[2]), 'available': int(cells[5]), 'percent': float(cells[6])}
if set(resources) != {'CLB LUTs*', 'CLB Registers', 'Block RAM Tile', 'URAM', 'DSPs'}:
    raise RuntimeError('Resource report schema mismatch')
record = dict(status='SYNTHESIS_COMPLETE_ROUTE_PENDING', build_id='0x4F503131',
              scope='kernel OOC resources; top includes unresolved OOC cells until implementation',
              resources=resources, capacity_pass=False, board_deployed=False,
              performance_pass=False, formal_promotion_allowed=False,
              live_controller_session=88401,
              next_action='Continue existing implementation; require routed timing/DRC before bitstream and minimum board smoke')
note = '''## Decode-one 新核及整壳综合完成（2026-09-25 21:03）

新核及top综合均生成DCP，原session88401接续impl_1；opt_design完成，布局布线和bitstream尚待。
新核OOC资源：LUT 36298/117120、FF 36665/234240、BRAM tile66/144、URAM16/64、DSP1070/1248。
上述不是整壳最终资源；top综合的0资源是OOC层级未展开，不能当作最终资源或核被删除的证据。
证据optimization_v1/runs/OP01-decode-one-shell-synthesis/result.json，原报告/DCP及更新前状态已备份。
容量专项仍STOPPED_BY_USER_NOT_PASS，未上板、未测收益。下一步原构建完成route/时序DRC后生成bitstream。

'''
with exclusive_lock(base / 'evidence.lock'):
    out.mkdir(parents=True)
    for label, run in (('kernel', child), ('top', top)):
        dest = out / label
        dest.mkdir()
        for source in [run / 'runme.log', *run.glob('*.dcp'), *run.glob('*utilization_synth.rpt')]:
            shutil.copy2(source, dest / source.name)
    before = out / 'state_before_update'
    before.mkdir()
    board_path = root / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    for source in (root / 'CURRENT_STATE.md', root / 'docsMILESTONES.md', board_path, base / 'STATE.json'):
        shutil.copy2(source, before / source.name)
    write_json(out / 'result.json', record)
    for path in (root / 'CURRENT_STATE.md', root / 'docsMILESTONES.md'):
        old = path.read_bytes()
        split = old.find(b'\n') + 1
        temporary = path.with_suffix('.synthesis.partial')
        temporary.write_bytes(old[:split] + b'\n' + note.encode('utf-8') + old[split:])
        temporary.replace(path)
    board = json.loads(board_path.read_text(encoding='utf-8-sig'))
    board['latest_decode_one_shell_synthesis'] = record
    write_json(board_path, board)
    state_path = base / 'STATE.json'
    state = json.loads(state_path.read_text(encoding='utf-8-sig'))
    state['results']['decode_one_shell_synthesis'] = str((out / 'result.json').relative_to(root))
    state['next_action'] = record['next_action']
    write_json(state_path, state)
    write_json(out / 'BACKUP_MANIFEST.json', {p.relative_to(out).as_posix(): sha256(p) for p in out.rglob('*') if p.is_file()})
print(json.dumps(record))
