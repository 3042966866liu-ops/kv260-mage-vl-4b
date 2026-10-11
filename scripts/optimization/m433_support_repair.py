"""Retain the fixture rejection; restore only explicit synthetic release metadata."""
import json
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
from m427_prepare import once


def main():
    stage = ROOT / 'tmp/m43302/component_stage'
    fixture = json.loads((stage / 'TRIALS_FIXTURE_RESULT.json').read_bytes())
    original = json.loads((BASE / 'runs/M432-integrated-video-board-01/BOARD_RESULT.json').read_bytes())
    if fixture['released_buffers'] != [] or len(original['released_buffers']) != 7:
        raise RuntimeError('Actual fixture rejection cause differs')
    record = dict(status='REJECTED_M433_SYNTHETIC_COLLECTOR_RELEASE_METADATA',
        reason='Actual stream component kept its explicitly fake seven buffers resident; its empty released_buffers field overwrote the accepted template final release metadata in the synthetic full-gate record. Strict host collector correctly rejected.',
        stream_component_return_code=0, collector_rejection='Seven DMA ownership differs',
        support_source_sha256=sha(HERE / 'm433_support.py'), component_stdout_sha256=sha(ROOT / 'tmp/m43302/component/stdout.bin'),
        component_stderr_sha256=sha(ROOT / 'tmp/m43302/component/stderr.bin'), fixture_sha256=sha(stage / 'TRIALS_FIXTURE_RESULT.json'),
        board_run=False, packet_changed=False, M432_numerical_PASS_unchanged=True, temperature_measurement_enabled=False)
    out = BASE / 'runs/M433-offline-support-rejection-01/RESULT.json'
    atomic(out, encoded(record), immutable=True)
    sync('latest_m433_offline_support_rejection', dict(status=record['status'], result=out.relative_to(ROOT).as_posix(), sha256=sha(out)),
        f'## M433 离线合成回收记录拒绝（2026-10-07）\n\nSHA {sha(out)}；实际原stream组件rc0，但合成完整记录把驻留组件的空released_buffers覆盖原模板七块退出释放，严格collector正确拒绝。仅fixture资源退出元数据，0板端/模型性能，原stderr/stdout/脚本保留；M432数值PASS及包同SHA不改。02仅恢复明确synthetic退出模板并用新fixture目录，完成配套前不得上传。')
    s = (HERE / 'm433_support.py').read_text(encoding='utf-8')
    s = s.replace('tmp/m43302/', 'tmp/m43303/').replace('M433-performance-support-01', 'M433-performance-support-02')
    s = once(s, '    r=copy.deepcopy(original);r.update(fixture)', "    r=copy.deepcopy(original);r.update(fixture)\n    # Explicit full-gate synthetic release metadata; stream fixture itself has no real DMA.\n    r['released_buffers']=copy.deepcopy(original['released_buffers'])")
    s = s.replace("'m433_support.py'", "'m433_support02.py'")
    atomic(HERE / 'm433_support02.py', s.encode('utf-8'), immutable=True)
    print('M433_SUPPORT_REPAIR_READY', sha(out))


if __name__ == '__main__':
    main()
