"""M544 data-only UART protocol. No shell, device API, file writes or model calls."""
import base64,hashlib,io,json,math,re,secrets,select,sys,time,zlib
from collections import OrderedDict
import numpy as np
MAX_LINE=1024;MAX_COMPRESSED=1<<20;MAX_RAW=612000;CHUNK=512
def digest(b):return hashlib.sha256(b).hexdigest()
def hexstr(v,n):return isinstance(v,str) and re.fullmatch('[0-9a-f]{'+str(n)+'}',v) is not None
def caseid(v):return isinstance(v,str) and re.fullmatch('u[0-9a-f]{32}_f0',v) is not None
def parse(line):
    if not isinstance(line,str) or not 1<=len(line.encode())<=MAX_LINE:raise ValueError('Bounded UART data line required')
    v=json.loads(line)
    if not isinstance(v,dict):raise ValueError('JSON object required')
    return v
def check_frame(v,nonce):
    fields={'action','nonce','id','case_id','frame_sha256','pixel_sha256','video_sha256','upload_id','timestamp_ms','compressed_bytes','compressed_sha256','file_bytes'}
    if set(v)!=fields or v['action']!='frame' or v['nonce']!=nonce:raise ValueError('Frame metadata or nonce differs')
    if not hexstr(v['id'],32) or not hexstr(v['upload_id'],32) or not caseid(v['case_id']) or not v['case_id'].startswith('u'+v['upload_id']+'_'):raise ValueError('Frame identity invalid')
    if not all(hexstr(v[k],64) for k in ['frame_sha256','pixel_sha256','video_sha256','compressed_sha256']):raise ValueError('Frame SHA invalid')
    if type(v['compressed_bytes']) is not int or not 0<v['compressed_bytes']<=MAX_COMPRESSED or type(v['file_bytes']) is not int or v['file_bytes']!=602240:raise ValueError('Frame byte bound differs')
    t=v['timestamp_ms']
    if type(t) not in (int,float) or not math.isfinite(t) or not 0<=t<=3600000:raise ValueError('Frame timestamp invalid')
    return v
def decode_frame(v,payload):
    if len(payload)!=v['compressed_bytes'] or digest(payload)!=v['compressed_sha256']:raise ValueError('Compressed frame differs')
    d=zlib.decompressobj();plain=d.decompress(payload,MAX_RAW+1)
    if len(plain)!=v['file_bytes'] or not d.eof or d.unconsumed_tail or d.unused_data or digest(plain)!=v['frame_sha256']:raise ValueError('Exact bounded NPY required')
    a=np.load(io.BytesIO(plain),allow_pickle=False)
    if a.shape!=(448,448,3) or a.dtype!=np.uint8 or not a.flags.c_contiguous or digest(a.tobytes())!=v['pixel_sha256']:raise ValueError('RGB shape/dtype/pixel SHA differs')
    return a
def check_chunk(v,identity,seq):
    if set(v)!={'action','id','seq','data'} or v['action']!='chunk' or v['id']!=identity or type(v['seq']) is not int or v['seq']!=seq:raise ValueError('Frame chunk sequence differs')
    b=base64.b64decode(v['data'],validate=True)
    if not 0<len(b)<=CHUNK:raise ValueError('Chunk byte bound differs')
    return b
def emit(kind,v):
    raw=json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    if len(raw)>32768:raise ValueError('Oversize response')
    print('M544_'+kind+' '+digest(raw)+' '+base64.b64encode(zlib.compress(raw,9)).decode(),flush=True)
def read_line(timeout):
    if not select.select([sys.stdin],[],[],timeout)[0]:raise TimeoutError('Data-only input timeout')
    line=sys.stdin.readline(MAX_LINE+1)
    if not line:raise EOFError('Data-only input EOF')
    return parse(line)
class Channel:
    def __init__(self,manifest,session,maximum=12,idle_seconds=21600):
        assert hexstr(manifest,64) and hexstr(session,32) and maximum==12 and idle_seconds==21600
        self.manifest,self.session,self.maximum,self.idle=manifest,session,maximum,idle_seconds
        self.frames=OrderedDict();self.seen=set();self.deadline=time.monotonic()+21600
    def packet(self,kind,v):emit(kind,dict(v,session=self.session,package_manifest_sha256=self.manifest))
    def jobs(self):
        errors=0
        for _ in range(40):
            if len(self.seen)>=self.maximum:break
            if time.monotonic()>=self.deadline:self.packet('STOP',dict(reason='absolute_six_hour_limit'));return
            nonce=secrets.token_hex(16);self.packet('READY',dict(nonce=nonce,remaining=self.maximum-len(self.seen),warm=True,idle_seconds=self.idle,fixed_gate_proof=getattr(self,'fixed_gate_proof',None)))
            try:
                v=read_line(max(0,min(self.idle,self.deadline-time.monotonic())))
                if v==dict(action='stop',nonce=nonce):self.packet('STOP',dict(reason='normal_operator_stop'));return
                if v.get('action')=='frame':
                    check_frame(v,nonce);parts=[];total=0;seq=0
                    while total<v['compressed_bytes']:
                        self.packet('ACK',dict(id=v['id'],next_seq=seq));b=check_chunk(read_line(20),v['id'],seq)
                        total+=len(b)
                        if total>v['compressed_bytes']:raise ValueError('Frame overflow')
                        parts.append(b);seq+=1
                    a=decode_frame(v,b''.join(parts));self.frames[v['case_id']]=(v,a);self.frames.move_to_end(v['case_id'])
                    while len(self.frames)>4:self.frames.popitem(last=False)
                    self.packet('PREPARED',dict(case_id=v['case_id'],frame_sha256=v['frame_sha256'],pixel_sha256=v['pixel_sha256'],id=v['id']));continue
                if set(v)!={'action','nonce','id','case_id','frame_sha256'} or v['action']!='infer' or v['nonce']!=nonce or not hexstr(v['id'],32) or v['id'] in self.seen:raise ValueError('New exact inference job required')
                if v['case_id'] not in self.frames:raise ValueError('Prepare frame before inference')
                header,a=self.frames[v['case_id']]
                if v['frame_sha256']!=header['frame_sha256']:raise ValueError('Inference frame SHA differs')
                self.seen.add(v['id']);request=dict(id=v['case_id'],frame_sha256=header['frame_sha256'],pixel_sha256=header['pixel_sha256'],video='uploaded:'+header['upload_id'],video_sha256=header['video_sha256'],timestamp_ms=header['timestamp_ms'],expected_decision=None)
                yield 'LIVE_'+v['id'],'B',request,dict(v,session=self.session),a.copy()
            except (ValueError,TypeError,KeyError,EOFError,TimeoutError,zlib.error) as error:
                errors+=1;self.packet('ERROR',dict(reason=str(error)[:160]))
                if errors>=3 or isinstance(error,(EOFError,TimeoutError)):break
        self.packet('STOP',dict(reason='bounded_session_complete'))
def tests():
    import copy
    a=np.zeros((448,448,3),np.uint8);a[10:20,30:40]=[12,34,56];f=io.BytesIO();np.save(f,a,allow_pickle=False);plain=f.getvalue();packed=zlib.compress(plain)
    nonce='a'*32;upload='b'*32;header=dict(action='frame',nonce=nonce,id='c'*32,case_id='u'+upload+'_f0',frame_sha256=digest(plain),pixel_sha256=digest(a.tobytes()),video_sha256='d'*64,upload_id=upload,timestamp_ms=2000,compressed_bytes=len(packed),compressed_sha256=digest(packed),file_bytes=len(plain))
    assert check_frame(header,nonce)==header and np.array_equal(decode_frame(header,packed),a)
    bad=[dict(header,nonce='e'*32),dict(header,action='shell'),dict(header,extra=True),dict(header,compressed_bytes=MAX_COMPRESSED+1),dict(header,file_bytes=602240.0),dict(header,timestamp_ms=float('nan')),dict(header,case_id='../../bad'),dict(header,frame_sha256='x'*64)]
    rejects=0
    for v in bad:
        try:check_frame(v,nonce)
        except ValueError:rejects+=1
        else:raise AssertionError('Unsafe frame header accepted')
    for payload in [packed+b'extra',packed[:-1]]:
        try:decode_frame(header,payload)
        except ValueError:rejects+=1
        else:raise AssertionError('Wrong payload accepted')
    for v in [dict(action='chunk',id=header['id'],seq=1,data='YQ=='),dict(action='chunk',id='f'*32,seq=0,data='YQ=='),dict(action='chunk',id=header['id'],seq=0,data=base64.b64encode(b'x'*513).decode())]:
        try:check_chunk(v,header['id'],0)
        except ValueError:rejects+=1
        else:raise AssertionError('Bad chunk accepted')
    channel=Channel('1'*64,'2'*32);packets=[];channel.packet=lambda k,v:packets.append((k,v));chunks=[packed[i:i+512] for i in range(0,len(packed),512)];step=[0]
    original=globals()['read_line']
    def fake_read(timeout):
        i=step[0];step[0]+=1
        n=next(v['nonce'] for k,v in reversed(packets) if k=='READY')
        if i==0:return dict(header,nonce=n)
        if i<=len(chunks):return dict(action='chunk',id=header['id'],seq=i-1,data=base64.b64encode(chunks[i-1]).decode())
        if i==len(chunks)+1:return dict(action='infer',nonce=n,id='3'*32,case_id=header['case_id'],frame_sha256=header['frame_sha256'])
        return dict(action='stop',nonce=n)
    try:
        globals()['read_line']=fake_read;iterator=channel.jobs();label,arm,r,job,frame=next(iterator)
        assert label=='LIVE_'+'3'*32 and arm=='B' and r['expected_decision'] is None and job['id']=='3'*32 and np.array_equal(frame,a)
        assert list(iterator)==[] and any(k=='PREPARED' for k,v in packets) and packets[-1]==('STOP',dict(reason='normal_operator_stop'))
    finally:globals()['read_line']=original
    return dict(status='PASS_DATA_ONLY_FRAME_AND_INFERENCE_PROTOCOL_CPU',negative_cases=rejects,actual_generator_frame_prepare_infer_normal_stop=True,raw_RGB_bit_exact=True,device_calls=0,model_calls=0,session_lifetime=lifetime_tests())

def lifetime_tests():
    ch=Channel('1'*64,'2'*32);assert ch.idle==21600 and 21599<ch.deadline-time.monotonic()<=21600
    packets=[];ch.packet=lambda k,v:packets.append((k,v));ch.deadline=time.monotonic()-1
    assert list(ch.jobs())==[] and packets==[('STOP',dict(reason='absolute_six_hour_limit'))]
    try:Channel('1'*64,'2'*32,idle_seconds=1200)
    except AssertionError:pass
    else:raise AssertionError('Old short idle still accepted')
    ch=Channel('1'*64,'2'*32);packets=[];ch.packet=lambda k,v:packets.append((k,v));ch.deadline=time.monotonic()+.1;original=globals()['read_line'];seen=[]
    def expired(timeout):
        assert 0<=timeout<=.1;seen.append(timeout);raise TimeoutError('fixture-only deadline')
    try:
        globals()['read_line']=expired;assert list(ch.jobs())==[] and seen and packets[-1]==('STOP',dict(reason='bounded_session_complete'))
    finally:globals()['read_line']=original
    return dict(six_hour_absolute_bound=True,idle21600=True,old1200_rejected=True,remaining_deadline_caps_read=True,expiry_returns_normally=True,max_live_jobs_unchanged=12,model_calls=0)
