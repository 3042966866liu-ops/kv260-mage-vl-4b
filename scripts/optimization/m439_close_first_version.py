"""Summarize saved first-version evidence; never rerun a tool or change RTL."""
import json
import xml.etree.ElementTree as ET
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync

specs = [
    ('csim', 'M439-record-load-csim-02', 'PASS_M439_REAL_RECORD_NUMERICAL_CSIM'),
    ('schedule', 'M439-original-MAC-schedule-02', None),
    ('narrow', 'M439-record-load-narrow-closure-01', 'PASS_M439_NARROW_BURST_AND_CYCLE_COMPARISON'),
    ('core', 'M439-record-load-core-OOC-closure-01', None),
]
# The schedule binding is taken from the synchronized board record, avoiding
# guesses about the original immutable result directory name.
board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
schedule = [v for v in board.values() if isinstance(v, dict) and v.get('sha256') ==
            '4323b265a892d1607589362377790ec5b7bf23dbae6154cf459a470035fd2aeb']
assert len(schedule) == 1
records = {}; bindings = []
for label, name, status in specs:
    if label == 'schedule':
        value = schedule[0]
        path = ROOT / value.get('result', value.get('evidence_path', ''))
    else:
        path = BASE / 'runs' / name / 'RESULT.json'
    raw = json.loads(path.read_bytes()); digest = sha(path)
    assert any(isinstance(v, dict) and v.get('sha256') == digest for v in board.values())
    assert all(digest in (ROOT / n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md', 'docsMILESTONES.md'))
    if status: assert raw['status'] == status
    records[label] = raw
    bindings.append(dict(label=label, path=path.relative_to(ROOT).as_posix(), sha256=digest))

core = records['core']; narrow = records['narrow']
passed = core['status'] == 'PASS_M439_SAME_CONSTRAINT_CORE_ROUTED_TIMING'
buffers = []
xml = ROOT / 'tmp/m439_hls_project_02/hls/impl/verilog/report/vivado_impl.xml'
if xml.exists():
    for module in ET.parse(xml).getroot().findall('RtlModules/RtlModule'):
        if module.get('CELL', '').endswith('/record_U'):
            node = module.find('Resources')
            buffers.append(dict(cell=module.get('CELL'), resources=dict(node.attrib) if node is not None else {}))

r = dict(status='PASS_M439_FIRST_VERSION_OFFLINE_COMPARISON_PROTOCOL_PENDING' if passed else 'CLOSED_M439_FIRST_VERSION_CORE_TIMING_OR_IMPLEMENTATION',
         build_id='0x4D343339', baseline_build_id='0x4D333537', source_evidence=bindings,
         comparisons=narrow['rows'], core_checks=core['checks'], routed_resources=core['resources'],
         resource_delta=core['resource_delta'], timing=core['timing'], timing_summary=core['timing_summary'],
         physical_record_buffers=buffers, extra_PS_slots=0, extra_CMA_banks=0, next_record_prefetch=False,
         complete_L2_protocol=False, complete_L3_shell=False, board=False, whole_request_speed_proven=False, promotion=False,
         next_step=core['next_step'], M437_preserved=True)
p = BASE / 'runs/M439-first-version-summary-01/RESULT.json'
atomic(p, encoded(r), immutable=True)
report = '# M439 第一版：当前权重记录连续读入片内缓冲\n\n'
report += ('小片段 burst、数值与周期对照成立，核心同约束时序通过。下一步是最大协议门禁；尚未完成整壳和板端验证。\n\n' if passed else
           '小片段 burst 与周期对照成立，但核心实现／时序门禁未通过，本版停止扩展，保留原核。\n\n')
report += '| 格式 | 延迟模型 | 原周期 | 候选周期 | 减少 | 每 shard 请求 | 返回字数 |\n|---|---|---:|---:|---:|---|---:|\n'
for x in r['comparisons']:
    report += f'| W{x["bits"]} | {x["mode"]} | {x["A_transaction_cycles"]} | {x["B_transaction_cycles"]} | {x["transaction_reduction_percent"]:.4f}% | {x["A_requests_per_shard"][0]}→{x["B_requests_per_shard"][0]} | {x["B_return_beats_per_shard"][0]} |\n'
report += '\n每 shard 原160次MAC调用、2560次有效迭代和7840 MAC忙周期保持。W2/W4小片段完整512输出及协议逐位核对；七组真实权重CSim累计16384输出通过。输入不是完整视频，VIP随机延迟不是实板DDR，表中百分比不可套用到完整请求。\n\n'
report += '| 实现资源 | 原M357 | M439 | 差值 |\n|---|---:|---:|---:|\n'
for k, v in core['resources'].items():
    report += f'| {k} | {core["original_M357"]["resources"].get(k,0)} | {v} | {core["resource_delta"][k]:+d} |\n'
report += '\n原4.8ns XDC要求逐字节SHA相同；实际时序：`' + json.dumps(r['timing_summary']) + '`。\n\n'
report += '独立Build0x4D343339，只改变当前记录的连续读取组织；无下一条预取／PS slot／CMA bank。保留首版自动flatten拒绝、W4时间0入口失败、收集器只读修正及所有原始证据。完整最大FIFO/背压/超时门禁尚待执行，不称为完整L2/L3或板端PASS。M437视觉范围、原语言路径和稳定服务保持。\n\n'
report += '下一步：' + r['next_step'] + '\n'
atomic(p.parent / 'REPORT.md', report.encode('utf-8'), immutable=True)
sync('latest_m439_first_version_summary', dict(status=r['status'], result=p.relative_to(ROOT).as_posix(), sha256=sha(p), build_id=r['build_id'], board=False),
     '## M439 第一版统一裁决（2026-10-07）\n\nSHA ' + sha(p) + '；' + r['status'] + '。原数值/计算序保持，实际地址请求W2 360→41、W4 680→42；核心实际资源/同XDC时序及失败保留见REPORT。非完整L2/L3、板端或请求新收益，0新增PS/CMA。下一步 ' + r['next_step'])
print(r['status'], sha(p))
