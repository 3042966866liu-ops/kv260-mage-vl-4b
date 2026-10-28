"""Close the new lower-gate transport and reject the first runner argument bug."""
import ast,base64,contextlib,hashlib,io,json,socket,sys,threading,time,zlib
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];H=Path(__file__).resolve().parent
sys.path[:0]=[str(H),str(ROOT/'experiments/speed_target_30s_20261020')]
from prepare_adaptive522 import R,read,save,sha,synchronized
from m441_host_io08 import atomic
import M455_P1_ingress52302 as transport
import M455_P1_shape52301 as native

def decode_shape(text):
    import re
    raw_shas=re.findall(r'^M523_SHAPE_RAW_SHA256=([0-9a-f]{64})\s*$',text,re.M)
    z_shas=re.findall(r'^M523_SHAPE_Z_SHA256=([0-9a-f]{64})\s*$',text,re.M)
    parts=re.findall(r'^M523_SHAPE_Z_PART=(\d+)/(\d+):([A-Za-z0-9+/=]+)\s*$',text,re.M)
    assert len(raw_shas)==len(z_shas)==1 and parts and len(parts)<=10000
    count=int(parts[0][1]);assert len(parts)==count and [int(p[0]) for p in parts]==list(range(count))
    assert all(int(p[1])==count for p in parts)
    z=b''.join(base64.b64decode(p[2],validate=True) for p in parts)
    assert len(z)<=4<<20 and hashlib.sha256(z).hexdigest()==z_shas[0]
    d=zlib.decompressobj();raw=d.decompress(z,(4<<20)+1)
    assert len(raw)<=4<<20 and d.eof and not d.unused_data and not d.unconsumed_tail
    assert hashlib.sha256(raw).hexdigest()==raw_shas[0]
    return json.loads(raw),raw

def tests(out):
    fixture=out/'saved_emit.json';save(fixture,dict(primary_rc=0,status='COMPONENT',rows=[dict(i=i,text='保存原字节') for i in range(1000)]))
    f=io.StringIO()
    with contextlib.redirect_stdout(f):native.emit(fixture)
    text=f.getvalue();v,raw=decode_shape(text);assert raw==fixture.read_bytes()
    rejected=[]
    lines=text.splitlines();parts=[s for s in lines if s.startswith('M523_SHAPE_Z_PART=')]
    for label,changed in [('missing',text.replace(parts[0]+'\n','')),('duplicate',text+parts[0]+'\n'),
        ('wrong_raw_hash',text.replace(sha(fixture),'0'*64)),('reordered','\n'.join(lines[:2]+list(reversed(parts)))+'\n')]:
        try:decode_shape(changed)
        except (AssertionError,ValueError):rejected.append(label)
        else:raise AssertionError(label)
    payload=b'exact ingress test\n'*200;rows=[dict(path='sub/file.bin',bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())]
    manifest=transport.encode(dict(files=rows,file_count=1,total_bytes=len(payload)));msha=hashlib.sha256(manifest).hexdigest()
    for label,changed in [('absolute','/outside'),('traversal','../outside'),('backslash','sub\\outside')]:
        r=[dict(rows[0],path=changed)];b=transport.encode(dict(files=r,file_count=1,total_bytes=len(payload)))
        try:transport.table(b,hashlib.sha256(b).hexdigest())
        except AssertionError:rejected.append(label)
        else:raise AssertionError(label)
    for corrupt in (False,True):
        target=out/('received_bad' if corrupt else 'received_good');errors=[]
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(5)
        def receiver():
            try:
                s,_=listener.accept()
                with s:s.settimeout(3);transport.receive(s,target,manifest,msha,time.monotonic())
            except BaseException as e:errors.append(type(e).__name__)
            finally:listener.close()
        t=threading.Thread(target=receiver,daemon=True);t.start()
        with socket.create_connection(listener.getsockname(),timeout=3) as s:
            transport.framed(s,transport.encode(rows[0]));s.sendall(payload if not corrupt else payload[:-1]+b'!')
            if not corrupt:assert transport.frame(s)==b'ALL_MEMBERS_SHA_VERIFIED'
        t.join(5);assert not t.is_alive()
        if corrupt:assert errors==['AssertionError'] and not (target/'sub/file.bin').exists();rejected.append('wrong_payload_SHA')
        else:assert not errors and (target/'sub/file.bin').read_bytes()==payload
    return dict(actual_zlib_emitter_decoder_original_bytes_equal=True,rejected=rejected,
        actual_local_socket_good_and_bad_SHA=True,no_UART_or_board_network=True)

def main():
    out=R/'M523-M455-P1-shape-preparation-03';assert not out.exists();out.mkdir()
    component=tests(out)
    old=R.parent/'candidates/M523-M455-P1-shape-01';prior=R/'M523-M455-P1-shape-preparation-01/RESULT.json';p=read(prior)
    assert sha(old/'PACKAGE_MANIFEST.json')==p['manifest_sha256']
    pkg=R.parent/'candidates/M523-M455-P1-shape-03';assert not pkg.exists();pkg.mkdir()
    for r in read(old/'PACKAGE_MANIFEST.json')['files']:
        src=old/r['path'];assert src.stat().st_size==r['bytes'] and sha(src)==r['sha256']
        raw=src.read_bytes()
        if r['path']=='run.sh':
            s=raw.decode();a='[[ $EUID == 0 && $# -ge 3 && $# -le 4 ]]';b='[[ $EUID == 0 && ( $# == 3 || $# == 5 ) ]]'
            assert s.count(a)==1;s=s.replace(a,b);raw=s.encode()
        atomic(pkg/r['path'],raw,immutable=True)
    rows=[dict(path=q.relative_to(pkg).as_posix(),bytes=q.stat().st_size,sha256=sha(q)) for q in sorted(pkg.rglob('*')) if q.is_file()]
    save(pkg/'PACKAGE_MANIFEST.json',dict(files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows)))
    for source in (H/'M455_P1_ingress52302.py',Path(__file__)):ast.parse(source.read_text(encoding='utf-8'),feature_version=(3,10))
    result=dict(status='SEALED_M455_P1_LOWER_CONTROL_TRANSPORT_COMPONENTS_ONLY',source_sha256=sha(__file__),
        prior_preparation_sha256=sha(prior),package=pkg.relative_to(ROOT).as_posix(),manifest_sha256=sha(pkg/'PACKAGE_MANIFEST.json'),
        runner_sha256=sha(pkg/'run.sh'),ingress_source_sha256=sha(H/'M455_P1_ingress52302.py'),
        native_shape_source_sha256=sha(pkg/'M455_P1_shape52301.py'),component=component,
        rejected_01='Runner accepted at most4 arguments but prior-sha requires5 including runner hash; found before upload or hardware. Original01 preserved.',
        only_package_change='run.sh argument arity3 or5; native lifecycle/math/fixtures unchanged',
        local_socket_failure_sha256=sha(R/'M523-M455-P1-shape-preparation-02/FAILED_PREPARATION.json'),
        original_CPU_lifecycle_checks=p['CPU_lifecycle_checks'],board_actions=0,model_runs=0)
    save(out/'RESULT.json',result);h=sha(out/'RESULT.json')
    synchronized('latest_m523_M455_P1_shape_preparation02',dict(status=result['status'],result=(out/'RESULT.json').relative_to(ROOT).as_posix(),sha256=h,board=False),
        '## M523 P1最小板测控制与固定peer新RAM传输组件\n\nRESULT SHA '+h+'；实际压缩emitter/decoder原字节及缺块/重复/乱序/SHA拒绝、本机socket完整复制/坏SHA不落正式文件/路径拒绝通过。01 runner前级SHA参数需要5项但只允4项，上传前发现原保留；02仅改3或5参数，native生命周期/七owner/夹具不变。尚未新Overlay/板端，下一实际COM3传输、纯导入后Build级。')
    print('M455_P1_SHAPE_CONTROL_SEALED',h,result['manifest_sha256'],flush=True)

if __name__=='__main__':main()
