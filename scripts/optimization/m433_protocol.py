"""Freeze the late11 complete-request experiment only after saved M432 closes."""
import copy
import json
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync


def main():
    board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    keys = ('latest_m432_integrated_board', 'latest_m432_integrated_closure',
            'latest_m430_complete_visual_closure', 'latest_m428_saved_language_board')
    prerequisites = {}
    for key in keys:
        e = board[key]
        if sha(ROOT / e['result']) != e['sha256'] or not all(e['sha256'] in (ROOT / n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md', 'docsMILESTONES.md')):
            raise RuntimeError('Prerequisite not synchronized')
        prerequisites[key] = copy.deepcopy(e)
    if board['latest_m432_integrated_closure']['numerical_pass'] is not True:
        raise RuntimeError('Complete-request numerical gate not passed')
    prior = board['latest_m425_warm_protocol']
    p = (ROOT / prior['result']).with_name('PROTOCOL.json')
    if sha(p) != prior['protocol_sha256']:
        raise RuntimeError('Original fixed measurement protocol differs')
    plan = json.loads(p.read_bytes())
    plan.update(schema='m433-late11-controlled-warm-complete-request-v1',
                prerequisites=prerequisites, scope='fixed159-two-view-original-versus-visual-MLP13-through23',
                changed_layers=list(range(13, 24)), supersedes_protocol_sha256=sha(p))
    plan['measurement'].update(candidate_visual_physical=286, candidate_visual_stage_bytes=49020928)
    plan['numerical'].update(A='bit exact saved original M428 and integrated M432',
                             B='bit exact saved late13..23 M428 and integrated M432', visual_source='M429/M432')
    if (plan['warmup_order'] != 'ABBA' or plan['formal_order'] != 'ABBABAAB' or plan['maximum_requests'] != 12
            or plan['temperature_measurement_enabled'] or plan['additional_DMA'] != 0):
        raise RuntimeError('Fixed experiment scope changed')
    folder = BASE / 'runs/M433-complete-request-warm-protocol-01'
    protocol = folder / 'PROTOCOL.json'
    atomic(protocol, encoded(plan), immutable=True)
    record = dict(status='FROZEN_M433_LATE11_COMPLETE_REQUEST_WARM_PROTOCOL',
                  protocol_sha256=sha(protocol), prerequisites=prerequisites,
                  source_sha256=sha(HERE / 'm433_protocol.py'),
                  original_measurement_protocol_sha256=sha(p),
                  board_run=False, performance_pass=False, temperature_measurement_enabled=False)
    out = folder / 'RESULT.json'
    atomic(out, encoded(record), immutable=True)
    text = f'## M433 后11层完整暖请求协议（2026-10-07）\n\nSHA {sha(out)}，协议{sha(protocol)}；M432完整接入数值已闭合才冻结。固定4预热ABBA＋8正式ABBABAAB、同一驻留runtime和七DMA/0新增，原stream complete计时，候选22暂存/286事务及pack/parse/恢复均计入，完整特征/logits/72KV哈希放计时后。保持原读盘/缓存/CPU与PL时钟匹配及双组正收益、配对95%下界>0判据，不拟合新阈值、删样本或加测；不测温、不接生产。尚无完整请求性能样本，下一步轻量实际provider组件和严格导出回收支持。'
    atomic(folder / 'REPORT.md', ('# M433 完整请求暖态实验\n\n' + text + '\n').encode('utf-8'), immutable=True)
    sync('latest_m433_complete_request_protocol', dict(result=out.relative_to(ROOT).as_posix(), sha256=sha(out), **record), text)
    print('M433_PROTOCOL_SYNC', sha(out), sha(protocol))


if __name__ == '__main__':
    main()
