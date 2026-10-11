"""Prepare/test a bounded readonly observer before any expensive warm request."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from m351_workflow import ROOT, BASE, HERE, sha, atomic, encoded, sync
import m404_warm_conditions as conditions

PKG = BASE / 'candidates/M404-environment-observer-01'


def checks():
    root = ROOT / 'tmp/m404'; root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as d:
        fixture = Path(d)
        files = {
            '/sys/devices/system/cpu/cpufreq/policy0/scaling_driver': 'cpufreq-dt',
            '/sys/devices/system/cpu/cpufreq/policy0/scaling_governor': 'schedutil',
            '/sys/devices/system/cpu/cpufreq/policy0/scaling_min_freq': '299999',
            '/sys/devices/system/cpu/cpufreq/policy0/scaling_max_freq': '1199999',
            '/sys/devices/system/cpu/cpufreq/policy0/related_cpus': '0 1 2 3',
            '/sys/devices/system/cpu/cpufreq/policy0/scaling_cur_freq': '1199999',
            '/sys/kernel/debug/clk/clk_summary': 'clock enable_cnt prepare_cnt protect_cnt rate accuracy phase duty cycle\n pl0_ref 1 1 0 100000000 0 0 50000\n',
            '/sys/class/thermal/thermal_zone0/type': 'cpu-thermal',
            '/sys/class/thermal/thermal_zone0/temp': '45000',
            '/sys/class/thermal/cooling_device0/type': 'cpufreq',
            '/sys/class/thermal/cooling_device0/max_state': '3',
            '/sys/class/thermal/cooling_device0/cur_state': '0',
            '/proc/self/mountinfo': 'explicit fake mount identity',
            '/home/ubuntu/tellme_release_install_20260926/fixture': 'self-owned fixture',
        }
        for n, content in files.items():
            p = fixture / n.lstrip('/'); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(content, encoding='utf-8')
        saved = conditions.Path, conditions.os
        conditions.Path = lambda p: fixture / p.lstrip('/')
        conditions.os = SimpleNamespace(uname=lambda: ('Linux', 'fake-board', 'fake-kernel', 'fake-version', 'aarch64'))
        try:
            reference = conditions.read_environment(); assert not reference['observability_issues']
            assert reference['pl_clocks'] == {'pl0_ref': 100000000}
            sample = dict(index=1, variant='A', before_environment=reference, after_environment=copy.deepcopy(reference),
                          before_cache=dict(cache_entries=26, cache_bytes=66699264, cache_misses=26, cache_within_budget=True),
                          io_delta=dict(read_bytes=0), major_fault_delta=0, timing=dict(total_ms=100000))
            sample['after_cache'] = copy.deepcopy(sample['before_cache'])
            assert not conditions.sample_issues(sample, reference, require_warm=True)
            mutated = []
            for key in ('cpu_policies', 'pl_clocks', 'thermal_zones', 'cooling_devices'):
                q=copy.deepcopy(sample); q['before_environment'][key]={}; mutated.append(q)
            for read in (-1, 1048577, True):
                q=copy.deepcopy(sample); q['io_delta']['read_bytes']=read; mutated.append(q)
            for fault in (1, -1, True):
                q=copy.deepcopy(sample); q['major_fault_delta']=fault; mutated.append(q)
            q=copy.deepcopy(sample); q['after_environment']['pl_clocks']['pl0_ref']=200000000; mutated.append(q)
            q=copy.deepcopy(sample); q['after_environment']['cooling_devices']['cooling_device0']['cur_state']=1; mutated.append(q)
            q=copy.deepcopy(sample); q['after_cache']['cache_misses']=27; mutated.append(q)
            q=copy.deepcopy(sample); q['timing']['total_ms']=180001; mutated.append(q)
            assert all(conditions.sample_issues(q, reference, require_warm=True) for q in mutated)
            result={}; seq=conditions.WarmSequence(result, reference, clock=lambda:0)
            for i, variant in enumerate(conditions.ORDER):
                seq.before(i); q=copy.deepcopy(sample); q.update(index=i+1,variant=variant); seq.record(q)
            assert len(result['warmup_samples'])==4 and len(result['formal_samples'])==8 and result['warm_conditions_established']
            assert not conditions.paired_conditions(result['formal_samples'])
            q=copy.deepcopy(result['formal_samples']); q[1]['before_environment']['thermal_zones']['thermal_zone0']['temperature_mC']+=5001
            assert conditions.paired_conditions(q)
            timer=[0]; result={}; seq=conditions.WarmSequence(result,reference,clock=lambda:timer[0]); timer[0]=1800
            try: seq.before(0)
            except conditions.WarmConditionsNotEstablished: pass
            else: raise AssertionError('Budget accepted')
            missing=fixture/'sys/class/thermal/cooling_device0/cur_state'; missing.unlink()
            assert conditions.read_environment()['observability_issues']
            return len(mutated), reference
        finally: conditions.Path, conditions.os = saved


def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes()); e=b['latest_m404_warm_protocol']
    assert e['sha256']==sha(ROOT/e['result'])
    assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    plan=json.loads((ROOT/e['result']).read_bytes())
    assert plan['protocol_sha256']==conditions.PROTOCOL_SHA==sha(ROOT/plan['protocol_path'])
    if PKG.exists(): raise RuntimeError('Immutable observation package exists')
    negative, reference=checks()
    names=('m404_warm_conditions.py','m404_environment_probe.py')
    for n in names:
        t=ast.parse((HERE/n).read_bytes(),feature_version=(3,10))
        imported={a.name.split('.')[0] for node in ast.walk(t) if isinstance(node,ast.Import) for a in node.names}
        assert not imported.intersection({'numpy','pynq','torch','serial','subprocess'})
    PKG.mkdir(parents=True)
    for n in names: atomic(PKG/n,(HERE/n).read_bytes(),immutable=True)
    atomic(PKG/'PROTOCOL_PREREQUISITE.json',encoded(dict(protocol_sha256=conditions.PROTOCOL_SHA,preparation_sha256=e['sha256'])),immutable=True)
    runner='''#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
manifest_sha=${1:?manifest SHA required}
mode=${2:?Run or Collect required}
if [[ "$mode" == Collect ]]; then
  exec /usr/local/share/pynq-venv/bin/python -B ./m404_environment_probe.py Collect
fi
[[ "$mode" == Run && "${M404_ENABLE_READONLY_ENV:-0}" == 1 ]] || exit 2
printf '%s  PACKAGE_MANIFEST.json\\n' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
[[ ! -e /home/ubuntu/m404_environment_observation_01 ]] || exit 2
exec /usr/local/share/pynq-venv/bin/python -B ./m404_environment_probe.py "$manifest_sha" --enable-readonly-observation
'''
    atomic(PKG/'run_m404_environment.sh',runner.encode('utf-8'),immutable=True)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'),immutable=True)
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='m404-readonly-environment-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))),immutable=True)
    spec=importlib.util.spec_from_file_location('m404_actual_probe',PKG/'m404_environment_probe.py'); probe=importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)
    probe.verify(sha(PKG/'PACKAGE_MANIFEST.json'))
    try: probe.verify('0'*64)
    except RuntimeError: pass
    else: raise AssertionError('Wrong manifest accepted')
    value=dict(status='PASS_OFFLINE_READONLY_ENVIRONMENT_OBSERVER',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),protocol_sha256=conditions.PROTOCOL_SHA,
               package_files=len(rows),package_bytes=sum(r['bytes'] for r in rows),explicit_fake_sysfs=True,fixture_negative_checks=negative,
               actual_environment_reader=True,sequence_4_warm_8_formal_checked=True,condition_budget_stop_checked=True,
               python310_syntax=True,board_run=False,overlay_loaded=False,model_forward_calls=0,performance_pass=False,
               source_sha256={n:sha(HERE/n) for n in names+('m404_environment_prepare.py',)})
    p=BASE/'runs/M404-environment-preparation-01/RESULT.json'; atomic(p,encoded(value),immutable=True); digest=sha(p)
    sync('latest_m404_environment_preparation',dict(status=value['status'],result=p.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=value['manifest_sha256']),
         f'## M404 只读环境观察准备（2026-10-05）\n\nSHA {digest}，协议{conditions.PROTOCOL_SHA}；{len(rows)}载荷/{value["package_bytes"]}B，'
         f'实际sysfs读取函数用明确自有fake文件和{negative}故障拒绝、4预热/8正式编排条件及预算停止检查。CPU-only/default-off，无Overlay/模型/FPGA；'
         '实际时钟/温度/降频字段未证明，下一步同COM3授权后仅一次只读观察，缺失则停止暖态实验，不启动十二请求。')
    print(json.dumps(value|dict(sha256=digest)))


if __name__=='__main__': main()
