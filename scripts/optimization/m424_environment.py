"""Readonly environment with catalogue-pinned, processed AMS hwmon temperatures.

Channel numbers are monitored consistently, without assuming a PS/PL mapping.
The hwmon ABI provides millidegree Celsius; no raw ADC conversion is used.
"""
import json
from pathlib import Path
from m404_warm_conditions import read_environment as original_environment, environment_issues

ABI_SOURCE='https://www.kernel.org/doc/html/v5.15/hwmon/sysfs-interface.html'


def temperatures(expected, root=Path('/')):
    device=root/expected['path'].lstrip('/')
    def canonical(path):
        return '/'+path.resolve().relative_to(root.resolve()).as_posix()
    if canonical(device)!=expected['resolved_path'] or (device/'name').read_text(encoding='utf-8').strip()!=expected['name']:
        raise RuntimeError('Catalogue AMS hwmon identity changed')
    driver=device/'device/driver'
    if not driver.exists() or canonical(driver)!=expected['driver']:
        raise RuntimeError('Catalogue iio_hwmon driver identity changed')
    names=sorted(p.name for p in device.glob('temp*_input'))
    if names!=expected['inputs']:raise RuntimeError('Catalogue temperature channel set changed')
    rows={}
    for name in names:
        path=device/name
        value=int(path.read_text(encoding='utf-8').strip())
        if not -40000<=value<=150000:raise RuntimeError('Invalid processed hwmon temperature')
        rows['ams/'+name]=dict(type='ams:iio_hwmon:'+name,temperature_mC=value,
                              source=expected['path']+'/'+name,
                              resolved_path=canonical(path),units='millidegree_Celsius',
                              anatomical_channel_mapping_proven=False)
    return rows


def read_environment():
    expected=json.loads((Path(__file__).parent/'AMS_EXPECTED.json').read_bytes())
    row=original_environment()
    if row['thermal_zones']:raise RuntimeError('Unexpected thermal-zone topology; frozen catalogue required')
    row['thermal_zones']=temperatures(expected)
    row['temperature_source']='catalogue-pinned processed AMS iio_hwmon inputs'
    row['temperature_ABI_source']=ABI_SOURCE
    row['temperature_channel_mapping_proven']=False
    row['observability_issues']=environment_issues(row)
    return row
