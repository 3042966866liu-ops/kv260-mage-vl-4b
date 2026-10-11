"""Freeze catalogue identities and a no-Overlay environment probe."""
import ast,json,shutil,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
PKG=BASE/'candidates/M424-environment-probe-01'


def main():
    if PKG.exists():raise RuntimeError('Immutable probe already prepared')
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    prerequisites={}
    for key in ('latest_m404_sensor_board','latest_m423_integrated_closure','latest_m424_warm_protocol'):
        e=b[key];p=ROOT/e['result'];assert sha(p)==e['sha256']
        assert all(e['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
        prerequisites[key]=dict(result=e['result'],sha256=e['sha256'])
    raw=json.loads((ROOT/b['latest_m404_sensor_board']['result']).read_bytes())
    devices=raw['catalogue']['devices'];fields={x['path']:x for x in raw['catalogue']['fields']}
    d=[x for x in devices if x['family']=='hwmon' and fields.get(x['path']+'/name',{}).get('raw_text')=='ams']
    assert len(d)==1 and d[0]['driver']=='/sys/bus/platform/drivers/iio_hwmon'
    d=d[0];inputs=sorted(x.rsplit('/',1)[1] for x in fields if x.startswith(d['path']+'/temp') and x.endswith('_input'))
    assert inputs==['temp1_input','temp2_input','temp3_input']
    expected=dict(path=d['path'],resolved_path=d['resolved_path'],driver=d['driver'],name='ams',inputs=inputs,
                  catalogue_sha256=b['latest_m404_sensor_board']['sha256'],
                  unit_source='https://www.kernel.org/doc/html/v5.15/hwmon/sysfs-interface.html',
                  anatomical_channel_mapping_proven=False)
    stage=ROOT/'tmp/m424environment/component_stage';stage.mkdir(parents=True,exist_ok=False)
    for n in ('m424_environment.py','test_m424_environment.py','m404_warm_conditions.py'):
        shutil.copyfile(HERE/n,stage/n)
    linux='/mnt/c/'+stage.relative_to(ROOT.anchor).as_posix()
    # -I excludes ambient paths; only this clean explicit three-file fixture stage is added.
    code=f"import runpy,sys;sys.path.insert(0,{linux!r});runpy.run_path({(linux+'/test_m424_environment.py')!r},run_name='__main__')"
    p=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/home/lyy/projects/qwen_baseline/.venv/bin/python','-I','-B','-c',code],capture_output=True,text=True,encoding='utf-8')
    if p.returncode or 'rejects=8' not in p.stdout:raise RuntimeError(p.stdout+p.stderr)
    PKG.mkdir(parents=True)
    for n in ('m424_environment.py','m424_environment_probe.py','m404_warm_conditions.py'):shutil.copyfile(HERE/n,PKG/n)
    atomic(PKG/'AMS_EXPECTED.json',encoded(expected))
    runner='''#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ "${2:-}" == Collect ]]; then
  exec /usr/local/share/pynq-venv/bin/python -B m424_environment_probe.py "$1" Collect
fi
if [[ "${M424_ENABLE_READONLY_ENV:-0}" != 1 || "${2:-}" != Run ]]; then exit 2; fi
set +e
/usr/local/share/pynq-venv/bin/python -B m424_environment_probe.py "$1" --enable-readonly-probe
gate_rc=$?
set -e
printf 'M424_ENV_DONE gate_rc=%s\\n' "$gate_rc"
exit "$gate_rc"
'''
    atomic(PKG/'run_m424_environment.sh',runner.encode('utf-8'))
    for f in PKG.glob('*.py'):ast.parse(f.read_text(encoding='utf-8'),feature_version=(3,10))
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(x['sha256']+'  '+x['path']+'\n' for x in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))))
    r=dict(status='PASS_OFFLINE_M424_PROCESSED_HWMON_ENVIRONMENT_PREPARATION',prerequisites=prerequisites,
           manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),fake_sysfs_component_output=p.stdout,
           anatomical_channel_mapping_proven=False,temperature_unit_source=expected['unit_source'],
           stable_production_sources_changed=False,board_run=False,performance_pass=False)
    out=BASE/'runs/M424-environment-preparation-01/RESULT.json';atomic(out,encoded(r),immutable=True)
    sync('latest_m424_environment_preparation',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=r['manifest_sha256']),
         f'## M424 AMS已处理温度观察准备（2026-10-06）\n\nSHA {sha(out)}；manifest {r["manifest_sha256"]}。'
         '原目录确认ams/iio_hwmon/temp1..3，按Linux5.15 hwmon ABI读取毫摄氏度，不推断编号与PS/PL对应，不作ADC转换。'
         '隔离WSL-I自有文件/符号链接fake sysfs正例及8身份/范围/缺项拒绝，通过；不是板端环境证据。'
         '下一步仅一次无Overlay只读观察，完整环境成立后才准备暖请求轻量入口。')
    print('M424_ENV_PREPARATION_SYNC',sha(out),r['manifest_sha256'])


if __name__=='__main__':main()
