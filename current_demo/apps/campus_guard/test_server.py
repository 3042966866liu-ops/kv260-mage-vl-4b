"""Software-only UI/queue tests. Synthetic worker results stay in temp roots."""
import hashlib,json,secrets,tempfile,threading,time,unittest,urllib.request,urllib.error,io,base64
from pathlib import Path
import server

class Tests(unittest.TestCase):
    def setUp(self):
        parent=server.HERE/'var/tests';parent.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=parent);self.root=Path(self.temp.name).resolve()
        assert self.root.is_relative_to(parent.resolve())
        self.store=server.Store(self.root/'test.sqlite');self.original_root=server.ROOT
    def tearDown(self):
        server.ROOT=self.original_root
        assert self.root.is_relative_to((server.HERE/'var/tests').resolve());self.temp.cleanup()
    def ready(self):self.store.worker=dict(ready=True,warm=True,seen=time.monotonic(),build='TEST_ONLY_FAKE_WORKER')
    def make_result(self,id,decision='Yes'):
        server.ROOT=self.root;f=self.root/'deployment/mage_vl4b/optimization_v1/runs/software_fixture.json';f.parent.mkdir(parents=True,exist_ok=True)
        value=dict(TEST_ONLY_SYNTHETIC=True,ui_job_id=id,case_id='cal_04_t0',frame_sha256=self.store.case('cal_04_t0')['frame_sha256'],package_manifest_sha256=self.store.catalog['package_sha256'],actual_full_vocab=151936,physical_calls=330,primary_rc=0,argmax_verified=True,decision=decision,TTFT_s=29.5,raw_token=decision)
        f.write_text(json.dumps(value));return dict(id=id,evidence_file=f.relative_to(self.root).as_posix(),evidence_sha256=server.sha(f))
    def test_disconnected_no_inference(self):
        with self.assertRaisesRegex(ValueError,'未启动推理'):self.store.enqueue('cal_04_t0')
        self.assertEqual(len(self.store.state()['events']),4)
    def test_single_queue_and_exact_nonce(self):
        self.ready();j=self.store.enqueue('cal_04_t0');job=self.store.worker_next()['job'];self.assertEqual(job['id'],j['id'])
        with self.assertRaises(ValueError):self.store.enqueue('cal_00_t0')
        result=self.make_result(j['id']);p=server.ROOT/result['evidence_file'];v=json.loads(p.read_text());v['ui_job_id']='wrong';p.write_text(json.dumps(v));result['evidence_sha256']=server.sha(p)
        with self.assertRaisesRegex(ValueError,'禁止使用历史答案'):self.store.complete(result)
    def test_saved_result_and_review_version(self):
        self.ready();j=self.store.enqueue('cal_04_t0');self.store.worker_next();r=self.make_result(j['id']);self.assertEqual(self.store.complete(r)['decision'],'Yes')
        e=next(e for e in self.store.state()['events'] if e['id']==j['id']);self.assertEqual(e['status'],'review')
        self.store.review(e['id'],dict(revision=e['revision'],disposition='normal_work',note='TEST ONLY normal preparation'))
        with self.assertRaisesRegex(ValueError,'已更新'):self.store.review(e['id'],dict(revision=e['revision'],disposition='attention',note='TEST ONLY stale'))
        with self.store.db() as c:self.assertEqual(c.execute("SELECT count(*) FROM audit WHERE action='human_review'").fetchone()[0],1)
    def test_invalid_output_not_negative(self):
        self.ready();j=self.store.enqueue('cal_04_t0');self.store.worker_next();r=self.make_result(j['id'],'Unclear');self.assertIsNone(self.store.complete(r)['decision'])
        e=next(e for e in self.store.state()['events'] if e['id']==j['id']);self.assertEqual(e['status'],'unknown')
    def test_timeout_not_negative(self):
        self.ready();j=self.store.enqueue('cal_04_t0')
        with self.store.db() as c:c.execute('UPDATE events SET created=? WHERE id=?',(time.time()-200,j['id']))
        self.assertIsNone(self.store.worker_next()['job']);e=next(e for e in self.store.state()['events'] if e['id']==j['id']);self.assertIsNone(e['decision']);self.assertEqual(e['status'],'unknown')
    def test_heartbeat_expires(self):
        self.ready();self.store.worker['seen']-=20;self.assertIsNone(self.store.state()['worker'])
        with self.assertRaises(ValueError):self.store.enqueue('cal_04_t0')
    def test_new_upload_and_actual_RGB_frames(self):
        from PIL import Image
        import numpy as np
        video=b'\x00\x00\x00\x18ftypmp42'+b'\x00'*20
        u=self.store.save_upload(io.BytesIO(video),len(video),'no_knife_claimed_by_filename.mp4')
        self.assertFalse(u['frames_ready']);self.assertFalse(u['verified_demo']);self.assertNotIn('decision',u)
        png=io.BytesIO();Image.new('RGB',(448,448),(12,34,56)).save(png,format='PNG')
        u=self.store.save_frames(u['id'],[dict(timestamp_ms=2500,png_base64=base64.b64encode(png.getvalue()).decode())])
        self.assertEqual(len(u['cases']),1);c=self.store.case(u['cases'][0]['id'])
        a=np.load(c['npy_file'],allow_pickle=False);self.assertEqual(a.shape,(448,448,3));self.assertTrue(np.all(a[0,0]==[12,34,56]));self.assertEqual(server.sha(c['npy_file']),c['frame_sha256'])
        self.ready()
        with self.assertRaisesRegex(ValueError,'上传帧通道'):self.store.enqueue(c['id'],u['id'])
        self.store.worker['supports_uploads']=True;j=self.store.enqueue(c['id'],u['id']);self.assertIsNotNone(self.store.worker_next()['job']['frame_file'])
        self.assertIsNone(next(e for e in self.store.state()['events'] if e['id']==j['id'])['decision'])
    def test_invalid_upload_and_question_rejected(self):
        with self.assertRaises(ValueError):self.store.save_upload(io.BytesIO(b'not a video'*10),110,'movie.mp4')
        self.ready()
        with self.assertRaisesRegex(ValueError,'条件尚未验收'):self.store.enqueue('cal_04_t0',task_id='hand_holding_knife')
    def test_video_cannot_borrow_another_case(self):
        video=b'\x00\x00\x00\x18ftypmp42'+b'\x00'*20
        u=self.store.save_upload(io.BytesIO(video),len(video),'knife.mp4');self.ready()
        with self.assertRaisesRegex(ValueError,'不能套用'):self.store.enqueue('cal_04_t0',u['id'])
    def test_http_auth_csrf_and_video_range(self):
        http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);http.store=self.store;http.worker_token=secrets.token_hex(16)
        thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start();base='http://127.0.0.1:'+str(http.server_port)
        try:
            with urllib.request.urlopen(base+'/api/state') as r:self.assertEqual(len(json.load(r)['events']),4)
            with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(base+'/api/worker/next')
            self.assertEqual(e.exception.code,401)
            req=urllib.request.Request(base+'/api/verify',data=b'{"case_id":"cal_04_t0"}',headers={'Content-Type':'application/json','Origin':'http://untrusted.invalid'})
            with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(req)
            self.assertEqual(e.exception.code,403)
            req=urllib.request.Request(base+'/media/kitchen.mp4',headers={'Range':'bytes=0-7'})
            with urllib.request.urlopen(req) as r:self.assertEqual(r.status,206);self.assertEqual(len(r.read()),8)
        finally:http.shutdown();http.server_close();thread.join()

if __name__=='__main__':unittest.main(verbosity=2)
