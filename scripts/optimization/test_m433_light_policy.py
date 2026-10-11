"""Exercise the real parent assessment with explicit fake memory/CMA counters."""
import copy
from m433_light_policy import StagePolicy


def component():
    memory = dict(process_bytes=dict(VmRSS=100 << 20), system_bytes=dict(CmaFree=20 << 20, MemAvailable=2 << 30))
    counts = {'fixture:success': 7, 'fixture:failure': 0}
    record = {}
    calls = []
    def snapshot():
        calls.append('snapshot')
        return copy.deepcopy(memory)
    policy = StagePolicy(record, lambda: None, None, snapshot=snapshot, counters=lambda: copy.deepcopy(counts))
    policy.sealed = True
    policy.buffer_bytes = [6963200] * 4 + [389152, 2621440, 2621440]
    policy.baseline_rss = 100 << 20
    policy.initial_counts = copy.deepcopy(counts)
    for label in ('before-visual-submit:13:fc1', 'after-visual-submit:13:fc1'):
        assert policy.capture(label, True) == memory
    assert len(calls) == 2 and record.get('stage_memory', []) == []
    policy.capture('before-visual-stage:13:fc1', True)
    assert len(record['stage_memory']) == 1 and record['stage_memory'][0]['admission']['diagnostic_additional_explicit_cma_bytes'] == 0
    rejected = []
    def reject(label, kind):
        try:
            policy.capture('before-visual-submit:13:fc1', True)
        except kind:
            rejected.append(label)
        else:
            raise AssertionError('Admission failure lost: ' + label)
    counts['fixture:success'] += 1
    reject('counter-change', RuntimeError)
    counts['fixture:success'] -= 1
    memory['system_bytes']['MemAvailable'] = 1
    reject('ordinary-capacity', MemoryError)
    memory['system_bytes']['MemAvailable'] = 2 << 30
    memory['process_bytes']['VmRSS'] = 1200 << 20
    reject('PS-growth', MemoryError)
    memory['process_bytes']['VmRSS'] = 100 << 20
    policy.stop_reason = 'explicit fake latched stop'
    reject('latched-stop', RuntimeError)
    return dict(actual_parent_snapshot_count_and_assessment_executed=True, two_submit_checks_without_duplicate_storage=True,
                stage_evidence_preserved=True, negative_checks=rejected, memory_and_CMA_explicit_fake=True,
                no_board_capacity_or_performance_evidence=True)


if __name__ == '__main__':
    import json
    print('M433_LIGHT_POLICY_COMPONENT=' + json.dumps(component(), sort_keys=True))
