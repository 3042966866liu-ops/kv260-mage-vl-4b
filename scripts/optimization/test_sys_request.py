from types import SimpleNamespace
import unittest
import numpy as np
from sys_request import run_sys_request,run_raw_contract_request


class SysRequestTests(unittest.TestCase):
    def arguments(self):
        board=SimpleNamespace(logical_calls=0,evidence=lambda:{'logical_calls':0})
        return dict(video_path='unused',video_sha256='test',question='Which direction?',
            vision=lambda **kw:np.zeros((784,2560),np.float32),
            model=SimpleNamespace(input_embeddings=lambda ids,visual:np.zeros((len(ids),2560),np.float32)),
            tokenizer=SimpleNamespace(encode=lambda text:SimpleNamespace(ids=[1,2,3]),
                                      decode=lambda ids,**kw:'left to right'),
            preprocess=lambda frames:{'pixels':frames},board=board,max_new_tokens=2,
            decoder=lambda *a:(np.zeros((4,448,448,3),np.uint8),
                               dict(actual_frame_times_s=[.5,1.5,2.5,3.5])))

    def test_raw_decode_and_vision_repeated_per_request(self):
        args=self.arguments()
        seen=[]
        def generator(model,hidden,**kw):
            seen.append(kw)
            return dict(status='PASS',valid_token_ids=[2,3])
        args['generator']=generator
        for _ in range(2):
            result=run_sys_request(**args)
            self.assertEqual(result['status'],'PASS')
            self.assertFalse(result['hardware_proof_verified'])
        self.assertIsNot(seen[0]['trace'],seen[1]['trace'])
        self.assertIsNone(seen[0]['cpu_linear_fallback'])
        self.assertEqual([x['name'] for x in seen[0]['trace'].stages],
            ['video_decode_resize','vision_preprocess','vision_forward','tokenization','embedding_lookup'])

    def test_input_failure_retained_without_calling_model(self):
        args=self.arguments()
        def fail(*a):raise ValueError('PTS absent')
        args['decoder']=fail
        args['generator']=lambda *a,**kw:self.fail('Must not infer after input failure')
        result=run_sys_request(**args)
        self.assertEqual(result['status'],'FAIL')
        self.assertIn('PTS absent',result['error'])
        self.assertEqual(result['partial_top_level_stages'][0]['name'],'video_decode_resize')

    def test_empty_text_not_passing(self):
        args=self.arguments()
        args['generator']=lambda *a,**kw:dict(status='PASS',valid_token_ids=[2])
        args['tokenizer'].decode=lambda *a,**kw:' '
        self.assertEqual(run_sys_request(**args)['status'],'FAIL')

    def test_raw_contract_uses_source_indices_and_native_tags(self):
        args=self.arguments();seen={}
        args['decoder']=lambda *a:(np.zeros((4,448,448,3),np.uint8),
            dict(actual_frame_times_s=[.5,1.5,2.5,3.5],selected_frame_indices=[6,18,30,42]))
        def vision(**kwargs):
            self.assertEqual(np.unique(kwargs['patch_positions'][:,0]).tolist(),[6,18,30,42])
            return np.zeros((784,2560),np.float32)
        def encode(text):seen['prompt']=text;return SimpleNamespace(ids=[1,2,3])
        args['vision']=vision;args['tokenizer'].encode=encode
        args['generator']=lambda *a,**kw:dict(status='PASS',valid_token_ids=[2,3])
        result=run_raw_contract_request(**args)
        self.assertEqual(result['status'],'PASS')
        self.assertIn('<0.5 seconds>',seen['prompt']);self.assertNotIn('<0.500 seconds>',seen['prompt'])
