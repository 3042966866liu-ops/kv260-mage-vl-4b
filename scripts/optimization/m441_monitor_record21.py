"""Record actual follow-up scheduling without changing frozen simulator inputs."""
from m351_workflow import ROOT, BASE, encoded, sha, sync
from m441_host_io08 import atomic

run = BASE / 'runs/M441-W2-W4-simulation-coverage-21'
result = {
    'status': 'ACTIVE_M441_SUPPLEMENTAL_SIMULATION_FOLLOWUP21',
    'automation_id': 'm441-w2-w4',
    'interval_minutes': 10,
    'preparation_sha256': sha(run / 'PREPARATION.json'),
    'active_sha256': sha(run / 'ACTIVE.json'),
    'compile_sha256': sha(run / 'COMPILE.json'),
    'frozen_controller_unmodified': True,
    'notification_policy': 'Only new milestone, failure, completion or required user action; deduplicate stage and SHA.',
    'completion': 'Run saved-only m441_sim_report21.py after all strict PASS, deliver report, then delete this automation.',
    'board': False,
}
path = run / 'FOLLOWUP.json'
atomic(path, encoded(result), immutable=True)
sync('latest_m441_simulation21_followup', {
    'status': result['status'], 'result': path.relative_to(ROOT).as_posix(),
    'sha256': sha(path), 'board': False,
}, '## M441补仿真21持续跟进已实际建立（2026-10-10）\n\n'
   'SHA ' + sha(path) + '；m441-w2-w4每10分钟在本聊天跟进实际有限控制器，未变健康运行静默，'
   '仅新里程碑/失败/完成/人工需求通知。已有START/log/raw只观察或Collect，冻结控制器不改、不重启、不kill；'
   '全部原字节严格PASS后三记录重核、执行已准备只读最终报告并删除本提醒。0新板端/生产修改。')
print(result['status'], sha(path))
