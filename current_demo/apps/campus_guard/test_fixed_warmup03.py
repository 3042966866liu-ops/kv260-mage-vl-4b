"""Software-only fixed gate admission negatives, never writes a board result."""
import copy,json,unittest
from pathlib import Path
from save_fixed_warmup03 import validate,ROOT,HERE
class Tests(unittest.TestCase):
    def setUp(self):
        self.binding=json.loads((HERE/'LIVE_BINDING.json').read_bytes());prep=json.loads((ROOT/self.binding['worker_preparation']).read_bytes());self.plan=json.loads((ROOT/prep['package']/'DEMO_BOARD_PLAN.json').read_bytes());r=self.plan['demo_requests'][0]
        self.v=dict(session='a'*32,package_manifest_sha256=self.binding['package_manifest_sha256'],fixed_gate_proof=dict(status='PASS_M544_CURRENT_BOOT_FIXED_WARMUP_BEFORE_WEB',primary_rc=0,session='a'*32,package_manifest_sha256=self.binding['package_manifest_sha256'],boot_id=self.plan['expected_boot'],completed_request=True,answer_correct=True,decision=r['expected_decision'],expected_decision=r['expected_decision'],frame_sha256=r['frame_sha256'],actual_full_vocab=151936,argmax_verified=True,physical_calls=330,visual_physical_calls=104,input_tokens=128,T32_blocks=4,decode_calls=0,owners_still_live=True,logits_sha256='b'*64,source_sample_sha256='c'*64))
    def test_good_and_rejected_actual_admission(self):
        validate(self.v,self.binding,self.plan)
        for field,value in [('primary_rc',1),('session','d'*32),('boot_id','wrong'),('answer_correct',False),('decision','No'),('frame_sha256','e'*64),('actual_full_vocab',2),('physical_calls',0),('visual_physical_calls',0),('T32_blocks',3),('decode_calls',1),('argmax_verified',False)]:
            with self.subTest(field=field):
                v=copy.deepcopy(self.v);v['fixed_gate_proof'][field]=value
                with self.assertRaises(AssertionError):validate(v,self.binding,self.plan)
if __name__=='__main__':unittest.main()
