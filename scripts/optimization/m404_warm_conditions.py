"""Frozen M404 protocol checks. Only read system evidence; never alter caches."""
import hashlib
import json
import math
import os
from pathlib import Path
import time

PROTOCOL_SHA = '3a25854d9b24ae47f86a295b6a56d460159e22614e6065eb3e317a302d5485d8'
ORDER = 'ABBAABBABAAB'
PAIRS = ((1, 2), (4, 3), (6, 5), (7, 8))


class WarmConditionsNotEstablished(RuntimeError):
    pass


def read_environment():
    """Unavailable fields are explicit. Reading debugfs is not mounting it."""
    row = dict(kernel=list(os.uname()), cpu_policies={}, pl_clocks={},
               thermal_zones={}, cooling_devices={}, missing=[])
    for path in sorted(Path('/sys/devices/system/cpu/cpufreq').glob('policy*')):
        values = {}
        for name in ('scaling_driver', 'scaling_governor', 'scaling_min_freq',
                     'scaling_max_freq', 'related_cpus', 'scaling_cur_freq'):
            try: values[name] = (path / name).read_text(encoding='utf-8').strip()
            except OSError: row['missing'].append(str(path / name))
        row['cpu_policies'][path.name] = values
    try:
        lines = Path('/sys/kernel/debug/clk/clk_summary').read_text(encoding='utf-8').splitlines()
        header = next(s.split() for s in lines if s.strip().startswith('clock') and 'rate' in s)
        rate_index = header.index('rate')
        for line in lines:
            fields = line.split()
            if fields and fields[0] in ('pl0_ref', 'pl1_ref', 'pl2_ref', 'pl3_ref'):
                if fields[0] in row['pl_clocks']: raise ValueError('Duplicate PL clock identity')
                row['pl_clocks'][fields[0]] = int(fields[rate_index])
    except (OSError, ValueError, IndexError, StopIteration) as exc:
        row['missing'].append('PL clock summary: ' + str(exc))
    for path in sorted(Path('/sys/class/thermal').glob('thermal_zone*')):
        try:
            row['thermal_zones'][path.name] = dict(
                type=(path / 'type').read_text(encoding='utf-8').strip(),
                temperature_mC=int((path / 'temp').read_text(encoding='utf-8')))
        except (OSError, ValueError) as exc: row['missing'].append(str(path) + ': ' + str(exc))
    for path in sorted(Path('/sys/class/thermal').glob('cooling_device*')):
        try:
            row['cooling_devices'][path.name] = dict(
                type=(path / 'type').read_text(encoding='utf-8').strip(),
                max_state=int((path / 'max_state').read_text(encoding='utf-8')),
                cur_state=int((path / 'cur_state').read_text(encoding='utf-8')))
        except (OSError, ValueError) as exc: row['missing'].append(str(path) + ': ' + str(exc))
    # Identify actual weight storage without assuming a unique mount by dev number.
    weights = Path('/home/ubuntu/tellme_release_install_20260926')
    try:
        row['storage_device'] = weights.stat().st_dev
        row['mountinfo_sha256'] = hashlib.sha256(Path('/proc/self/mountinfo').read_bytes()).hexdigest()
    except OSError as exc: row['missing'].append('storage identity: ' + str(exc))
    row['observability_issues'] = environment_issues(row)
    return row


def environment_issues(row):
    issues = list(row.get('missing', []))
    for key in ('kernel', 'cpu_policies', 'pl_clocks', 'thermal_zones', 'cooling_devices'):
        if not row.get(key): issues.append('unavailable: ' + key)
    if 'storage_device' not in row or not row.get('mountinfo_sha256'):
        issues.append('unavailable: storage identity')
    if not row.get('pl_clocks', {}).get('pl0_ref', 0): issues.append('PL0 clock not observable/active')
    for name, policy in row.get('cpu_policies', {}).items():
        required = ('scaling_driver', 'scaling_governor', 'scaling_min_freq',
                    'scaling_max_freq', 'related_cpus', 'scaling_cur_freq')
        if any(not policy.get(k) for k in required): issues.append('incomplete CPU policy: ' + name)
    for name, zone in row.get('thermal_zones', {}).items():
        t = zone.get('temperature_mC')
        if not zone.get('type') or type(t) is not int or not -40000 <= t <= 150000:
            issues.append('invalid thermal identity/reading: ' + name)
    for name, cooling in row.get('cooling_devices', {}).items():
        if not cooling.get('type') or type(cooling.get('cur_state')) is not int:
            issues.append('invalid cooling observation: ' + name)
        elif cooling['cur_state'] != 0: issues.append('cooling/throttling active: ' + name)
    return issues


def configuration(row):
    return dict(kernel=row.get('kernel'), storage_device=row.get('storage_device'),
                mountinfo_sha256=row.get('mountinfo_sha256'), pl_clocks=row.get('pl_clocks'),
                cpu_policies={n: {k: v for k, v in p.items() if k != 'scaling_cur_freq'}
                              for n, p in row.get('cpu_policies', {}).items()},
                thermal_types={n: z.get('type') for n, z in row.get('thermal_zones', {}).items()},
                cooling_types={n: {k: v for k, v in c.items() if k != 'cur_state'}
                               for n, c in row.get('cooling_devices', {}).items()})


def sample_issues(sample, reference, *, require_warm):
    issues = []
    for which in ('before_environment', 'after_environment'):
        env = sample.get(which, {})
        issues.extend(which + ': ' + e for e in environment_issues(env))
        if configuration(env) != configuration(reference): issues.append(which + ': configuration changed')
    for key in ('before_cache', 'after_cache'):
        c = sample.get(key, {})
        if any(c.get(k) != v for k, v in dict(cache_entries=26, cache_bytes=66699264,
                                             cache_misses=26, cache_within_budget=True).items()):
            issues.append(key + ': bounded visual cache differs')
    if require_warm:
        b = sample.get('io_delta', {}).get('read_bytes')
        if type(b) is not int or not 0 <= b <= 1048576: issues.append('warm read_bytes limit')
        m = sample.get('major_fault_delta')
        if type(m) is not int or m != 0: issues.append('warm major fault limit')
    t = sample.get('timing', {}).get('total_ms')
    if type(t) not in (int, float) or not math.isfinite(t) or not 0 < t <= 180000:
        issues.append('request budget/invalid timer')
    return issues


def paired_conditions(samples):
    issues = []
    if len(samples) != 8: return ['formal eight requests incomplete']
    for a, b in PAIRS:
        x, y = samples[a-1], samples[b-1]
        if abs(x['io_delta']['read_bytes'] - y['io_delta']['read_bytes']) > 1048576:
            issues.append(f'pair {a}/{b}: read mismatch')
        ex, ey = x['before_environment']['thermal_zones'], y['before_environment']['thermal_zones']
        if set(ex) != set(ey): issues.append(f'pair {a}/{b}: thermal identity differs')
        else:
            for n in ex:
                if abs(ex[n]['temperature_mC'] - ey[n]['temperature_mC']) > 5000:
                    issues.append(f'pair {a}/{b}: entry temperature mismatch {n}')
    return issues


class WarmSequence:
    def __init__(self, result, reference, clock=time.monotonic):
        self.result, self.reference, self.clock = result, reference, clock
        self.started = clock()
        self.recorded = 0
        result['warm_protocol_sha256'] = PROTOCOL_SHA
        result['warm_sequence'] = ORDER
        result['warm_conditions_established'] = False
        result['warmup_samples'], result['formal_samples'] = [], []

    def stop(self, issues):
        self.result['experiment_stop'] = dict(status='WARM_CONDITIONS_NOT_ESTABLISHED', issues=issues)
        raise WarmConditionsNotEstablished('; '.join(issues))

    def before(self, index):
        if index != self.recorded or index >= 12: self.stop(['sequence position invalid'])
        if self.clock() - self.started >= 1800: self.stop(['sequence budget exhausted before next request'])
        if index == 4 and not self.result['warm_conditions_established']:
            self.stop(['fixed warmups did not establish admission'])

    def record(self, sample):
        i = self.recorded
        if sample['index'] != i+1 or sample['variant'] != ORDER[i]: self.stop(['sample identity/order differs'])
        sample['phase'] = 'warmup' if i < 4 else 'formal'
        sample['phase_index'] = i+1 if i < 4 else i-3
        self.result['warmup_samples' if i < 4 else 'formal_samples'].append(sample)
        self.recorded += 1
        issues = sample_issues(sample, self.reference, require_warm=i >= 2)
        if i >= 5 and i % 2 == 1:
            x, y = self.result['formal_samples'][-2:]
            if abs(x['io_delta']['read_bytes']-y['io_delta']['read_bytes']) > 1048576:
                issues.append('adjacent pair read mismatch')
            for n in self.reference['thermal_zones']:
                if abs(x['before_environment']['thermal_zones'][n]['temperature_mC']-
                       y['before_environment']['thermal_zones'][n]['temperature_mC']) > 5000:
                    issues.append('adjacent entry temperature mismatch: '+n)
        if self.clock()-self.started > 1800: issues.append('sequence budget exhausted')
        if issues: self.stop(issues)
        if i == 3: self.result['warm_conditions_established'] = True
