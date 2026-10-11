"""Strict transfer receipts and saved CPU observation; no hardware execution."""
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
from m351_workflow import ROOT, BASE, sha, atomic, encoded, sync
from m404_sensor_prepare import PKG
from m404_warm_conditions import PROTOCOL_SHA, environment_issues


def transfer():
    manifest=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes())
    names=['PACKAGE_MANIFEST.json']+[r['path'] for r in manifest['files']]
    receipts=[]
    for name in names:
        prefix='upload_'+name.replace('.','_'); folder=ROOT/'tmp/m404sensor'
        final=folder/(prefix+'_final.log'); text=final.read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in text or sha(PKG/name) not in text: raise RuntimeError('Final file receipt differs')
        size=(PKG/name).stat().st_size; count=(size+899)//900
        chunks=sorted(folder.glob(prefix+'_chunk_*.log'))
        if len(chunks)!=count: raise RuntimeError('Chunk receipt count differs')
        for i,p in enumerate(chunks,1):
            if not re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,size))+r'\s',p.read_text(encoding='utf-8-sig')):
                raise RuntimeError('Chunk receipt order differs')
        receipts.append(dict(path=name,sha256=sha(PKG/name),receipt_sha256=sha(final),chunks=count))
    syntax=ROOT/'tmp/m404sensor/syntax.log'
    assert '__M404_SENSOR_SYNTAX_RC_0__' in syntax.read_text(encoding='utf-8-sig')
    value=dict(status='PASS_M404_READONLY_OBSERVER_TRANSFER',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),files=receipts,syntax_sha256=sha(syntax),board_observation_started=False)
    out=BASE/'runs/M404-sensor-transfer-01/RESULT.json'; atomic(out,encoded(value),immutable=True); h=sha(out)
    sync('latest_m404_sensor_transfer',dict(status=value['status'],manifest_sha256=value['manifest_sha256'],result=out.relative_to(ROOT).as_posix(),sha256=h),
         f'## M404 只读探针传输（2026-10-05）\n\nSHA {h}；manifest-first/900B全部载荷回执及完整SHA、bash-n通过。尚未观察或Overlay/模型/FPGA；下一步仅运行一次只读环境探针。')
    print('M404_SENSOR_TRANSFER_SYNC',h)


def decode(text):
    hashes=re.findall(r'(?m)^M404_SENSOR_RESULT_SHA256=([0-9a-f]{64})\s*$',text)
    rows=re.findall(r'(?m)^M404_SENSOR_RESULT_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    if len(hashes)!=1 or not rows or len(rows)!=int(rows[0][1]):raise ValueError('Incomplete catalogue')
    parts=[]
    for i,(index,count,part) in enumerate(rows):
        raw=base64.b64decode(part,validate=True)
        if int(index)!=i or int(count)!=len(rows) or not 0<len(raw)<=900:raise ValueError('Catalogue chunk order/size')
        parts.append(raw)
    raw=b''.join(parts);digest=hashlib.sha256(raw).hexdigest()
    if len(raw)>32768 or digest!=hashes[0]:raise ValueError('Catalogue raw SHA/size')
    r=json.loads(raw)
    if r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or r['status']!='OBSERVED_SENSOR_CATALOGUE_ONLY':raise ValueError('Catalogue identity')
    for k in ('overlay_loaded','cache_changes','numerical_pass','performance_pass','formal_promotion_allowed'):
        if r[k] is not False:raise ValueError('Catalogue scope')
    for k in ('dma_allocations','model_forward_calls','fpga_transactions'):
        if type(r[k]) is not int or r[k]!=0:raise ValueError('Unexpected work')
    c=r['catalogue']
    if len(c['devices'])>16 or len(c['fields'])>128 or not 0<=r['elapsed_s']<=20:raise ValueError('Catalogue budget')
    for k in ('temperature_conversion_performed','driver_sensor_association_proven','throttling_absence_proven'):
        if c[k] is not False:raise ValueError('Unsupported sensor conclusion')
    paths=[]
    for f in c['fields']:
        if f['family'] not in ('hwmon','iio','thermal') or not f['path'].startswith(('/sys/class/hwmon/','/sys/bus/iio/devices/','/sys/class/thermal/')):raise ValueError('Unbounded field')
        if ('raw_text' in f)==('read_error' in f) or len(f.get('raw_text',''))>1024:raise ValueError('Field read evidence differs')
        paths.append(f['path'])
    if len(paths)!=len(set(paths)):raise ValueError('Duplicate fields')
    return digest,raw,r,len(rows)


def collect(path):
    digest,raw,r,chunks=decode(Path(path).read_text(encoding='utf-8-sig'))
    out=BASE/'runs/M404-sensor-board-01/BOARD_RESULT.json';atomic(out,raw,immutable=True)
    sync('latest_m404_sensor_board',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=digest,
         overlay_loaded=False,model_forward_calls=0,performance_pass=False),
         f'## M404 温度接口只读目录（2026-10-05）\n\n原SHA {digest}，{chunks}块≤900B严格回收，固定hwmon/IIO/thermal目录{len(r["catalogue"]["devices"])}设备/{len(r["catalogue"]["fields"])}字段；仅保存名称/原值/路径/driver线索，不计算温度或证明降频。0Overlay/DMA/模型/FPGA；暖协议和旧裁决保持。下一步仅据实际driver身份核对温度单位和转换。')
    print(json.dumps(dict(status=r['status'],sha256=digest,catalogue=r['catalogue']),ensure_ascii=False))


if __name__=='__main__':
    if sys.argv[1:]==['transfer']: transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect': collect(ROOT/sys.argv[2])
    else: raise SystemExit('transfer | collect log')
