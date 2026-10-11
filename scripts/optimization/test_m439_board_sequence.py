"""Exercise complete real new control flow with fake DMA/fixtures, no hardware."""
import json,unittest
from m351_workflow import HERE
from test_m439_board_support import old
text=old
text=text.replace('def exercise(self,*,failure=None):', "def exercise(self,*,failure=None,mode='BuildID'):")
anchor="            boot=root/'boot';boot.write_bytes(b'unchanged');cmd=root/'cmd';cmd.write_text('fixed',encoding='utf-8')"
assert text.count(anchor)==1
insertion='''            spec=json.loads((pkg/'BOARD_CASES.json').read_text(encoding='utf-8'))
            (pkg/'baseline/overlay').mkdir(parents=True)
            (pkg/'baseline/overlay/m120_m89x2_t32.bit').write_bytes(b'fake M357 baseline fixture')
            spec.update(cases={},comparison_cases=['w2','w4','q_full'])
            for name in ('w2','w4','q_full','w4_chain'):
                for suffix in ('packet','golden'):(pkg/(name+'_'+suffix+'.bin')).write_bytes(bytes(16))
                (pkg/(name+'_weight.bin')).write_bytes(bytes(16))
                from measurement import sha256
                spec['cases'][name]=dict(name=name,packet=name+'_packet.bin',golden=name+'_golden.bin',config_u32='0x10228',window_bytes_per_port=16,windows=[dict(path=name+'_weight.bin',bytes=16,sha256=sha256(pkg/(name+'_weight.bin')))]*4)
            (pkg/'BOARD_CASES.json').write_text(json.dumps(spec),encoding='utf-8')
'''
# measurement fake is created later in the inherited harness, so use hashlib here.
insertion=insertion.replace('                from measurement import sha256\n','                import hashlib\n').replace("sha256(pkg/(name+'_weight.bin'))", "hashlib.sha256((pkg/(name+'_weight.bin')).read_bytes()).hexdigest()")
text=text.replace(anchor,insertion+anchor)
text=text.replace("state['expected']=0x4d395832 if str(stable) in str(path) else 0x4d343339", "state['expected']=0x4d395832 if str(stable) in str(path) else (0x4d333537 if 'baseline' in str(path) else 0x4d343339)")
text=text.replace("return snapshot(),dict(wait_ns=1000,expected_build=kwargs['expected_build_id'])", "return snapshot(),dict(wait_ns=(1000000 if state['expected']==0x4d333537 else 800000)+(200000 if failure=='no-gain' and state['expected']==0x4d343339 else 0),expected_build=kwargs['expected_build_id'])")
text=text.replace("['probe','fake-sha','BuildID','--enable-candidate-gate']", "['probe','fake-sha',mode,'--enable-candidate-gate','--prior-sha','fake-prior']")
text=text.replace("(root/'evidence/BuildID/BOARD_RESULT.json')", "(root/('evidence/'+mode+'/BOARD_RESULT.json'))")
anchor="            exporter=types.ModuleType('m439_export_result')"
assert text.count(anchor)==1
text=text.replace(anchor,"            if mode!='BuildID':\n                prior={'Descriptor':'BuildID','Chain':'Descriptor','Compare':'Chain'}[mode]\n                (root/('evidence/'+prior)).mkdir(parents=True)\n                (root/('evidence/'+prior+'/BOARD_RESULT.json')).write_text(json.dumps(dict(status='PASS_M439_'+prior.upper(),gate_return_code=0)),encoding='utf-8')\n                actual_sha=measurement.sha256\n                measurement.sha256=lambda path:'fake-prior' if str(path).endswith(prior+'\\\\BOARD_RESULT.json') or str(path).endswith(prior+'/BOARD_RESULT.json') else actual_sha(path)\n"+anchor)
ns=dict(__name__='m439_full_flow_fake',__file__=str(HERE/'test_m439_board_sequence.py'))
exec(compile(text,str(HERE/'test_m439_board_sequence.py')+':full-control-flow','exec'),ns)
Base=ns['ProbeTest']
class Sequence(unittest.TestCase):
    def exercise(self,**kwargs):return Base().exercise(**kwargs)
    def test_descriptor_sequence(self):
        r,s=self.exercise(mode='Descriptor');self.assertEqual(r['status'],'PASS_M439_DESCRIPTOR');self.assertEqual(r['physical_transactions_started'],2);self.assertTrue(all(b.released for b in s['buffers']))
    def test_two_format_chain_sequence(self):
        r,s=self.exercise(mode='Chain');self.assertEqual(r['status'],'PASS_M439_CHAIN');self.assertEqual(r['physical_transactions_started'],3);self.assertEqual([x.get('case') for x in r['transactions']],['q_full','w4_chain',None]);self.assertTrue(all(b.released for b in s['buffers']))
    def test_all_balanced_requests_and_restore(self):
        r,s=self.exercise(mode='Compare');self.assertEqual(r['status'],'PASS_M439_COMPARE');self.assertEqual(len(r['transactions']),217);self.assertEqual(len(r['allocations']),150);self.assertEqual(len(s['loads']),9);self.assertTrue(r['comparison']['all_cases_pass']);self.assertTrue(all(b.released for b in s['buffers']))
    def test_no_gain_still_safe_restore_and_failure(self):
        r,s=self.exercise(mode='Compare',failure='no-gain');self.assertEqual(r['status'],'FAIL_M439_COMPARE');self.assertFalse(r['chain_performance_pass']);self.assertEqual(r['gate_return_code'],1);self.assertTrue(r['stable_restored']);self.assertEqual(len(r['transactions']),217);self.assertTrue(all(b.released for b in s['buffers']))
    def test_chain_timeout_retains_owner(self):
        r,s=self.exercise(mode='Chain',failure='timeout');self.assertEqual(r['status'],'FAIL_UNSAFE_RETAINED');self.assertEqual(r['physical_transactions_started'],1);self.assertEqual(len(s['loads']),1);self.assertTrue(all(not b.released for b in s['buffers']));self.assertTrue(s['fake_lock_retained'])
if __name__=='__main__':unittest.main()
