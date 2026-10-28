"""Bounded fixed-peer fresh RAM ingress; no model or device access."""
import base64,hashlib,json,os,socket,struct,subprocess,sys,time,traceback
from pathlib import Path,PurePosixPath
BOARD='192.168.0.2';PC='192.168.0.10';PORT=8778
MAGIC=b'M523_M455_P1_INGRESS01\n'
TARGET=Path('/dev/shm/m523_M455_twentytwo_local_package322')
EVIDENCE=Path('/dev/shm/m544_freshboot_current22_ingress05')

def digest(raw):return hashlib.sha256(raw).hexdigest()
def encode(v):return (json.dumps(v,sort_keys=True,separators=(',',':'))+'\n').encode()
def exact(s,n):
    if not 0<=n<=1<<20:raise ValueError('Frame allocation bound')
    b=bytearray(n);v=memoryview(b);o=0
    while o<n:
        k=s.recv_into(v[o:])
        if not k:raise EOFError('Bounded ingress EOF')
        o+=k
    return bytes(b)
def frame(s):return exact(s,struct.unpack('!I',exact(s,4))[0])
def framed(s,b):
    assert len(b)<=1<<20;s.sendall(struct.pack('!I',len(b))+b)
def table(raw,manifest_sha):
    assert 0<len(raw)<=1<<20 and digest(raw)==manifest_sha
    m=json.loads(raw);rows=m['files'];names=[]
    assert 0<len(rows)<=512 and len(rows)==m['file_count'] and 0<m['total_bytes']<=800<<20
    for r in rows:
        p=PurePosixPath(r['path']);assert set(r)=={'path','bytes','sha256'}
        assert not p.is_absolute() and '..' not in p.parts and '\\' not in r['path'] and ':' not in r['path']
        assert p.as_posix()==r['path'] and p.suffix not in ('.pyc','.partial') and '__pycache__' not in p.parts
        assert type(r['bytes']) is int and 0<=r['bytes']<=8<<20
        assert len(r['sha256'])==64 and all(c in '0123456789abcdef' for c in r['sha256'])
        names.append(r['path'])
    assert len(set(names))==len(names) and 'PACKAGE_MANIFEST.json' not in names
    assert sum(r['bytes'] for r in rows)==m['total_bytes']
    return rows
def validate_storage(mem_available,shm_free,required):
    assert type(required)is int and 0<required<=800<<20
    observation=dict(MemAvailable=mem_available,shm_free=shm_free,required_payload_bytes=required,
        minimum_MemAvailable=required+(256<<20),minimum_shm_free=required+(128<<20))
    if mem_available<observation['minimum_MemAvailable'] or shm_free<observation['minimum_shm_free']:
        raise MemoryError('Bounded full22 artifact memory admission: '+json.dumps(observation,sort_keys=True))
    return observation
def storage_admission(target,required):
    assert target.parent==Path('/dev/shm') and not target.exists()
    values={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')}
    info=os.statvfs('/dev/shm')
    return validate_storage(values['MemAvailable'],info.f_bavail*info.f_frsize,required)

def receive(s,target,raw,manifest_sha,started):
    rows=table(raw,manifest_sha);assert target.is_absolute() and not target.exists()
    admitted=storage_admission(target,sum(r['bytes'] for r in rows));target.mkdir()
    (target/'PACKAGE_MANIFEST.json').write_bytes(raw)
    for r in rows:
        assert frame(s)==encode(r) and time.monotonic()-started<600
        p=target/r['path'];p.parent.mkdir(parents=True,exist_ok=True);part=p.with_name(p.name+'.partial')
        left=r['bytes'];h=hashlib.sha256()
        with part.open('xb') as f:
            while left:
                assert time.monotonic()-started<600
                b=exact(s,min(left,1<<20));f.write(b);h.update(b);left-=len(b)
            f.flush();os.fsync(f.fileno())
        assert h.hexdigest()==r['sha256'] and not p.exists();os.rename(part,p)
    assert {p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()}=={r['path'] for r in rows}|{'PACKAGE_MANIFEST.json'}
    assert all(not p.is_symlink() and p.stat().st_nlink==1 for p in target.rglob('*') if p.is_file())
    framed(s,b'ALL_MEMBERS_SHA_VERIFIED')
    return dict(file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows),manifest_sha256=manifest_sha,storage_admission=admitted)
def ip(*a):return json.loads(subprocess.run(['ip','-j',*a],check=True,capture_output=True,text=True,timeout=10).stdout)
def addresses(links):return sorted((a['family'],a['local'],a['prefixlen']) for link in links for a in link['addr_info'])
def serve(self_sha,manifest_sha):
    assert os.geteuid()==0 and digest(Path(__file__).read_bytes())==self_sha and not EVIDENCE.exists() and not TARGET.exists()
    EVIDENCE.mkdir();v=dict(status='FAIL_FRESH_M455_P1_INGRESS',primary_rc=1,errors=[],hardware_actions=0,model_runs=0,
        source_sha256=self_sha,target=str(TARGET),manifest_sha256=manifest_sha,temporary_address_restored=False)
    before=routes=None;added=False;started=time.monotonic()
    try:
        assert Path('/sys/class/net/eth0/carrier').read_text().strip()=='1'
        before=ip('addr','show','dev','eth0');routes=ip('route','show','default')
        v.update(addresses_before=before,default_routes_before=routes)
        present=any(a.get('local')==BOARD and a.get('prefixlen')==24 for link in before for a in link['addr_info'])
        if not present:
            assert not any(a.get('local')==BOARD for link in before for a in link['addr_info'])
            subprocess.run(['ip','addr','add',BOARD+'/24','dev','eth0'],check=True,timeout=10);added=True
        assert ip('route','show','default')==routes
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);listener.bind((BOARD,PORT));listener.listen(1);listener.settimeout(60)
            print('M523_M455_P1_INGRESS_READY',flush=True);s,peer=listener.accept()
        with s:
            s.settimeout(20);assert peer[0]==PC and exact(s,len(MAGIC))==MAGIC
            v['received']=receive(s,TARGET,frame(s),manifest_sha,started)
        v.update(status='PASS_FRESH_M455_P1_INGRESS_ONLY',primary_rc=0)
    except BaseException:v['errors'].append(traceback.format_exc())
    finally:
        try:
            if added:subprocess.run(['ip','addr','del',BOARD+'/24','dev','eth0'],check=True,timeout=10)
            if before is not None:
                after=ip('addr','show','dev','eth0');final=ip('route','show','default')
                v.update(addresses_after=after,default_routes_after=final,
                    temporary_address_restored=addresses(after)==addresses(before) and final==routes)
        except BaseException:v['errors'].append(traceback.format_exc())
        if v['errors'] or not v['temporary_address_restored']:v.update(status='FAIL_FRESH_M455_P1_INGRESS',primary_rc=1)
        raw=encode(v)
        with (EVIDENCE/'BOARD_RESULT.json').open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        print('M523_B0_RESULT_SHA256='+digest(raw),flush=True)
        pieces=[raw[i:i+480] for i in range(0,len(raw),480)]
        for i,b in enumerate(pieces):print('M523_B0_RESULT_PART='+str(i)+'/'+str(len(pieces))+':'+base64.b64encode(b).decode(),flush=True);time.sleep(.01)
    return v['primary_rc']
def send(pkg,manifest_sha):
    raw=(pkg/'PACKAGE_MANIFEST.json').read_bytes();rows=table(raw,manifest_sha)
    with socket.create_connection((BOARD,PORT),timeout=15,source_address=(PC,0)) as s:
        s.settimeout(20);s.sendall(MAGIC);framed(s,raw)
        for r in rows:
            p=pkg/r['path'];assert p.stat().st_size==r['bytes'] and digest(p.read_bytes())==r['sha256']
            framed(s,encode(r))
            with p.open('rb') as f:
                for b in iter(lambda:f.read(1<<20),b''):s.sendall(b)
        assert frame(s)==b'ALL_MEMBERS_SHA_VERIFIED'
    return dict(manifest_sha256=manifest_sha,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))
if __name__=='__main__':raise SystemExit(serve(sys.argv[1],sys.argv[2]))
