"""Fake devices only: retained owner, original identity, strict saved evidence."""
import base64,copy,hashlib,importlib.util,json,statistics,unittest
from pathlib import Path
from m351_workflow import ROOT,HERE
import m441_board_collection as collect
from m441_comparison import derive_comparison
OUT=ROOT/'tmp/m441_board_support_07'

# Reuse the actual proven failure harness against the actual new prepared source.
old=(HERE/'test_m357_board_probe.py').read_text(encoding='utf-8')
old=old.replace('m357','m441').replace('M357','M441').replace('0x4d333537','0x4d343431')
old=old.replace("HERE/'m441_board_probe.py'", "ROOT/'tmp/m441_board_support_07/m441_board_probe.py'")
old=old.replace('tempfile.TemporaryDirectory()', "tempfile.TemporaryDirectory(dir=str(ROOT/'tmp'))")
old=old.replace("self.assertEqual(r['gate_return_code'],1);self.assertTrue(r['stable_restored']);self.assertEqual(r['physical_transactions_started'],1);self.assertTrue(all(b.released for b in s['buffers']))", "self.assertEqual(r['gate_return_code'],0);self.assertTrue(r['stable_restored']);self.assertEqual(r['physical_transactions_started'],2);self.assertTrue(all(b.released for b in s['buffers']));self.assertEqual(r['memory'][0]['CmaFree'],1);self.assertFalse(r['memory'][0]['fixed_cma_reserve_enforced'])")
old=old.replace("if __name__=='__main__':unittest.main()", '')
old=old.replace("diagnostic['chain_identity'],'minimal-zero'", "diagnostic['chain_identity'],'candidate-build-id'")
ns=dict(__name__='m441_reused_failure_harness',__file__=str(HERE/'test_m441_board_support.py'))
exec(compile(old,str(HERE/'test_m441_board_support.py')+':original-failure-harness','exec'),ns)
ProbeTest=ns['ProbeTest']

def exported(r):
    raw=(json.dumps(r,indent=2)+'\n').encode();parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    return 'M441_RESULT_SHA256='+hashlib.sha256(raw).hexdigest()+'\nM441_SAVED_GATE_RC='+str(r['gate_return_code'])+'\n'+''.join('M441_RESULT_CHUNK='+str(i)+'/'+str(len(parts))+':'+base64.b64encode(part).decode()+'\n' for i,part in enumerate(parts))+'M441_DONE gate_rc='+str(r['gate_return_code'])+' export_rc=0\n'

def success(mode):
    spec=json.loads((OUT/'BOARD_CASES.json').read_bytes());fixtures={r['path']:r for r in spec['files']}
    rows=[];alloc=[];releases=[];memory=[];loads=[]
    def group(variant,label,name,block=0):
        case=spec['cases'].get(name) if name else None
        packet=fixtures[case['packet'] if case else 'build_packet.bin'];gold=fixtures[case['golden'] if case else 'build_golden.bin'];config=case['config_u32'] if case else spec['build_config']
        owns=[dict(label=label,bytes=16,address=0x10000000+i*4096) for i in range(6)];alloc.extend(owns);releases.extend(reversed(owns))
        memory.append(dict(label=label,CmaFree=10<<20,MemAvailable=1<<30,Cached=0,fixed_cma_reserve_enforced=False))
        for repeat in (range(-1,8) if mode=='Compare' and name else range(1)):
            snap=dict(ap_ctrl=4,ap_return=collect.BUILDS[variant],mm2s_dmasr=4098,s2mm_dmasr=4098,kernel_read_error='',return_read_error='',dma_read_error='',mm2s_error=False,s2mm_error=False)
            row=dict(label=label,variant=variant,input_bytes=packet['bytes'],output_bytes=gold['bytes'],config=config,packet_sha256=packet['sha256'],expected_sha256=gold['sha256'],output_sha256=gold['sha256'],full_output_exact=True,completed_snapshot=snap,wait_ns=(1000000 if variant=='A' else 900000)+block*10+repeat)
            if name:row.update(case=name,repeat=repeat,block=block,measured=repeat>=0)
            rows.append(row);memory.append(dict(label=label,CmaFree=10<<20,MemAvailable=1<<30,Cached=0,fixed_cma_reserve_enforced=False))
    def load(v):loads.append(dict(variant=v,clocks_mhz={'0':200.0,'1':0.0}))
    if mode=='BuildID':load('B');group('B','candidate-build-id',None)
    elif mode=='Descriptor':
        load('B')
        for name in ('w2','w4'):group('B','descriptor:'+name,name)
    elif mode=='Chain':
        load('B')
        for name in ('q_full','gate_up_full','mlp_down_full'):group('B','chain:'+name,name)
    else:
        for block,v in enumerate('ABBABAAB'):
            load(v)
            for name in spec['comparison_cases']:group(v,'compare:'+name,name,block)
    load('R');group('R','stable-restored-build-id',None)
    r=dict(status='PASS_M441_'+mode.upper(),gate_level=mode,build_id='0x4D343431',manifest_sha256='fake-manifest',gate_return_code=0,errors=[],full_model=False,video=False,promoted=False,package_verified=True,unsafe_dma_buffers_retained=False,safe_buffers_released=True,stable_restored=True,boot_unchanged=True,cmdline_unchanged=True,numerical_pass=mode!='BuildID',physical_transactions_started=len(rows),transactions=rows,allocations=alloc,releases=releases,memory=memory,overlay_loads=loads)
    if mode!='BuildID':r['prior_raw_sha256']='fake-prior'
    if mode=='Compare':r.update(comparison=derive_comparison(rows,loads,spec['comparison_cases']),balanced_orders=['A-B-B-A','B-A-A-B'],chain_performance_pass=True)
    return r

class CollectionTest(unittest.TestCase):
    def check(self,r):return collect.decode(exported(r),r['gate_level'],'fake-manifest','fake-prior' if r['gate_level']!='BuildID' else None)
    def test_all_lower_gates(self):
        for mode in collect.MODES:
            with self.subTest(mode=mode):self.assertEqual(self.check(success(mode))[2]['status'],'PASS_M441_'+mode.upper())
    def test_wrong_baseline_build_rejected(self):
        r=success('Compare');next(x for x in r['transactions'] if x['variant']=='A')['completed_snapshot']['ap_return']=0x4d395832
        with self.assertRaises(ValueError):self.check(r)
    def test_omitted_sample_rejected(self):
        r=success('Compare');r['transactions'].pop(5)
        with self.assertRaises(ValueError):self.check(r)
    def test_wrong_release_rejected(self):
        r=success('Chain');r['releases'].reverse()
        with self.assertRaises(ValueError):self.check(r)
    def test_active_dma_rejected(self):
        r=success('BuildID');r['transactions'][0]['completed_snapshot']['mm2s_dmasr']=0
        with self.assertRaises(ValueError):self.check(r)
    def test_silently_restored64_reserve_rejected(self):
        r=success('BuildID');r['memory'][0]['fixed_cma_reserve_enforced']=True
        with self.assertRaises(ValueError):self.check(r)
    def test_timing_falsification_rejected(self):
        r=success('Compare');r['comparison']['cases']['gate_up_full']['gain_fraction']=0.99
        with self.assertRaises(ValueError):self.check(r)
    def test_clock_difference_rejected(self):
        r=success('Compare');r['overlay_loads'][0]['clocks_mhz']['0']=210.0
        with self.assertRaises(ValueError):self.check(r)
    def test_gate_rc_preserved(self):
        r=dict(success('BuildID'),status='FAIL_UNSAFE_RETAINED',gate_return_code=1,errors=['active owner retained'],unsafe_dma_buffers_retained=True)
        self.assertEqual(self.check(r)[2]['gate_return_code'],1)
        with self.assertRaises(ValueError):collect.decode(exported(r).replace('export_rc=0','export_rc=1'),'BuildID','fake-manifest')
    def test_all_fixture_bytes(self):
        spec=json.loads((OUT/'BOARD_CASES.json').read_bytes())
        for r in spec['files']:self.assertEqual(hashlib.sha256((OUT/r['path']).read_bytes()).hexdigest(),r['sha256']);self.assertEqual((OUT/r['path']).stat().st_size,r['bytes'])
    def test_address_requests_not_masquerading_as_board_measurement(self):
        r=derive_comparison(success('Compare')['transactions'],success('Compare')['overlay_loads'],['gate_up_full','mlp_down_full'])
        self.assertFalse(r['pure_compute']);self.assertTrue(r['all_cases_pass'])
    def test_no_gain_closed(self):
        r=success('Compare')
        for row in r['transactions']:
            if row['variant']=='B':row['wait_ns']+=200000
        d=derive_comparison(r['transactions'],r['overlay_loads'],['gate_up_full','mlp_down_full']);self.assertFalse(d['all_cases_pass'])

if __name__=='__main__':unittest.main()
