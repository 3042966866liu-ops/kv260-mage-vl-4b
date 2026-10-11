"""Catalogue candidate: preserve frozen M404 protocol and original observation."""
import ast
import importlib.util
import json
from pathlib import Path
import tempfile
from m351_workflow import ROOT, BASE, HERE, sha, atomic, encoded, sync

PKG=BASE/'candidates/M404-sensor-catalogue-01'


def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());e=b['latest_m404_environment_board']
    assert e['status']=='WARM_ENVIRONMENT_UNPROVEN' and e['sha256']==sha(ROOT/e['result'])
    assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    if PKG.exists():raise RuntimeError('Immutable catalogue package exists')
    spec=importlib.util.spec_from_file_location('m404_sensor_check',HERE/'m404_sensor_inventory.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    root=ROOT/'tmp/m404sensor';root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root) as d:
        fixture=Path(d)
        assert mod.gather(fixture)['fields']==[]
        # Windows fixture names cannot contain ':'. Only this test supplies an alias;
        # production main calls gather() with the literal Linux default unchanged.
        for n,v in {'sys/class/hwmon/hwmon0/name':'fake-hwmon','sys/class/hwmon/hwmon0/temp1_input':'45000',
                    'sys/bus/iio/devices/iio_device0/name':'fake-adc','sys/bus/iio/devices/iio_device0/in_temp0_raw':'35000',
                    'sys/bus/iio/devices/iio_device0/in_temp0_scale':'7.77','sys/bus/iio/devices/iio_device0/in_temp0_offset':'-36000',
                    'sys/bus/iio/devices/iio_device0/in_voltage0_raw':'not a temperature; do not read'}.items():
            p=fixture/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(v,encoding='utf-8')
        r=mod.gather(fixture,iio_pattern='iio_device*');assert len(r['fields'])==6 and len(r['devices'])==2
        assert not r['temperature_conversion_performed'] and not r['throttling_absence_proven']
        p=fixture/'sys/class/hwmon/hwmon0/temp1_input';p.write_text('x'*1025,encoding='utf-8')
        try:mod.gather(fixture)
        except RuntimeError:pass
        else:raise AssertionError('Unbounded field read accepted')
        p.write_text('45000',encoding='utf-8')
        for i in range(17):(fixture/f'sys/class/hwmon/hwmon{i+1}').mkdir()
        try:mod.gather(fixture)
        except RuntimeError:pass
        else:raise AssertionError('Unbounded device scan accepted')
    ast.parse((HERE/'m404_sensor_inventory.py').read_bytes(),feature_version=(3,10))
    PKG.mkdir();atomic(PKG/'m404_sensor_inventory.py',(HERE/'m404_sensor_inventory.py').read_bytes(),immutable=True)
    runner='''#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
manifest_sha=${1:?manifest SHA}
mode=${2:?Run or Collect}
if [[ "$mode" == Collect ]]; then
 exec /usr/local/share/pynq-venv/bin/python -B ./m404_sensor_inventory.py Collect
fi
[[ "$mode" == Run && "${M404_ENABLE_READONLY_SENSOR:-0}" == 1 ]] || exit 2
printf '%s  PACKAGE_MANIFEST.json\\n' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
exec /usr/local/share/pynq-venv/bin/python -B ./m404_sensor_inventory.py "$manifest_sha" --enable-readonly-catalogue
'''
    atomic(PKG/'run_m404_sensor.sh',runner.encode('utf-8'),immutable=True)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'),immutable=True)
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='m404-bounded-sensor-catalogue-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))),immutable=True)
    value=dict(status='PASS_OFFLINE_BOUNDED_SENSOR_CATALOGUE',prior_observation_sha256=e['sha256'],
               manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),package_files=len(rows),package_bytes=sum(r['bytes'] for r in rows),
               actual_gather_fixture_checked=True,Windows_fixture_colon_alias_explicit=True,Linux_default_pattern_unchanged=True,
               non_temperature_fields_excluded=True,empty_and_read_and_device_budgets_checked=True,
               numerical_conversion=False,board_run=False,performance_pass=False)
    out=BASE/'runs/M404-sensor-preparation-01/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    sync('latest_m404_sensor_preparation',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=h,manifest_sha256=value['manifest_sha256']),
         f'## M404 温度来源只读目录准备（2026-10-05）\n\nSHA {h}；原只读观察{e["sha256"]}保持，thermal_zone无条目，不代表所有温度接口不存在；仅hwmon/IIO/thermal固定目录最多16设备/128字段/1024字符，自有fixture边界检查。'
         '不计算温度、不证明降频、无Overlay/模型/FPGA或缓存变化；下一步一次只读目录，原暖协议门槛不降低。')
    print(json.dumps(value|dict(sha256=h)))


if __name__=='__main__':main()
