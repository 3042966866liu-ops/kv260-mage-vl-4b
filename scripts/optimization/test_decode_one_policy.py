import unittest
from decode_one_policy import execution_config, CANDIDATE_BUILD_ID, DECODE_ONE_BIT

class PolicyTest(unittest.TestCase):
    def test_valid_geometry_and_mode(self):
        for groups in (1,40,64,152):
            for bits in (2,4):
                for count in (1,10):
                    config=groups | bits<<8 | count<<16
                    for tokens in (1,2,31,32):
                        self.assertEqual(execution_config(config,build_id=CANDIDATE_BUILD_ID,
                            phase='prefill',valid_tokens=tokens),config)
                    self.assertEqual(execution_config(config,build_id=CANDIDATE_BUILD_ID,
                        phase='decode',valid_tokens=1),config|DECODE_ONE_BIT)
    def test_reject(self):
        defaults=dict(config=0x10428,build_id=CANDIDATE_BUILD_ID,phase='decode',valid_tokens=1)
        for changed in [dict(build_id=0x4D395832),dict(build_id=True),dict(config=True),
                        dict(config=0x10428|DECODE_ONE_BIT),dict(config=0),dict(config=0x10499),
                        dict(config=0x10328),dict(config=0xB0428),dict(phase='unknown'),
                        dict(valid_tokens=2),dict(valid_tokens=0),dict(valid_tokens=True)]:
            with self.subTest(changed=changed),self.assertRaises(ValueError):
                execution_config(**dict(defaults,**changed))

if __name__=='__main__': unittest.main()
