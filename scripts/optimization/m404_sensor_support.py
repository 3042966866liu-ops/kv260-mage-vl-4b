"""Bounded catalogue control and strict raw collection; no board invocation."""
import ast
import base64
from contextlib import redirect_stdout
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from m351_workflow import ROOT, BASE, HERE, sha, atomic, encoded, sync
from m404_sensor_prepare import PKG


def rename(text):
    return text.replace('M404-environment-observer','M404-sensor-catalogue').replace(
        'm404_environment_observer_candidate','m404_sensor_catalogue_candidate').replace(
        'm404_environment','m404_sensor').replace('M404-environment','M404-sensor').replace(
        'M404_ENV','M404_SENSOR').replace('m404env','m404sensor').replace('READONLY_ENV','READONLY_SENSOR')


DECODER='''def decode(text):
    hashes=re.findall(r'(?m)^M404_SENSOR_RESULT_SHA256=([0-9a-f]{64})\\s*$',text)
    rows=re.findall(r'(?m)^M404_SENSOR_RESULT_CHUNK=(\\d+)/(\\d+):([A-Za-z0-9+/=]+)\\s*$',text)
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
'''


COLLECT='''def collect(path):
    digest,raw,r,chunks=decode(Path(path).read_text(encoding='utf-8-sig'))
    out=BASE/'runs/M404-sensor-board-01/BOARD_RESULT.json';atomic(out,raw,immutable=True)
    sync('latest_m404_sensor_board',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=digest,
         overlay_loaded=False,model_forward_calls=0,performance_pass=False),
         f'## M404 温度接口只读目录（2026-10-05）\\n\\n原SHA {digest}，{chunks}块≤900B严格回收，固定hwmon/IIO/thermal目录{len(r["catalogue"]["devices"])}设备/{len(r["catalogue"]["fields"])}字段；仅保存名称/原值/路径/driver线索，不计算温度或证明降频。0Overlay/DMA/模型/FPGA；暖协议和旧裁决保持。下一步仅据实际driver身份核对温度单位和转换。')
    print(json.dumps(dict(status=r['status'],sha256=digest,catalogue=r['catalogue']),ensure_ascii=False))
'''


def export_fixture(r):
    raw=encoded(r);parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    return 'M404_SENSOR_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\n'+''.join(
        f'M404_SENSOR_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode()+'\n' for i,p in enumerate(parts))


def main():
    workflow=rename((HERE/'m404_environment_workflow.py').read_text(encoding='utf-8'))
    start=workflow.index('def decode(');end=workflow.index("\n\nif __name__",start)
    workflow=workflow[:start]+DECODER+'\n\n'+COLLECT+workflow[end:]
    atomic(HERE/'m404_sensor_workflow.py',workflow.encode('utf-8'),immutable=True)
    control=rename((HERE/'m404_environment_control.ps1').read_text(encoding='utf-8'))
    atomic(HERE/'m404_sensor_control.ps1',control.encode('utf-8'),immutable=True)
    ast.parse(workflow,feature_version=(3,10))
    import m404_sensor_workflow as w
    spec=importlib.util.spec_from_file_location('m404_actual_catalogue',PKG/'m404_sensor_inventory.py')
    p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp/m404sensor') as d:
        root=Path(d);p.OUT=root/'saved/RESULT.json'
        p.os=SimpleNamespace(geteuid=lambda:0,uname=lambda:['Linux','fake','fake-kernel','fake','aarch64'],fsync=__import__('os').fsync,replace=__import__('os').replace)
        p.gather=lambda:dict(devices=[],fields=[],temperature_conversion_performed=False,driver_sensor_association_proven=False,throttling_absence_proven=False)
        argv=sys.argv
        try:
            sys.argv=['probe',sha(PKG/'PACKAGE_MANIFEST.json'),'--enable-readonly-catalogue'];capture=io.StringIO()
            with redirect_stdout(capture):assert p.main()==0
            _,raw,r,_=w.decode(capture.getvalue());assert raw==p.OUT.read_bytes()
            try:p.main()
            except RuntimeError:pass
            else:raise AssertionError('Immutable catalogue overwritten')
            sys.argv=['probe','Collect'];capture=io.StringIO()
            with redirect_stdout(capture):assert p.main()==0
            assert w.decode(capture.getvalue())[1]==raw
        finally:sys.argv=argv
        bad=[]
        for k,v in [('manifest_sha256','bad'),('performance_pass',True),('dma_allocations',True),('model_forward_calls',1),('status','PASS'),('elapsed_s',21)]:
            q=copy.deepcopy(r);q[k]=v;bad.append(export_fixture(q))
        for k in ('temperature_conversion_performed','throttling_absence_proven','driver_sensor_association_proven'):
            q=copy.deepcopy(r);q['catalogue'][k]=True;bad.append(export_fixture(q))
        q=copy.deepcopy(r);q['catalogue']['fields']=[dict(path='/etc/passwd',family='hwmon',raw_text='fake')];bad.append(export_fixture(q))
        valid=export_fixture(r);bad+=[valid+valid.splitlines(True)[0],valid.replace('CHUNK=0/','CHUNK=2/')]
        for text in bad:
            try:w.decode(text)
            except (ValueError,KeyError,TypeError):pass
            else:raise AssertionError('Invalid catalogue accepted')
        # Reuse the actual receipt/atomic/sync test with exact new schema and paths.
        import inspect
        import m404_environment_support as old
        code=inspect.getsource(old.main)
        start=code.index('        saved=(workflow.ROOT');end=code.index('    ps=Path(',start)
        region=rename(code[start:end])
        wrapper='def transfer_check():\n    with tempfile.TemporaryDirectory(dir=ROOT/"tmp/m404sensor") as d:\n        directory=Path(d)\n'+region
        namespace=dict(globals(),workflow=w,valid=valid)
        exec(compile(wrapper,'<actual-sensor-transfer-check>','exec'),namespace)
        namespace['transfer_check']()
    ps=Path(r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe')
    checked=subprocess.run([str(ps),'-NoProfile','-File',str(HERE/'m404_sensor_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8',check=True)
    assert 'M404_SENSOR_CONTROL_SYNTAX_PASS' in checked.stdout
    value=dict(status='PASS_OFFLINE_SENSOR_CATALOGUE_CONTROL_COLLECTION',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),
               actual_probe_export_and_collect=True,immutable=True,actual_transfer_all4_files=True,missing_receipt_refused=True,
               collector_negative_checks=len(bad),atomic_destination_sync_keys_checked=True,board_run=False,performance_pass=False,
               source_sha256={n:sha(HERE/n) for n in ('m404_sensor_control.ps1','m404_sensor_workflow.py','m404_sensor_support.py')})
    out=BASE/'runs/M404-sensor-support-01/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    sync('latest_m404_sensor_support',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=h,manifest_sha256=value['manifest_sha256']),
         f'## M404 温度目录控制/回收（2026-10-05）\n\nSHA {h}；实际producer/Collect原字节、immutable、{len(bad)}回收拒绝、实际4文件回执/缺失拒绝及保存目标/同步键检查通过。明确fake catalogue，仅L0；下一步同COM3一次只读目录，无模型/Overlay。')
    print(json.dumps(value|dict(sha256=h)))


if __name__=='__main__':main()
