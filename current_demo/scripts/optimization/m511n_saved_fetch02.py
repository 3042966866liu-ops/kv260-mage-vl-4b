"""Specific-peer read-only saved binary fetch; no FPGA imports or execution.

PC still initiates 192.168.0.10 -> board192.168.0.2:8777. Only an added
temporary board address is removed. Original addresses/defaults are preserved.
"""
import argparse,hashlib,json,os,socket,struct,subprocess,time
from pathlib import Path,PurePosixPath
MAGIC=b'TELLME_M511N_SAVED02\n';BOARD='192.168.0.2';PC='192.168.0.10';PORT=8777
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def encode(v):return (json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
def exact(s,n):
    if not 0<=n<=1<<20:raise ValueError('Read allocation bound')
    b=bytearray(n);v=memoryview(b);i=0
    while i<n:
        k=s.recv_into(v[i:])
        if not k:raise EOFError('Saved transfer EOF')
        i+=k
    return b
def framed(s,b):
    if len(b)>1<<20:raise ValueError('Frame bound')
    s.sendall(struct.pack('!I',len(b))+b)
def frame(s):return bytes(exact(s,struct.unpack('!I',exact(s,4))[0]))
def rows_for(raw,digest,level):
    if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Exact original raw SHA')
    r=json.loads(raw)
    if r['gate_level']!=level or r['status']!='PASS_M511N_'+level.upper() or r['gate_return_code']!=0 or r['safe_buffers_released'] is not True or r['unsafe_dma_buffers_retained'] is not False:raise ValueError('Only safely ended PASS binaries')
    rows=r['raw_files']
    if not 0<len(rows)<=64 or len({x['path'] for x in rows})!=len(rows) or not 0<sum(x['bytes'] for x in rows)<=24<<20:raise ValueError('File count/total bound')
    for x in rows:
        n=x['path'];p=PurePosixPath(n)
        if p.is_absolute() or '..' in p.parts or '\\' in n or ':' in n or n!=p.as_posix() or not n.endswith('.bin') or type(x['bytes']) is not int or not 0<x['bytes']<=2<<20 or len(x['sha256'])!=64:raise ValueError('Saved member identity/path')
    return rows
def ip(*args):return json.loads(subprocess.run(['ip','-j',*args],capture_output=True,text=True,check=True,timeout=10).stdout)
def addresses(links):return sorted((x['family'],x['local'],x['prefixlen']) for link in links for x in link['addr_info'])
def serve(level,digest,self_sha):
    if os.geteuid()!=0 or sha(Path(__file__))!=self_sha:raise RuntimeError('Root exact exporter source required')
    root=Path('/home/ubuntu/m511n_width_evidence_01')/level;raw=(root/'BOARD_RESULT.json').read_bytes();rows=rows_for(raw,digest,level)
    evidence=root/'saved_fetch01_RESULT.json'
    if evidence.exists():raise RuntimeError('Original saved fetch exists; no duplicate attempt')
    r=dict(status='FAIL_M511N_SAVED_FETCH02',raw_sha256=digest,source_sha256=self_sha,board_gate_executed=False,overlay_loaded=False,fpga_transactions=0,files=[],errors=[],added_address=False,temporary_address_restored=False)
    before=routes=None;added=False;connection=None;started=time.monotonic()
    try:
        if Path('/sys/class/net/eth0/carrier').read_text().strip()!='1':raise RuntimeError('Ethernet carrier absent')
        before=ip('addr','show','dev','eth0');routes=ip('route','show','default');r.update(addresses_before=before,default_routes_before=routes)
        present=any(x.get('local')==BOARD and x.get('prefixlen')==24 for l in before for x in l['addr_info'])
        if not present:
            if any(x.get('local')==BOARD for l in before for x in l['addr_info']):raise RuntimeError('Existing address prefix differs')
            subprocess.run(['ip','addr','add',BOARD+'/24','dev','eth0'],check=True,timeout=10);added=True;r['added_address']=True
        if ip('route','show','default')!=routes:raise RuntimeError('Default route changed')
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);listener.bind((BOARD,PORT));listener.listen(1);listener.settimeout(90);print('M511N_SAVED_FETCH02_READY',flush=True);connection,peer=listener.accept()
        connection.settimeout(20)
        if peer[0]!=PC or bytes(exact(connection,len(MAGIC)))!=MAGIC or frame(connection).decode()!=digest:raise ValueError('Specific peer/proof differs')
        framed(connection,encode(dict(raw_sha256=digest,files=rows)))
        for x in rows:
            p=root/x['path'];p.resolve().relative_to(root.resolve())
            if p.is_symlink() or p.stat().st_size!=x['bytes'] or sha(p)!=x['sha256']:raise ValueError('Saved source SHA differs')
            framed(connection,encode(x));sent=0;h=hashlib.sha256()
            with p.open('rb') as f:
                for b in iter(lambda:f.read(1<<20),b''):
                    if time.monotonic()-started>300:raise TimeoutError('Total export budget')
                    connection.sendall(b);h.update(b);sent+=len(b)
            if sent!=x['bytes'] or h.hexdigest()!=x['sha256'] or sha(p)!=x['sha256']:raise ValueError('Saved source changed')
            r['files'].append(x)
        if frame(connection)!=b'FILES_VERIFIED':raise ValueError('PC did not verify all bytes')
        r['status']='PASS_M511N_SAVED_FETCH02'
    except BaseException as e:r['errors'].append(type(e).__name__+': '+str(e))
    finally:
        if added:
            try:subprocess.run(['ip','addr','del',BOARD+'/24','dev','eth0'],check=True,timeout=10)
            except BaseException as e:r['errors'].append('Address restoration: '+str(e))
        if before is not None:
            try:
                after=ip('addr','show','dev','eth0');route_after=ip('route','show','default');r.update(addresses_after=after,default_routes_after=route_after,temporary_address_restored=addresses(before)==addresses(after) and routes==route_after)
            except BaseException as e:r['errors'].append('Network readback: '+str(e))
        if r['errors'] or not r['temporary_address_restored']:r['status']='FAIL_M511N_SAVED_FETCH02'
        r['elapsed_s']=time.monotonic()-started;b=encode(r);evidence.write_bytes(b)
        if connection is not None:
            # Address has already been restored. Never depend on another TCP
            # response here; the final saved proof is exported through COM3.
            connection.close()
        # Small whole saved result, not the potentially many-MB binary payload.
        import base64
        print('M511N_FETCH_RAW_SHA256='+hashlib.sha256(b).hexdigest(),flush=True)
        for i in range(0,len(b),900):print('M511N_FETCH_RAW_PART='+base64.b64encode(b[i:i+900]).decode(),flush=True)
    return int(r['status']!='PASS_M511N_SAVED_FETCH02')
def fetch(raw,digest,level,out,endpoint=None):
    rows=rows_for(raw,digest,level)
    if out.exists():raise RuntimeError('Saved receive directory exists')
    out.mkdir(parents=True);started=time.monotonic()
    with socket.create_connection(endpoint or (BOARD,PORT),timeout=20,source_address=(PC,0) if endpoint is None else None) as s:
        s.settimeout(20);s.sendall(MAGIC);framed(s,digest.encode());spec=json.loads(frame(s))
        if spec!=dict(raw_sha256=digest,files=rows):raise ValueError('Frozen complete file table differs')
        for x in rows:
            if json.loads(frame(s))!=x:raise ValueError('Actual member order differs')
            p=out/x['path'];p.parent.mkdir(parents=True,exist_ok=True);left=x['bytes'];h=hashlib.sha256()
            with p.open('xb') as f:
                while left:
                    if time.monotonic()-started>300:raise TimeoutError('Total receive budget')
                    b=exact(s,min(left,1<<20));f.write(b);h.update(b);left-=len(b)
            if sha(p)!=x['sha256'] or h.hexdigest()!=x['sha256']:raise ValueError('Actual complete binary SHA differs')
        framed(s,b'FILES_VERIFIED')
        r=dict(status='PC_BYTES_VERIFIED_AWAITING_COM3_NETWORK_CLOSURE',raw_sha256=digest,files=rows)
        (out/'PC_RECEIPT.json').write_bytes(encode(r))
    return r
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('serve','fetch'));ap.add_argument('level',choices=('BuildID','Descriptor','Chain','Layer','Timing'));ap.add_argument('raw_sha');ap.add_argument('--self-sha');ap.add_argument('--raw',type=Path);ap.add_argument('--out',type=Path);a=ap.parse_args()
    if a.mode=='serve':raise SystemExit(serve(a.level,a.raw_sha,a.self_sha))
    if a.raw is None or a.out is None:raise ValueError('Explicit saved raw/output paths')
    fetch(a.raw.read_bytes(),a.raw_sha,a.level,a.out)
