"""Retain budget rejection; align synthetic template with the tested sparse policy."""
import json
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
from m427_prepare import once


def main():
    original = json.loads((BASE / 'runs/M432-integrated-video-board-01/BOARD_RESULT.json').read_bytes())
    duplicate = [x for x in original['stage_memory'] if 'visual-submit:' in x['label']]
    if len(duplicate) != 572:
        raise RuntimeError('Numerical template submit checkpoint identity differs')
    record = dict(status='REJECTED_M433_SYNTHETIC_EXPORT_BUDGET_TEMPLATE',
        reason='Synthetic full-gate record reused all 572 per-submit memory records from diagnostic M432, although the actual tested M433 sparse policy omits only their storage. Full synthetic record exceeded the unchanged 4MiB export budget.',
        component_return_code=0, host_structural_check_passed=True, exporter_not_executed=True,
        support_source_sha256=sha(HERE / 'm433_support02.py'), component_stdout_sha256=sha(ROOT / 'tmp/m43303/component/stdout.bin'),
        component_stderr_sha256=sha(ROOT / 'tmp/m43303/component/stderr.bin'), numerical_submit_records=572,
        board_run=False, packet_changed=False, source_policy_or_budget_changed=False, temperature_measurement_enabled=False)
    out = BASE / 'runs/M433-offline-support-rejection-02/RESULT.json'
    atomic(out, encoded(record), immutable=True)
    sync('latest_m433_offline_support_rejection_02', dict(status=record['status'], result=out.relative_to(ROOT).as_posix(), sha256=sha(out)),
        f'## M433 离线合成导出预算拒绝（2026-10-07）\n\nSHA {sha(out)}；实际原stream/内存policy组件及host结构通过，但fixture仍复制M432的572次提交快照，未反映已验证M433仅省重复存储的策略，4MiB预算正确拒绝。导出未执行，0上板；原日志/两脚本/包同SHA保留。03只按实际policy省略fixture重复提交快照，保留原4MiB上限/所有运行时检查，不扩大硬件测试。')
    s = (HERE / 'm433_support02.py').read_text(encoding='utf-8').replace('tmp/m43303/', 'tmp/m43304/').replace('M433-performance-support-02', 'M433-performance-support-03')
    s = once(s, "    r['released_buffers']=copy.deepcopy(original['released_buffers'])", "    r['released_buffers']=copy.deepcopy(original['released_buffers'])\n    # Explicit synthetic metadata follows the actual tested sparse-policy storage rule.\n    r['stage_memory']=[x for x in r['stage_memory'] if 'visual-submit:' not in x['label']]")
    s = s.replace("'m433_support02.py'", "'m433_support03.py'")
    atomic(HERE / 'm433_support03.py', s.encode('utf-8'), immutable=True)
    print('M433_SUPPORT03_READY', sha(out))


if __name__ == '__main__':
    main()
