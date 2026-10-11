"""Synthetic export corruption/scope/lifecycle rejection; no hardware claim."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import unittest
from m357_board_collection import decode

ROOT=Path(__file__).resolve().parents[2]

def export(r):
    raw=(json.dumps(r,indent=2)+'\n').encode('utf-8');parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    return 'M357_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM357_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join('M357_RESULT_CHUNK='+str(i)+'/'+str(len(parts))+':'+base64.b64encode(p).decode('ascii')+'\n' for i,p in enumerate(parts))+'M357_DONE gate_rc='+str(r['gate_return_code'])+' export_rc=0\n'

def good():
    case=json.loads((ROOT/'tmp/m357_board_fixture_02/BOARD_CASES.json').read_text(encoding='utf-8'));files={r['path']:r for r in case['files']}
    rows=[];allocations=[];releases=[];memory=[]
    for i,(label,variant,build) in enumerate([('candidate-build-id','B',0x4d333537),('stable-restored-build-id','A',0x4d395832)]):
        packet=files['build_packet.bin'];golden=files['build_golden.bin']
        rows.append(dict(label=label,variant=variant,config=case['build_config'],input_bytes=packet['bytes'],output_bytes=golden['bytes'],packet_sha256=packet['sha256'],expected_sha256=golden['sha256'],output_sha256=golden['sha256'],full_output_exact=True,wait_ns=1000,completed_snapshot=dict(ap_ctrl=4,mm2s_dmasr=4098,s2mm_dmasr=4098,ap_return=build)))
        bank=[dict(label=label,bytes=144,address=0x10000000+i*0x100000+j*0x10000) for j in range(6)]
        allocations.extend(bank);releases.extend(reversed(bank));memory.extend([dict(CmaFree=128<<20,required_cma_free_bytes=64<<20)]*2)
    return dict(status='PASS_M357_BUILDID',gate_level='BuildID',build_id='0x4D333537',manifest_sha256='f'*64,package_verified=True,
        gate_return_code=0,full_model=False,video=False,promoted=False,errors=[],unsafe_dma_buffers_retained=False,safe_buffers_released=True,stable_restored=True,boot_unchanged=True,cmdline_unchanged=True,transactions=rows,physical_transactions_started=2,allocations=allocations,releases=releases,memory=memory)

class CollectionTest(unittest.TestCase):
    def test_original_op00_word_geometry(self):
        packet=(ROOT/'tmp/m357_board_fixture_02/build_packet.bin').read_bytes()
        descriptor=int.from_bytes(packet[:16],'little');rows=(descriptor>>32)&1023
        expected=rows//8*32*4*4*8
        self.assertEqual(expected,4096)
        self.assertEqual(len((ROOT/'tmp/m357_board_fixture_02/build_golden.bin').read_bytes()),expected)
        self.assertNotEqual(len((ROOT/'tmp/m357_board_fixture_01/build_golden.bin').read_bytes()),expected)
    def test_complete_original_bytes(self):
        r=good();digest,raw,restored=decode(export(r),'BuildID','f'*64);self.assertEqual(restored,r);self.assertEqual(digest,hashlib.sha256(raw).hexdigest())
    def test_failure_and_live_owner_export(self):
        r=dict(good(),status='FAIL_UNSAFE_RETAINED',gate_return_code=1,errors=['active timeout'],unsafe_dma_buffers_retained=True,safe_buffers_released=False,stable_restored=False)
        self.assertEqual(decode(export(r).split('M357_DONE')[0],'BuildID','f'*64)[2],r)
    def test_reject_protocol_corruption(self):
        text=export(good())
        invalid=[text.replace('M357_RESULT_CHUNK=1/','M357_RESULT_CHUNK=0/'),text.replace('M357_SAVED_GATE_RC=0','M357_SAVED_GATE_RC=1'),text.replace('export_rc=0','export_rc=1'),text+'M357_RESULT_SHA256='+'a'*64+'\n','\n'.join(line for line in text.splitlines() if not line.startswith('M357_RESULT_CHUNK=1/'))]
        for bad in invalid:
            with self.subTest(sample=bad[:70]),self.assertRaises((ValueError,KeyError)):decode(bad,'BuildID','f'*64)
    def test_reject_scope_lifecycle_and_wire_false_passes(self):
        mutators=[lambda r:r.update(promoted=True),lambda r:r.update(package_verified=False),lambda r:r.update(stable_restored=False),lambda r:r.update(boot_unchanged=False),lambda r:r.update(physical_transactions_started=1),lambda r:r['transactions'][0].update(full_output_exact=False),lambda r:r['transactions'][0].update(packet_sha256='0'*64),lambda r:r['transactions'][0]['completed_snapshot'].update(mm2s_dmasr=0),lambda r:r['transactions'][0]['completed_snapshot'].update(ap_return=0x4d395832),lambda r:r['transactions'][0].update(config='0x0'),lambda r:r['releases'].pop(),lambda r:r['allocations'].pop(),lambda r:r['memory'].pop(),lambda r:r['memory'][0].update(CmaFree=1)]
        for i,mutate in enumerate(mutators):
            r=copy.deepcopy(good());mutate(r)
            with self.subTest(case=i),self.assertRaises((ValueError,KeyError)):decode(export(r),'BuildID','f'*64)

if __name__=='__main__':unittest.main()
