"""Software-only uploaded-input/session/No/error checks, never board evidence."""
import base64,hashlib,io,json,tempfile,time,unittest
from pathlib import Path
from PIL import Image
import numpy as np
import live_server as live
class Tests(unittest.TestCase):
    def setUp(self):
        p=live.HERE/'var/test_live';p.mkdir(parents=True,exist_ok=True);self.temp=tempfile.TemporaryDirectory(dir=p);self.folder=Path(self.temp.name)
        binding=self.folder/'binding.json';binding.write_text(json.dumps(dict(build='SOFTWARE_FIXTURE_ONLY',package_manifest_sha256='a'*64,canonical_inputs={})))
        self.store=live.LiveStore(self.folder/'events.sqlite',binding);self.orig=(live.ROOT,live.legacy.ROOT)
        video=b'\0\0\0\x18ftypmp42'+b'\0'*20;self.upload=self.store.save_upload(io.BytesIO(video),len(video),'knife_yes_renamed.mp4')
        b=io.BytesIO();Image.new('RGB',(448,448),(12,34,56)).save(b,format='PNG');self.upload=self.store.save_frames(self.upload['id'],[dict(timestamp_ms=2000,png_base64=base64.b64encode(b.getvalue()).decode())]);self.case=self.upload['cases'][0]['id']
    def tearDown(self):live.ROOT,live.legacy.ROOT=self.orig;self.temp.cleanup()
    def ready(self,session='b'*32):self.store.heartbeat(dict(session=session,package_manifest_sha256='a'*64,ready=True,warm=True))
    def prepared(self):
        c=self.store.case(self.case);self.store.prepared_frame(dict(session=self.store.worker['session'],case_id=self.case,frame_sha256=c['frame_sha256'],pixel_sha256=c['pixel_sha256']))
    def result(self,id,decision):
        live.ROOT=live.legacy.ROOT=self.folder;c=self.store.case(self.case);f=self.folder/'deployment/mage_vl4b/optimization_v1/runs/SOFTWARE_ONLY/result.json';f.parent.mkdir(parents=True,exist_ok=True)
        v=dict(TEST_ONLY_SYNTHETIC=True,ui_job_id=id,session=self.store.worker['session'],case_id=self.case,frame_sha256=c['frame_sha256'],package_manifest_sha256='a'*64,actual_full_vocab=151936,physical_calls=330,primary_rc=0,argmax_verified=True,decision=decision,TTFT_s=28,raw_token=decision,completed_request=True,full_logits_sha256='c'*64,logits_sha256='c'*64)
        f.write_text(json.dumps(v));return dict(id=id,evidence_file=f.relative_to(self.folder).as_posix(),evidence_sha256=live.sha(f))
    def test_real_uploaded_pixels_no_filename_answer(self):
        c=self.store.case(self.case);a=np.load(c['npy_file'],allow_pickle=False);self.assertTrue(np.all(a==[12,34,56]));self.assertNotIn('decision',self.upload);self.assertFalse(self.upload['board_prepared'])
    def test_play_job_requires_exact_prepared_frame(self):
        self.ready()
        with self.assertRaises(ValueError):self.store.enqueue(self.case,self.upload['id'])
        self.prepared();job=self.store.enqueue(self.case,self.upload['id']);actual=self.store.worker_next()['job'];self.assertEqual(actual['id'],job['id']);self.assertNotIn('expected_decision',actual)
    def test_session_restart_invalidates_prepared_frames(self):
        self.ready();self.prepared();self.assertTrue(self.store.upload(self.upload['id'])['board_prepared']);self.ready('d'*32);self.assertFalse(self.store.upload(self.upload['id'])['board_prepared'])
    def test_wrong_prepared_sha_rejected(self):
        self.ready();c=self.store.case(self.case)
        with self.assertRaises(ValueError):self.store.prepared_frame(dict(session='b'*32,case_id=self.case,frame_sha256='0'*64,pixel_sha256=c['pixel_sha256']))
    def test_yes_and_no_are_actual_result_only(self):
        self.ready();self.prepared();j=self.store.enqueue(self.case,self.upload['id']);self.store.worker_next();r=self.result(j['id'],'No');self.assertEqual(self.store.complete(r)['decision'],'No')
        row=next(r for r in self.store.state()['events'] if r['id']==j['id']);self.assertEqual(row['decision'],'No')
    def test_invalid_result_not_no(self):
        self.ready();self.prepared();j=self.store.enqueue(self.case,self.upload['id']);self.store.worker_next();self.assertIsNone(self.store.complete(self.result(j['id'],'Unclear'))['decision'])
    def test_old_session_result_not_accepted(self):
        self.ready();self.prepared();j=self.store.enqueue(self.case,self.upload['id']);self.store.worker_next();r=self.result(j['id'],'Yes');self.ready('d'*32)
        with self.assertRaises(ValueError):self.store.complete(r)
    def test_transport_failure_remains_unknown(self):
        self.ready();self.prepared();j=self.store.enqueue(self.case,self.upload['id']);self.store.worker_next();self.store.fail_job(dict(id=j['id']));e=next(e for e in self.store.state()['events'] if e['id']==j['id']);self.assertEqual(e['status'],'unknown');self.assertIsNone(e['decision'])
    def test_closed_worker_does_not_leave_running_result(self):
        self.ready();self.prepared();j=self.store.enqueue(self.case,self.upload['id']);self.store.worker_next()
        self.store.heartbeat(dict(session='b'*32,package_manifest_sha256='a'*64,closed=True))
        self.assertIsNone(self.store.worker);e=next(e for e in self.store.state()['events'] if e['id']==j['id']);self.assertEqual(e['status'],'unknown');self.assertIsNone(e['decision'])
    def test_new_session_never_replays_queued_old_job(self):
        self.ready();self.prepared();j=self.store.enqueue(self.case,self.upload['id']);self.ready('d'*32)
        self.assertIsNone(self.store.worker_next()['job']);e=next(e for e in self.store.state()['events'] if e['id']==j['id']);self.assertEqual(e['status'],'unknown');self.assertIsNone(e['decision'])
    def test_wrong_worker_package_not_online(self):
        with self.assertRaises(ValueError):self.store.heartbeat(dict(session='b'*32,package_manifest_sha256='0'*64,ready=True,warm=True))
    def test_latest_upload_only_and_new_nonce(self):
        self.ready();self.assertEqual(self.store.prepare_next()['frame']['case_id'],self.case);self.prepared();self.assertIsNone(self.store.prepare_next()['frame']);j1=self.store.enqueue(self.case,self.upload['id']);self.store.worker_next();self.store.fail_job(dict(id=j1['id']));j2=self.store.enqueue(self.case,self.upload['id']);self.assertNotEqual(j1['id'],j2['id'])
if __name__=='__main__':unittest.main()
