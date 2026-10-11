"""Bounded readonly hwmon/IIO catalogue; no temperature conversions or model."""
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
OUT=Path('/home/ubuntu/m404_sensor_inventory_01/RESULT.json')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def gather(root=Path('/'), *, iio_pattern='iio:device*'):
    rows=[];devices=[]
    for family,base,pattern in (
        ('hwmon','sys/class/hwmon','hwmon*'),
        ('iio','sys/bus/iio/devices',iio_pattern),
        ('thermal','sys/class/thermal','thermal_zone*')):
        for device in sorted((root/base).glob(pattern)):
            if len(devices)>=16:raise RuntimeError('Sensor device budget exceeded')
            devices.append(dict(family=family,path='/'+device.relative_to(root).as_posix(),
                                resolved_path=str(device.resolve()),
                                driver=str((device/'device/driver').resolve()) if (device/'device/driver').exists() else None))
            files=[device/n for n in ('name','type') if (device/n).exists()]
            if family=='hwmon':files+=list(device.glob('temp*_input'))+list(device.glob('temp*_label'))
            elif family=='iio':files+=list(device.glob('in_temp*'))
            else:files+=[device/'temp'] if (device/'temp').exists() else []
            for file in sorted(set(files)):
                if not file.is_file():continue
                if len(rows)>=128:raise RuntimeError('Sensor field budget exceeded')
                row=dict(family=family,path='/'+file.relative_to(root).as_posix(),resolved_path=str(file.resolve()))
                try:
                    with file.open('r',encoding='utf-8') as f:raw=f.read(1025)
                    if len(raw)>1024:raise RuntimeError('Sensor field exceeds read budget')
                    row['raw_text']=raw.strip()
                except OSError as exc:row['read_error']=type(exc).__name__+': '+str(exc)
                rows.append(row)
    return dict(devices=devices,fields=rows,temperature_conversion_performed=False,
                driver_sensor_association_proven=False,throttling_absence_proven=False)


def emit():
    raw=OUT.read_bytes();parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    print('M404_SENSOR_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    for i,p in enumerate(parts):
        print(f'M404_SENSOR_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode('ascii'),flush=True)
        time.sleep(.025)


def main():
    if os.geteuid()!=0:raise RuntimeError('Root required')
    if sys.argv[1:]==['Collect']:emit();return 0
    if len(sys.argv)!=3 or sys.argv[2]!='--enable-readonly-catalogue':raise RuntimeError('Catalogue disabled by default')
    if OUT.parent.exists():raise RuntimeError('Original catalogue exists; Collect only')
    manifest=HERE/'PACKAGE_MANIFEST.json'
    if sha(manifest)!=sys.argv[1]:raise RuntimeError('Catalogue manifest differs')
    m=json.loads(manifest.read_bytes());names=set(r['path'] for r in m['files'])
    if len(names)!=m['file_count'] or {p.name for p in HERE.iterdir()}!=names|{'PACKAGE_MANIFEST.json'}:raise RuntimeError('Catalogue whitelist differs')
    for row in m['files']:
        p=HERE/row['path']
        if p.name!=row['path'] or p.is_symlink() or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Catalogue payload differs')
    if sum(r['bytes'] for r in m['files'])!=m['total_bytes']:raise RuntimeError('Catalogue bytes differ')
    started=time.monotonic();catalogue=gather()
    r=dict(status='OBSERVED_SENSOR_CATALOGUE_ONLY',manifest_sha256=sys.argv[1],kernel=list(os.uname()),
           catalogue=catalogue,elapsed_s=time.monotonic()-started,overlay_loaded=False,dma_allocations=0,
           model_forward_calls=0,fpga_transactions=0,cache_changes=False,numerical_pass=False,
           performance_pass=False,formal_promotion_allowed=False)
    raw=(json.dumps(r,ensure_ascii=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
    if len(raw)>32768:raise RuntimeError('Catalogue export budget exceeded')
    OUT.parent.mkdir();temp=OUT.with_suffix('.partial')
    with temp.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    os.replace(temp,OUT);emit();return 0


if __name__=='__main__':raise SystemExit(main())
