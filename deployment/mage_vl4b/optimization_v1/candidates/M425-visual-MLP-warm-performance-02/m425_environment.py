"""Readonly clock/storage observation; no temperature or cooling interfaces."""
import hashlib,os
from pathlib import Path
CPU_FIELDS=('scaling_driver','scaling_governor','scaling_min_freq','scaling_max_freq','related_cpus','scaling_cur_freq')

def environment_issues(row):
    issues=list(row.get('missing',[]))
    for key in ('kernel','cpu_policies','pl_clocks'):
        if not row.get(key):issues.append('unavailable: '+key)
    if 'storage_device' not in row or not row.get('mountinfo_sha256'):issues.append('unavailable: storage identity')
    if not row.get('pl_clocks',{}).get('pl0_ref',0):issues.append('PL0 clock not observable/active')
    if row.get('temperature_measurement_enabled') is not False:issues.append('Temperature reads must remain disabled')
    for name,policy in row.get('cpu_policies',{}).items():
        if any(not policy.get(k) for k in CPU_FIELDS):issues.append('incomplete CPU policy: '+name)
    return issues

def configuration(row):
    return {k:row.get(k) for k in ('kernel','cpu_policies','pl_clocks','storage_device','mountinfo_sha256','temperature_measurement_enabled')}

def read_environment():
    row=dict(kernel=list(os.uname()),cpu_policies={},pl_clocks={},missing=[],temperature_measurement_enabled=False)
    for path in sorted(Path('/sys/devices/system/cpu/cpufreq').glob('policy*')):
        policy={}
        for name in CPU_FIELDS:
            try:policy[name]=(path/name).read_text(encoding='utf-8').strip()
            except OSError:row['missing'].append(str(path/name))
        row['cpu_policies'][path.name]=policy
    try:
        lines=Path('/sys/kernel/debug/clk/clk_summary').read_text(encoding='utf-8').splitlines()
        rate_index=next(s.split() for s in lines if s.strip().startswith('clock') and 'rate' in s).index('rate')
        for line in lines:
            fields=line.split()
            if fields and fields[0] in ('pl0_ref','pl1_ref','pl2_ref','pl3_ref'):
                if fields[0] in row['pl_clocks']:raise ValueError('Duplicate PL clock')
                row['pl_clocks'][fields[0]]=int(fields[rate_index])
    except (OSError,ValueError,IndexError,StopIteration) as exc:row['missing'].append('PL clock summary: '+str(exc))
    try:
        row['storage_device']=Path('/home/ubuntu/tellme_release_install_20260926').stat().st_dev
        row['mountinfo_sha256']=hashlib.sha256(Path('/proc/self/mountinfo').read_bytes()).hexdigest()
    except OSError as exc:row['missing'].append('storage identity: '+str(exc))
    row['observability_issues']=environment_issues(row)
    return row
