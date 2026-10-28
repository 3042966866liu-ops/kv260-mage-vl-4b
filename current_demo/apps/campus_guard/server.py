"""Local campus demonstration UI; historical evidence and live jobs stay separate.

The web process has no UART, subprocess, Overlay or DMA access. An authenticated
worker must supply a fresh nonce-bound saved hardware result for live answers.
"""
import argparse,hashlib,json,mimetypes,os,secrets,sqlite3,threading,time,uuid,socket,base64,io,math
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,unquote

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())

class Store:
    def __init__(self,database):
        self.path=Path(database);self.path.parent.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock();self.worker=None
        self.catalog=read(HERE/'catalog.json')
        assert sha(ROOT/self.catalog['evidence_file'])==self.catalog['evidence_sha256']
        with self.db() as c:
            c.execute('CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,kind TEXT NOT NULL,case_id TEXT NOT NULL,status TEXT NOT NULL,decision TEXT,created REAL NOT NULL,updated REAL NOT NULL,revision INTEGER NOT NULL DEFAULT 0,result TEXT,disposition TEXT,note TEXT)')
            if 'upload_id' not in {r[1] for r in c.execute('PRAGMA table_info(events)')}:
                c.execute('ALTER TABLE events ADD COLUMN upload_id TEXT')
            c.execute('CREATE TABLE IF NOT EXISTS uploads(id TEXT PRIMARY KEY,name TEXT NOT NULL,path TEXT NOT NULL,sha256 TEXT NOT NULL,bytes INTEGER NOT NULL,created REAL NOT NULL,known_cases TEXT NOT NULL)')
            c.execute('CREATE TABLE IF NOT EXISTS uploaded_frames(case_id TEXT PRIMARY KEY,upload_id TEXT NOT NULL,timestamp_ms REAL NOT NULL,image_file TEXT NOT NULL,npy_file TEXT NOT NULL,frame_sha256 TEXT NOT NULL,pixel_sha256 TEXT NOT NULL)')
            c.execute('CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT NOT NULL,created REAL NOT NULL,action TEXT NOT NULL,body TEXT NOT NULL)')
            for r in self.catalog['rows']:
                c.execute('INSERT OR IGNORE INTO events(id,kind,case_id,status,decision,created,updated,result) VALUES(?,?,?,?,?,?,?,?)',('record-'+r['id'],'recorded',r['id'],'review',r['actual_decision'],0,0,json.dumps(r)))
    @contextmanager
    def db(self):
        c=sqlite3.connect(self.path);c.row_factory=sqlite3.Row
        try:
            with c:yield c
        finally:c.close()
    def case(self,id):
        row=next((r for r in self.catalog['rows'] if r['id']==id),None)
        if row:return row
        with self.db() as c:r=c.execute('SELECT * FROM uploaded_frames WHERE case_id=?',(id,)).fetchone()
        if r is None:return None
        return dict(id=r['case_id'],camera_id='upload',timestamp_ms=r['timestamp_ms'],frame_path='/uploaded/'+r['upload_id']+'/frame/'+r['case_id'],frame_sha256=r['frame_sha256'],npy_file=r['npy_file'],upload_id=r['upload_id'])
    def upload(self,id):
        with self.db() as c:
            row=c.execute('SELECT * FROM uploads WHERE id=?',(id,)).fetchone()
            if row is None:return None
            value=dict(row);value['known_cases']=json.loads(value['known_cases']);value['video_url']='/uploaded/'+value['id']
            value['cases']=[{k:r[k] for k in ('id','camera_id','timestamp_ms','frame_path')} for id in value['known_cases'] if (r:=self.case(id))]
            value['frames_ready']=bool(value['cases']);value['verified_demo']=any(r['video_sha256']==value['sha256'] for r in self.catalog['rows']);value.pop('path',None)
            return value
    def save_frames(self,id,frames):
        import numpy as np
        from PIL import Image
        upload=self.upload(id)
        if upload is None:raise ValueError('视频不存在')
        if upload['cases']:return upload
        if not isinstance(frames,list) or not 1<=len(frames)<=3:raise ValueError('每段视频需要1至3个真实采样帧')
        folder=(self.path.parent/'uploads'/id).resolve();rows=[]
        for index,item in enumerate(frames):
            timestamp=float(item['timestamp_ms'])
            if not math.isfinite(timestamp) or not 0<=timestamp<=3600000:raise ValueError('采样时间无效')
            raw=base64.b64decode(item['png_base64'],validate=True)
            if not 16<=len(raw)<=2<<20:raise ValueError('采样图像大小超限')
            image=Image.open(io.BytesIO(raw))
            if image.format!='PNG' or image.size!=(448,448):raise ValueError('采样帧必须为448×448 PNG')
            a=np.asarray(image.convert('RGB'),np.uint8).copy();case_id='u'+id+'_f'+str(index)
            image_file=folder/(case_id+'.png');npy_file=folder/(case_id+'.npy')
            with image_file.open('xb') as f:f.write(raw)
            with npy_file.open('xb') as f:np.save(f,a,allow_pickle=False)
            rows.append((case_id,id,timestamp,str(image_file),str(npy_file),sha(npy_file),hashlib.sha256(a.tobytes()).hexdigest()))
        with self.lock,self.db() as c:
            c.executemany('INSERT INTO uploaded_frames VALUES(?,?,?,?,?,?,?)',rows)
            c.execute('UPDATE uploads SET known_cases=? WHERE id=?',(json.dumps([r[0] for r in rows]),id))
        return self.upload(id)
    def save_upload(self,stream,length,name):
        if not 16<=length<=100<<20:raise ValueError('视频大小须在16字节至100 MiB之间')
        name=unquote(name).replace('\\','/').split('/')[-1][:200].strip() or 'uploaded-video.mp4'
        id=uuid.uuid4().hex;folder=self.path.parent/'uploads'/id;folder.mkdir(parents=True)
        part=folder/'video.partial';digest=hashlib.sha256();remaining=length
        try:
            with part.open('xb') as f:
                while remaining:
                    block=stream.read(min(remaining,256<<10))
                    if not block:raise ValueError('视频上传中断，请重新选择文件')
                    f.write(block);digest.update(block);remaining-=len(block)
            with part.open('rb') as f:magic=f.read(16)
            suffix='.mp4' if magic[4:8]==b'ftyp' else '.webm' if magic[:4]==b'\x1aE\xdf\xa3' else None
            if suffix is None:raise ValueError('请选择可播放的MP4或WebM视频')
            target=folder/('video'+suffix);part.rename(target);h=digest.hexdigest()
            cases=[r['id'] for r in self.catalog['rows'] if r['video_sha256']==h]
            with self.db() as c:c.execute('INSERT INTO uploads VALUES(?,?,?,?,?,?,?)',(id,name,str(target.resolve()),h,length,time.time(),json.dumps(cases)))
            return self.upload(id)
        except BaseException:
            if part.exists() and part.resolve().is_relative_to(folder.resolve()):part.unlink()
            raise
    def state(self):
        with self.lock,self.db() as c:
            self.expire(c)
            events=[]
            for row in c.execute('SELECT * FROM events ORDER BY created DESC,id'):
                e=dict(row);e['result']=json.loads(e['result']) if e['result'] else None
                frame=self.case(e['case_id']);e['frame_path']=frame['frame_path'] if frame else '';events.append(e)
            w=dict(self.worker) if self.worker and time.monotonic()-self.worker['seen']<15 else None
            if w:w.pop('seen',None)
            extra=[self.case(r[0]) for r in c.execute('SELECT case_id FROM uploaded_frames')]
            cases=[{k:v for k,v in r.items() if k in ('id','camera_id','timestamp_ms','frame_path')} for r in list(self.catalog['rows'])+extra if r]
            return dict(cameras=[dict(id='kitchen',name='食堂后厨',location='演示机位 01',description='正常备餐场景 · 模拟素材'),dict(id='workshop',name='实训工坊',location='演示机位 02',description='设备作业场景 · 模拟素材')],cases=cases,events=events,worker=w,model_build=self.catalog['model_build'],tasks=[dict(id='knife_visible',name='是否可见刀具',enabled=True),dict(id='hand_holding_knife',name='是否有人手持刀具',enabled=False,note='实验待验收')],evidence=dict(sha256=self.catalog['evidence_sha256'],fixed_windows=4,hot_samples=2,hot_mean_s=sum(self.catalog['hot_TTFT_s'])/2,hot_s=self.catalog['hot_TTFT_s'],first_request_s=self.catalog['first_request_TTFT_s'],scope='四个固定窗口已实板验收；不代表任意视频准确率'),broker=dict(configured=False,connected=False),now=time.time())
    def expire(self,c):
        limit=time.time()-180
        for row in c.execute("SELECT id FROM events WHERE kind='live' AND status IN ('queued','running') AND created<?",(limit,)).fetchall():
            c.execute("UPDATE events SET status='unknown',decision=NULL,note='复核超时，待人工确认',updated=?,revision=revision+1 WHERE id=?",(time.time(),row['id']))
    def enqueue(self,case_id,upload_id=None,task_id='knife_visible'):
        with self.lock,self.db() as c:
            self.expire(c)
            if task_id!='knife_visible':raise ValueError('该检查条件尚未验收，不会使用原刀具问题冒充新任务')
            if not self.case(case_id):raise ValueError('未知演示窗口')
            if upload_id is not None:
                row=c.execute('SELECT known_cases FROM uploads WHERE id=?',(upload_id,)).fetchone()
                if row is None or case_id not in json.loads(row['known_cases']):raise ValueError('该视频尚未完成当前板端工作器的输入验收，不能套用其他视频结果')
            if not self.worker or time.monotonic()-self.worker['seen']>=15 or not self.worker['ready']:raise ValueError('板端工作器尚未就绪；未启动推理')
            if self.case(case_id).get('camera_id')=='upload' and not self.worker.get('supports_uploads'):raise ValueError('板端上传帧通道尚未就绪；未启动识别')
            if c.execute("SELECT id FROM events WHERE kind='live' AND status IN ('queued','running')").fetchone():raise ValueError('已有一个复核任务，请等待完成')
            id=uuid.uuid4().hex;now=time.time()
            c.execute('INSERT INTO events(id,kind,case_id,status,created,updated,upload_id) VALUES(?,?,?,?,?,?,?)',(id,'live',case_id,'queued',now,now,upload_id))
            c.execute('INSERT INTO audit(event_id,created,action,body) VALUES(?,?,?,?)',(id,now,'requested',json.dumps(dict(case_id=case_id))))
            return dict(id=id,status='queued')
    def worker_next(self):
        with self.lock,self.db() as c:
            self.expire(c);r=c.execute("SELECT * FROM events WHERE kind='live' AND status='queued' ORDER BY created LIMIT 1").fetchone()
            if not r:return dict(job=None)
            c.execute("UPDATE events SET status='running',updated=? WHERE id=?",(time.time(),r['id']))
            frame=self.case(r['case_id'])
            return dict(job=dict(id=r['id'],case_id=r['case_id'],frame_sha256=frame['frame_sha256'],timestamp_ms=frame['timestamp_ms'],frame_file=frame.get('npy_file'),upload_id=r['upload_id'],model_package_sha256=self.catalog['package_sha256'],prompt_tokens=128,task_id='knife_visible'))
    def complete(self,data):
        with self.lock,self.db() as c:
            row=c.execute("SELECT * FROM events WHERE id=? AND kind='live'",(data['id'],)).fetchone()
            if row is None or row['status']!='running':raise ValueError('没有对应的活动任务')
            # The saved result must belong to this exact request and source frame.
            f=(ROOT/data['evidence_file']).resolve();allowed=(ROOT/'deployment/mage_vl4b/optimization_v1/runs').resolve()
            if not f.is_relative_to(allowed) or f.suffix!='.json' or not f.is_file():raise ValueError('结果证据路径不合法')
            if sha(f)!=data['evidence_sha256']:raise ValueError('结果证据校验失败')
            v=read(f);case=self.case(row['case_id'])
            if v.get('ui_job_id')!=row['id'] or v.get('frame_sha256')!=case['frame_sha256'] or v.get('case_id')!=row['case_id']:raise ValueError('结果与当前任务不匹配，禁止使用历史答案冒充实时结果')
            if v.get('package_manifest_sha256')!=self.catalog['package_sha256'] or v.get('actual_full_vocab')!=151936 or v.get('physical_calls',0)<1:raise ValueError('缺少已冻结模型和真实全词表/板端执行证据')
            decision=v.get('decision') if v.get('primary_rc')==0 and v.get('argmax_verified') else None
            if decision not in ('Yes','No'):decision=None
            t=v.get('TTFT_s');t=float(t) if isinstance(t,(int,float)) and 0<t<180 else None
            if t is None:decision=None
            result=dict(TTFT_s=t,prepare_s=v.get('prepare_s'),prefill_s=v.get('prefill_s'),evidence_sha256=data['evidence_sha256'],token=v.get('raw_token'),physical_calls=v.get('physical_calls'),logits_sha256=v.get('logits_sha256'))
            c.execute('UPDATE events SET status=?,decision=?,updated=?,revision=revision+1,result=?,note=? WHERE id=?',('review' if decision else 'unknown',decision,time.time(),json.dumps(result),'待人工确认' if decision else '推理失败或输出不明确，待人工复核',row['id']))
            return dict(accepted=True,decision=decision)
    def review(self,id,data):
        action=data.get('disposition');note=str(data.get('note','')).strip()
        if action not in ('normal_work','attention','false_alarm'):raise ValueError('请选择处置方式')
        if not note or len(note)>500:raise ValueError('请填写1–500字的处置说明')
        with self.lock,self.db() as c:
            r=c.execute('SELECT * FROM events WHERE id=?',(id,)).fetchone()
            if r is None or r['status'] not in ('review','unknown','closed'):raise ValueError('当前事件不能处置')
            if r['revision']!=data.get('revision'):raise ValueError('事件已更新，请刷新后重试')
            now=time.time();c.execute("UPDATE events SET status='closed',disposition=?,note=?,updated=?,revision=revision+1 WHERE id=?",(action,note,now,id))
            c.execute('INSERT INTO audit(event_id,created,action,body) VALUES(?,?,?,?)',(id,now,'human_review',json.dumps(dict(disposition=action,note=note),ensure_ascii=False)))
            return dict(saved=True)

class Handler(BaseHTTPRequestHandler):
    server_version='CampusGuard/0.1'
    def log_message(self,*args):pass
    def send_json(self,value,code=200):
        raw=json.dumps(value,ensure_ascii=False,allow_nan=False).encode();self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(raw)
    def file(self,path):
        if not path.is_file():return self.send_error(404)
        size=path.stat().st_size;start=0;end=size-1;code=200
        range_header=self.headers.get('Range','')
        if range_header.startswith('bytes='):
            try:
                a,b=range_header[6:].split('-',1);start=int(a);end=min(int(b) if b else size-1,size-1)
                if start<0 or start>end:raise ValueError()
                code=206
            except ValueError:return self.send_error(416)
        self.send_response(code);self.send_header('Content-Type',mimetypes.guess_type(path.name)[0] or 'application/octet-stream');self.send_header('Content-Length',str(end-start+1));self.send_header('Accept-Ranges','bytes');self.send_header('X-Content-Type-Options','nosniff')
        if code==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.end_headers()
        try:
            with path.open('rb') as f:
                f.seek(start);left=end-start+1
                while left:
                    part=f.read(min(left,256*1024))
                    if not part:break
                    self.wfile.write(part);left-=len(part)
        except (BrokenPipeError,ConnectionResetError):pass
    def worker_authorized(self):return secrets.compare_digest(self.headers.get('X-Worker-Token',''),self.server.worker_token)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/state':return self.send_json(self.server.store.state())
        if path=='/api/worker/next':
            if not self.worker_authorized():return self.send_json(dict(error='Unauthorized'),401)
            return self.send_json(self.server.store.worker_next())
        if path=='/api/export':
            with self.server.store.db() as c:return self.send_json(dict(state=self.server.store.state(),audit=[dict(r) for r in c.execute('SELECT * FROM audit ORDER BY id')]))
        if path.startswith('/api/uploads/'):
            value=self.server.store.upload(path.split('/')[-1])
            return self.send_json(value) if value else self.send_error(404)
        if path.startswith('/uploaded/'):
            parts=path.split('/')
            with self.server.store.db() as c:
                row=c.execute('SELECT image_file AS path FROM uploaded_frames WHERE upload_id=? AND case_id=?',(parts[2],parts[4])).fetchone() if len(parts)==5 and parts[3]=='frame' else c.execute('SELECT path FROM uploads WHERE id=?',(parts[-1],)).fetchone()
            if row is None:return self.send_error(404)
            target=Path(row['path']).resolve();allowed=(self.server.store.path.parent/'uploads').resolve()
            return self.file(target) if target.is_relative_to(allowed) else self.send_error(404)
        if path.startswith('/media/'):
            camera=path.split('/')[-1].removesuffix('.mp4');row=next((r for r in self.server.store.catalog['rows'] if r['camera_id']==camera),None)
            return self.file(ROOT/row['video']) if row else self.send_error(404)
        target=(HERE/('static/demo.html' if path=='/' else path.lstrip('/'))).resolve()
        if not target.is_relative_to((HERE/'static').resolve()):return self.send_error(404)
        if target.suffix=='.html' and target.name!='demo.html':return self.send_error(404)
        return self.file(target)
    def do_POST(self):
        try:
            if self.headers.get('Origin') not in (None,f'http://{self.headers.get("Host")}'):return self.send_json(dict(error='Cross-origin write rejected'),403)
            n=int(self.headers.get('Content-Length','0'))
            if urlparse(self.path).path=='/api/uploads':return self.send_json(self.server.store.save_upload(self.rfile,n,self.headers.get('X-File-Name','uploaded-video.mp4')),201)
            request_path=urlparse(self.path).path
            if not 0<n<=(9<<20 if request_path.startswith('/api/uploads/') and request_path.endswith('/frames') else 16384):raise ValueError('请求过大或为空')
            data=json.loads(self.rfile.read(n));path=urlparse(self.path).path
            if path.startswith('/api/uploads/') and path.endswith('/frames'):return self.send_json(self.server.store.save_frames(path.split('/')[3],data['frames']))
            if path.startswith('/api/worker/'):
                if not self.worker_authorized():return self.send_json(dict(error='Unauthorized'),401)
                if path=='/api/worker/heartbeat':
                    with self.server.store.lock:self.server.store.worker=dict(ready=data.get('ready') is True,warm=data.get('warm') is True,supports_uploads=data.get('supports_uploads') is True,seen=time.monotonic(),build=str(data.get('build','未核验'))[:100])
                    return self.send_json(dict(accepted=True))
                if path=='/api/worker/result':return self.send_json(self.server.store.complete(data))
            if path=='/api/verify':return self.send_json(self.server.store.enqueue(data['case_id'],data.get('upload_id'),data.get('task_id','knife_visible')),202)
            if path.startswith('/api/events/') and path.endswith('/review'):return self.send_json(self.server.store.review(path.split('/')[3],data))
            return self.send_error(404)
        except (ValueError,KeyError,TypeError,sqlite3.Error,OSError) as e:return self.send_json(dict(error=str(e)),409)

class LocalServer(ThreadingHTTPServer):
    allow_reuse_address=False
    def server_bind(self):
        if os.name=='nt':self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        return super().server_bind()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8765);ap.add_argument('--database',default=str(HERE/'var/events.sqlite'));args=ap.parse_args()
    store=Store(args.database);http=LocalServer(('127.0.0.1',args.port),Handler);http.store=store
    token_path=Path(args.database).parent/'worker_token';token_path.parent.mkdir(exist_ok=True,parents=True)
    if not token_path.exists():token_path.write_text(secrets.token_hex(32),encoding='ascii')
    http.worker_token=token_path.read_text(encoding='ascii').strip()
    print(f'Campus UI http://127.0.0.1:{args.port} · recorded evidence available · live worker initially disconnected',flush=True)
    try:http.serve_forever()
    finally:http.server_close()
if __name__=='__main__':main()
