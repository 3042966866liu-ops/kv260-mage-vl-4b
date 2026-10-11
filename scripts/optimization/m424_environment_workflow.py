"""Strict readonly environment receipts and immutable original-byte recovery."""
import base64,hashlib,json,re
from pathlib import Path
from m351_workflow import ROOT,BASE,HERE,sha,atomic,encoded,sync
PKG=BASE/'candidates/M424-environment-probe-01'
FOLDER=ROOT/'tmp/m424environment01'
OUT=BASE/'runs/M424-environment-board-01/BOARD_RESULT.json'


def decode(text):
    hashes=re.findall(r'(?m)^M424_ENV_SHA256=([0-9a-f]{64})\s*$',text)
    chunks=re.findall(r'(?m)^M424_ENV_CHUNK=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text)
    if len(hashes)!=1 or not chunks or len(chunks)!=int(chunks[0][1]):raise ValueError('Incomplete/duplicate result')
    parts=[]
    for i,(n,count,b64) in enumerate(chunks):
        p=base64.b64decode(b64,validate=True)
        if int(n)!=i or int(count)!=len(chunks) or not 0<len(p)<=900:raise ValueError('Chunk order/size')
        parts.append(p)
    raw=b''.join(parts);h=hashlib.sha256(raw).hexdigest()
    if h!=hashes[0] or len(raw)>32768:raise ValueError('Full SHA/size')
    r=json.loads(raw)
    if r['manifest_sha256']!=sha(PKG/'PACKAGE_MANIFEST.json') or type(r['gate_return_code']) is not int or r['gate_return_code'] not in (0,1):raise ValueError('Manifest/rc')
    for k in ('overlay_loaded','cache_changes','performance_pass','throttling_absence_proven'):
        if r[k] is not False:raise ValueError('Scope changed')
    for k in ('model_forward_calls','dma_allocations','fpga_transactions'):
        if type(r[k]) is not int or r[k]!=0:raise ValueError('Unexpected hardware/model work')
    if not 0<=r['elapsed_s']<=15:raise ValueError('Observation budget')
    if r['status']=='PASS_M424_READONLY_ENVIRONMENT_OBSERVABLE':
        e=r['environment']
        if r['gate_return_code'] or r['errors'] or e['observability_issues'] or e['temperature_channel_mapping_proven'] is not False:raise ValueError('PASS missing proof')
        from m404_warm_conditions import environment_issues
        if environment_issues(e):raise ValueError('Environment incomplete')
        expected=json.loads((PKG/'AMS_EXPECTED.json').read_bytes())
        if set(e['thermal_zones'])!={'ams/'+n for n in expected['inputs']}:raise ValueError('Channels differ')
        for name in expected['inputs']:
            t=e['thermal_zones']['ams/'+name]
            if t['source']!=expected['path']+'/'+name or t['resolved_path']!=expected['resolved_path']+'/'+name or t['units']!='millidegree_Celsius' or t['anatomical_channel_mapping_proven'] is not False:raise ValueError('Processed sensor identity differs')
    elif r['status']=='FAIL_M424_ENVIRONMENT_OBSERVABILITY':
        if r['gate_return_code']!=1 or not r['errors']:raise ValueError('Failure missing rc/error')
    else:raise ValueError('Unknown status')
    done=re.findall(r'M424_ENV_DONE gate_rc=(\d+)',text)
    if done and done!=[str(r['gate_return_code'])]:raise ValueError('Runner lost original rc')
    return h,raw,r,len(chunks)


def transfer():
    m=json.loads((PKG/'PACKAGE_MANIFEST.json').read_bytes());receipts=[]
    for name in ['PACKAGE_MANIFEST.json']+[x['path'] for x in m['files']]:
        prefix='upload_'+name.replace('.','_');size=(PKG/name).stat().st_size;count=(size+899)//900
        p=FOLDER/(prefix+'_final.log');text=p.read_text(encoding='utf-8-sig')
        if 'M212_CHUNKED_FILE_PASS' not in text or sha(PKG/name) not in text:raise ValueError('Transfer SHA missing')
        chunks=sorted(FOLDER.glob(prefix+'_chunk_*.log'))
        if len(chunks)!=count:raise ValueError('Receipt count')
        for i,p in enumerate(chunks,1):
            if not re.search(r'M212_CHUNK_PASS\s+'+str(i)+r'\s+'+str(count)+r'\s+'+str(min(i*900,size))+r'\s',p.read_text(encoding='utf-8-sig')):raise ValueError('Receipt order')
        receipts.append(dict(path=name,sha256=sha(PKG/name),chunks=count))
    if '__M424_ENV_SYNTAX_RC_0__' not in (FOLDER/'syntax.log').read_text(encoding='utf-8-sig'):raise ValueError('bash-n failed')
    v=dict(status='PASS_M424_READONLY_ENVIRONMENT_TRANSFER',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),receipts=receipts,board_run=False)
    p=BASE/'runs/M424-environment-transfer-01/RESULT.json';atomic(p,encoded(v),immutable=True)
    sync('latest_m424_environment_transfer',dict(status=v['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=v['manifest_sha256']),
         f'## M424 已处理温度观察包传输（2026-10-06）\n\nSHA {sha(p)}；manifest-first900B全部回执/逐SHA/bash-n通过。尚未观察；0Overlay/推理。')
    print('M424_ENV_TRANSFER_SYNC',sha(p))


def collect(log):
    h,raw,r,count=decode(Path(log).read_text(encoding='utf-8-sig'));atomic(OUT,raw,immutable=True)
    sync('latest_m424_environment_board',dict(status=r['status'],result=OUT.relative_to(ROOT).as_posix(),sha256=h,manifest_sha256=r['manifest_sha256'],performance_pass=False,board_run=True),
         f'## M424 AMS温度与暖态环境只读观察（2026-10-06）\n\n原SHA {h}，{count}个900B以内原分块整SHA回收，rc{r["gate_return_code"]}，{r["status"]}。'
         '0Overlay/DMA/模型/FPGA；固定ams/iio_hwmon三processed温度按毫摄氏度读取，不猜PS/PL编号、不ADC转换。'
         '这是环境可观测性，不是正式请求暖态/无瞬时降频/性能PASS；三记录同步后仅准备完整请求轻量入口。')
    print('M424_ENV_RESULT_SYNC',h,r['status'])


if __name__=='__main__':
    import sys
    if sys.argv[1:]==['transfer']:transfer()
    elif len(sys.argv)==3 and sys.argv[1]=='collect':collect(sys.argv[2])
    else:raise SystemExit('transfer | collect LOG')
