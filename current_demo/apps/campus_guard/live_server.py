"""Local presentation API. Receives nonce-bound live board proofs; no UART/device calls."""
import argparse,base64,hashlib,io,json,math,secrets,threading,time
from pathlib import Path
import server as legacy
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
read=legacy.read;sha=legacy.sha
class LiveStore(legacy.Store):
    def __init__(self,database,binding=None):
        super().__init__(database)
        self.binding=read(Path(binding)) if binding else read(HERE/'LIVE_BINDING.json')
        self.catalog=dict(self.catalog,rows=[],package_sha256=self.binding['package_manifest_sha256'],model_build=self.binding['build'])
        self.prepared={};self.pending_stop=False;self.selected_upload_id=None
        self.web_source_sha256=sha(Path(__file__))
        self.parent_audit=None
        if self.binding.get('parent_audit'):
            f=ROOT/self.binding['parent_audit']
            if sha(f)!=self.binding['parent_audit_sha256']:raise ValueError('当前实板参考证据SHA不符')
            self.parent_audit=read(f)
    def case(self,id):
        value=super().case(id)
        if value and value.get('camera_id')=='upload':
            with self.db() as c:r=c.execute('SELECT pixel_sha256 FROM uploaded_frames WHERE case_id=?',(id,)).fetchone()
            value['pixel_sha256']=r[0];value['prepared']=self.prepared.get(id)==(self.worker or {}).get('session') and self.worker is not None
        return value
    def upload(self,id):
        value=super().upload(id)
        if value:
            value['board_prepared']=bool(value['cases']) and bool(self.case(value['cases'][0]['id']).get('prepared'))
            value['canonical_input']=value['sha256'] in self.binding.get('canonical_inputs',{})
        return value
    def save_upload(self,stream,length,name):
        value=super().save_upload(stream,length,name)
        profile=self.binding.get('canonical_inputs',{}).get(value['sha256'])
        if profile:
            import numpy as np
            from PIL import Image
            source=ROOT/profile['frame'];assert sha(source)==profile['frame_sha256']
            a=np.load(source,allow_pickle=False);assert a.shape==(448,448,3) and a.dtype==np.uint8
            b=io.BytesIO();Image.fromarray(a).save(b,format='PNG')
            value=self.save_frames(value['id'],[dict(timestamp_ms=profile['timestamp_ms'],png_base64=base64.b64encode(b.getvalue()).decode())])
        return value
    def save_frames(self,id,frames):
        if not isinstance(frames,list) or len(frames)!=1:raise ValueError('每次演示只提交一张明确的真实采样画面')
        return super().save_frames(id,frames)
    def heartbeat(self,data):
        session=data.get('session','')
        if len(session)!=32 or any(c not in '0123456789abcdef' for c in session):raise ValueError('工作器会话无效')
        if data.get('package_manifest_sha256')!=self.binding['package_manifest_sha256']:raise ValueError('不是已冻结的当前修复版工作器')
        with self.lock:
            if data.get('closed') is True:
                if self.worker and self.worker.get('session')==session:
                    with self.db() as c:c.execute("UPDATE events SET status='unknown',decision=NULL,note=?,updated=? WHERE kind='live' AND status IN ('queued','running')",('板端连接结束，本次识别未完成',time.time()))
                    self.worker=None;self.prepared.clear()
                return dict(accepted=True)
            if not self.worker or self.worker.get('session')!=session:
                with self.db() as c:c.execute("UPDATE events SET status='unknown',decision=NULL,note=?,updated=? WHERE kind='live' AND status IN ('queued','running')",('工作器会话已更换，请重新播放',time.time()))
                self.prepared.clear();self.pending_stop=False
            self.worker=dict(session=session,ready=data.get('ready') is True,warm=data.get('warm') is True,supports_uploads=True,seen=time.monotonic(),build=self.binding['build'],package_manifest_sha256=data['package_manifest_sha256'])
        return dict(accepted=True)
    def prepared_frame(self,data):
        with self.lock:
            c=self.case(data.get('case_id'));w=self.worker
            if not c or not w or data.get('session')!=w['session'] or data.get('frame_sha256')!=c['frame_sha256'] or data.get('pixel_sha256')!=c['pixel_sha256']:raise ValueError('板端准备回执与本次输入不匹配')
            self.prepared[c['id']]=w['session']
        return dict(accepted=True)
    def select_input(self,data):
        if set(data)!={'upload_id'} or not isinstance(data['upload_id'],str) or len(data['upload_id'])!=32 or any(c not in '0123456789abcdef' for c in data['upload_id']):raise ValueError('视频标识无效')
        with self.lock,self.db() as c:
            value=self.upload(data['upload_id'])
            if not value or not value['frames_ready'] or not value['cases']:raise ValueError('视频识别画面尚未准备')
            if c.execute("SELECT 1 FROM events WHERE kind='live' AND status IN ('queued','running') LIMIT 1").fetchone():raise ValueError('当前识别尚未结束')
            self.selected_upload_id=data['upload_id']
        return dict(accepted=True,upload_id=self.selected_upload_id)
    def prepare_next(self):
        with self.lock,self.db() as c:
            if self.pending_stop:return dict(stop=True,frame=None)
            if not self.worker:return dict(frame=None)
            rows=c.execute('SELECT id,known_cases,sha256 FROM uploads WHERE id=?',(self.selected_upload_id,)) if self.selected_upload_id else c.execute('SELECT id,known_cases,sha256 FROM uploads ORDER BY created DESC LIMIT 1')
            for row in rows:
                ids=json.loads(row['known_cases'])
                if not ids:continue
                value=self.case(ids[0])
                if value and not value.get('prepared'):
                    return dict(frame=dict(case_id=value['id'],frame_file=value['npy_file'],frame_sha256=value['frame_sha256'],pixel_sha256=value['pixel_sha256'],timestamp_ms=value['timestamp_ms'],upload_id=row['id'],video_sha256=row['sha256']))
            return dict(frame=None)
    def enqueue(self,case_id,upload_id=None,task_id='knife_visible'):
        case=self.case(case_id)
        if not upload_id or not case or not case.get('prepared'):raise ValueError('画面还未准备到当前板端，请稍候')
        return super().enqueue(case_id,upload_id,task_id)
    def worker_next(self):
        result=super().worker_next()
        if result.get('job'):result['job']['session']=self.worker['session']
        return result
    def complete(self,data):
        f=(ROOT/data['evidence_file']).resolve();allowed=ROOT/'deployment/mage_vl4b/optimization_v1/runs'
        if not f.is_relative_to(allowed) or not f.is_file():raise ValueError('结果证据路径不合法')
        v=read(f)
        if not self.worker or v.get('session')!=self.worker['session']:raise ValueError('结果来自其他工作器会话')
        if not v.get('completed_request') or v.get('full_logits_sha256')!=v.get('logits_sha256'):raise ValueError('缺少本次完整词表判断证明')
        return super().complete(data)
    def fail_job(self,data):
        with self.lock,self.db() as c:
            row=c.execute("SELECT * FROM events WHERE id=? AND kind='live' AND status IN ('queued','running')",(data.get('id'),)).fetchone()
            if row:c.execute("UPDATE events SET status='unknown',decision=NULL,note=?,updated=? WHERE id=?",('识别未完成，请检查板端连接',time.time(),row['id']))
        return dict(accepted=True)
    def state(self):
        value=super().state();value['model_build']=self.binding['build'];value['stop_requested']=self.pending_stop;value['web_source_sha256']=self.web_source_sha256;value['worker_package_sha256']=self.binding['package_manifest_sha256']
        if self.parent_audit:
            a=self.parent_audit;value['evidence']=dict(sha256=self.binding['parent_audit_sha256'],fixed_windows=a['validation_frames'],hot_samples=len(a['hot_TTFT_s']),hot_mean_s=a['hot_mean_s'],hot_s=a['hot_TTFT_s'],first_request_s=a['first_request_s'],scope='当前M543六固定帧实板参考；新网页任务另有独立结果证据')
        return value
class Handler(legacy.Handler):
    def do_GET(self):
        if self.path=='/api/worker/prepare':
            if not self.worker_authorized():return self.send_json(dict(error='Unauthorized'),401)
            return self.send_json(self.server.store.prepare_next())
        return super().do_GET()
    def do_POST(self):
        path=self.path
        routes={'/api/worker/heartbeat':'heartbeat','/api/worker/prepared':'prepared_frame','/api/worker/failed':'fail_job','/api/input/select':'select_input'}
        if path not in routes and path!='/api/board/stop':return super().do_POST()
        try:
            if self.headers.get('Origin') not in (None,'http://'+self.headers.get('Host','')):return self.send_json(dict(error='Cross-origin write rejected'),403)
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=16384:raise ValueError('请求大小无效')
            data=json.loads(self.rfile.read(n))
            if path=='/api/input/select':return self.send_json(self.server.store.select_input(data))
            if path=='/api/board/stop':
                self.server.store.pending_stop=True;return self.send_json(dict(accepted=True))
            if not self.worker_authorized():return self.send_json(dict(error='Unauthorized'),401)
            return self.send_json(getattr(self.server.store,routes[path])(data))
        except (ValueError,KeyError,TypeError,OSError) as e:return self.send_json(dict(error=str(e)),409)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8766);ap.add_argument('--database',default=str(HERE/'var/live/events.sqlite'));a=ap.parse_args()
    store=LiveStore(a.database);http=legacy.LocalServer(('127.0.0.1',a.port),Handler);http.store=store
    token=Path(a.database).parent/'worker_token';token.parent.mkdir(parents=True,exist_ok=True)
    if not token.exists():token.write_text(secrets.token_hex(32),encoding='ascii')
    http.worker_token=token.read_text(encoding='ascii').strip()
    print('Campus demonstration http://127.0.0.1:'+str(a.port),flush=True)
    try:http.serve_forever()
    finally:http.server_close()
if __name__=='__main__':main()
