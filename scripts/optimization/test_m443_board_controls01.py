"""Explicit fake-device/trace fixtures against actual M443 controls. No board evidence."""
import base64,copy,hashlib,importlib.util,json,os,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
from m351_workflow import ROOT,HERE
import m443_configuration01 as config
import m443_board_collection as collect
OUT=ROOT/'tmp/m443_board_controls_01'
FOUND=ROOT/'tmp/m443_board_support_01'
BIT=FOUND/'overlay/m120_m89x2_t32.bit'
APPLICATION=FOUND/'CONFIGURATION_APPLICATION.json'

def trace_record(pid,fail=None):
    text=''.join('python-'+str(pid)+' [0] '+e+': name=reserved '+fields+' count=1904\n => zynqmp_fpga_ops_write\n => '+stack+'\n' for e,fields,stack in [
        ('cma_alloc_start','','dma_alloc_attrs'),('cma_alloc_finish','pfn=0x1234','dma_alloc_attrs'),('cma_release','pfn=0x1234','dma_free_attrs')])
    if fail=='config_release':text=text[:text.index('python-'+str(pid)+' [0] cma_release')]
    if fail=='config_pfn':text=text.replace('cma_release: name=reserved pfn=0x1234','cma_release: name=reserved pfn=0x5678')
    t=dict(trace_text=text,trace_sha256=hashlib.sha256(text.encode()).hexdigest(),observer_errors=[],own_instance_removed=True,owned_instance_only=True,
        shared_root_configuration_changed=False,pid=pid,elapsed_trace_s=1,
        stats={f'cpu{i}':'overrun: 0\ncommit overrun: 0\ndropped events: 0\n' for i in range(4)})
    if fail=='config_loss':t['stats']['cpu0']='overrun: 1\ncommit overrun: 0\ndropped events: 0\n'
    if fail=='config_cleanup':t['own_instance_removed']=False
    return t

def fake_configuration(failure=None):
    """Replace only device/kernel counters/trace; actual configuration policy executes."""
    class FakeTrace:
        def __init__(self,evidence):self.created=False;self.evidence=evidence
        def prepare(self):self.created=True
        def start(self):pass
        def stop(self):
            t=trace_record(os.getpid(),failure)
            (self.evidence/'CMA_TRACE.txt').write_bytes(t['trace_text'].encode())
            return t
    class Tested(config.Configuration):
        def __init__(self,*a,**kw):
            calls=[]
            def counters():
                calls.append(1)
                return {'reserved:alloc_pages_success':100 if len(calls)==1 else (2005 if failure=='config_extra' else 2004),
                        'reserved:alloc_pages_fail':1 if failure=='config_failed' and len(calls)>1 else 0}
            super().__init__(*a,**kw,counters=counters,trace_factory=FakeTrace,kernel=lambda:'5.15.0-1027-xilinx-zynqmp',page_size=lambda:4096)
    return Tested

# Adapt original real failure harness against new source; fixture setup is explicit.
old=(HERE/'test_m357_board_probe.py').read_text(encoding='utf-8')
old=old.replace('m357','m443').replace('M357','M443').replace('0x4d333537','0x4d343433')
old=old.replace("HERE/'m443_board_probe.py'","OUT/'m443_board_probe.py'")
old=old.replace('tempfile.TemporaryDirectory()', "tempfile.TemporaryDirectory(dir=str(ROOT/'tmp'))")
old=old.replace("if __name__=='__main__':unittest.main()",'')
old=old.replace("diagnostic['chain_identity'],'minimal-zero'","diagnostic['chain_identity'],'candidate-build-id'")
old=old.replace("self.assertEqual(r['gate_return_code'],1);self.assertTrue(r['stable_restored']);self.assertEqual(r['physical_transactions_started'],1);self.assertTrue(all(b.released for b in s['buffers']))",
    "self.assertEqual(r['gate_return_code'],0);self.assertTrue(r['stable_restored']);self.assertEqual(r['physical_transactions_started'],2);self.assertTrue(all(b.released for b in s['buffers']))")
old=old.replace("(pkg/'HARDWARE_CLOSURE.json').write_text",
    "(pkg/'overlay/m120_m89x2_t32.bit').write_bytes(BIT.read_bytes())\n            (pkg/'CONFIGURATION_APPLICATION.json').write_bytes(APPLICATION.read_bytes())\n            (pkg/'HARDWARE_CLOSURE.json').write_text")
old=old.replace('m.HERE=pkg;m.EVIDENCE=',"m.Configuration=fake_configuration(failure)\n                m.HERE=pkg;m.EVIDENCE=")
old=old.replace("if failure=='timeout':\n                        with self.assertRaises(Retained):m.main()",
    "if failure=='timeout' or (failure and failure.startswith('config_')):\n                        with self.assertRaises(Retained):m.main()")
ns=dict(__name__='m443_explicit_fixture_failure_harness',__file__=str(HERE/'test_m443_board_controls01.py'),ROOT=ROOT,OUT=OUT,BIT=BIT,APPLICATION=APPLICATION,fake_configuration=fake_configuration)
exec(compile(old,'m443:actual-new-probe-original-failure-harness','exec'),ns)
ProbeTest=ns['ProbeTest']

class ConfigurationRetentionTest(ProbeTest):
    def test_all_unknown_configuration_paths_retain_without_DMA_or_rollback(self):
        for failure in ('config_extra','config_failed','config_release','config_pfn','config_loss','config_cleanup'):
            with self.subTest(failure=failure):
                r,s=self.exercise(failure=failure)
                self.assertEqual(r['status'],'FAIL_UNSAFE_RETAINED')
                self.assertTrue(r['unknown_configuration_ownership'])
                self.assertTrue(r['unsafe_dma_buffers_retained'])
                self.assertFalse(r.get('configuration_application_accepted',False))
                self.assertEqual(r['physical_transactions_started'],0)
                self.assertEqual(len(s['loads']),1)
                self.assertEqual(len(s['buffers']),0)
                self.assertTrue(s['retained_export'])
                self.assertTrue(s['fake_lock_retained'])

class ConfigurationComponentTest(unittest.TestCase):
    def test_actual_module_success_and_single_attempt(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as d:
            c=fake_configuration()(APPLICATION,'fixture-manifest',Path(d))
            overlay=object();calls=[]
            def loader(*a,**kw):calls.append((a,kw));return overlay
            self.assertIs(c.load(BIT,loader),overlay);self.assertFalse(c.unknown)
            self.assertEqual(len(calls),1);self.assertEqual(c.record['configuration_credits_granted'],0)
            with self.assertRaises(RuntimeError):c.load(BIT,loader)
            self.assertEqual(len(calls),1)
    def test_programming_exception_retains_unknown_ownership(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as d:
            c=fake_configuration()(APPLICATION,'fixture-manifest',Path(d))
            def loader(*a,**kw):raise RuntimeError('fixture programming exception')
            with self.assertRaises(RuntimeError):c.load(BIT,loader)
            self.assertTrue(c.unknown);self.assertFalse(c.record['overlay_returned'])
    def test_wrong_bit_rejected_before_trace_or_programming(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as d:
            c=fake_configuration()(APPLICATION,'fixture-manifest',Path(d))
            p=Path(d)/'unknown.bit';p.write_bytes(b'fixture')
            calls=[]
            with self.assertRaises(RuntimeError):c.load(p,lambda *a,**k:calls.append(1))
            self.assertFalse(c.unknown);self.assertFalse(calls);self.assertIsNone(c.record)
    def test_application_change_rejected(self):
        app=json.loads(APPLICATION.read_bytes());app['credits_granted']=1904
        with self.assertRaises(RuntimeError):config.validate_application(app)

# Fabricated lower receipts exercise actual strict collector; explicitly not board data.
prior_source=(HERE/'test_m441_board_support07.py').read_text(encoding='utf-8')
fabrication=prior_source[prior_source.index('def exported(r):'):prior_source.index('\nclass CollectionTest')]
fabrication=fabrication.replace('m441','m443').replace('M441','M443').replace('0x4D343431','0x4D343433')
fabrication=fabrication.replace("spec=json.loads((OUT/'BOARD_CASES.json').read_bytes())","spec=json.loads((FOUND/'BOARD_CASES.json').read_bytes())")
exec(compile(fabrication,'m443:explicit-fabricated-saved-receipts','exec'),globals())
original_success=success
def success(mode):
    r=original_success(mode)
    record=dict(bit_sha256=config.BIT,bit_bytes=7797914,pages=1904,kernel='5.15.0-1027-xilinx-zynqmp',page_size=4096,pid=123,
        application_sha256=config.sha(APPLICATION),manifest_sha256='fake-manifest',shell_closure_sha256=config.SHELL,
        observation_kind='same-process-kernel-CMA-trace',configuration_credits_granted=0,overlay_returned=True,
        before={'reserved:alloc_pages_success':100,'reserved:alloc_pages_fail':0},
        after={'reserved:alloc_pages_success':2004,'reserved:alloc_pages_fail':0},trace=trace_record(123))
    r.update(configuration_record=record,configuration_application_accepted=True,unknown_configuration_ownership=False)
    return r

class CollectorTest(unittest.TestCase):
    def check(self,r):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as d:
            base=Path(d);p=base/'runs/M443-buildid-board-01/BOARD_RESULT.json';p.parent.mkdir(parents=True)
            raw=json.dumps(success('BuildID')).encode();p.write_bytes(raw)
            r=copy.deepcopy(r)
            if r['gate_level']!='BuildID':
                r.setdefault('configuration_application_build_raw_sha256',hashlib.sha256(raw).hexdigest())
            with patch.object(collect,'BASE',base):
                return collect.decode(exported(r),r['gate_level'],'fake-manifest','fake-prior' if r['gate_level']!='BuildID' else None)
    def test_three_gates_accept_complete_fixture(self):
        for mode in collect.MODES:
            with self.subTest(mode=mode):self.assertEqual(self.check(success(mode))[2]['status'],'PASS_M443_'+mode.upper())
    def test_corruptions_rejected(self):
        mutations=[
            ('application',lambda r:r['configuration_record'].update(application_sha256='0'*64)),
            ('manifest',lambda r:r['configuration_record'].update(manifest_sha256='0'*64)),
            ('shell',lambda r:r['configuration_record'].update(shell_closure_sha256='0'*64)),
            ('unknown',lambda r:r.update(unknown_configuration_ownership=True)),
            ('not-accepted',lambda r:r.update(configuration_application_accepted=False)),
            ('extra-allocation',lambda r:r['configuration_record']['after'].update({'reserved:alloc_pages_success':2005})),
            ('resident-credit',lambda r:r['configuration_record'].update(configuration_credits_granted=1904)),
            ('wrong-build',lambda r:r['transactions'][0]['completed_snapshot'].update(ap_return=0x4d343431)),
            ('active-DMA',lambda r:r['transactions'][0]['completed_snapshot'].update(mm2s_dmasr=0)),
            ('release',lambda r:r['releases'].reverse()),
            ('floor',lambda r:r['memory'][0].update(fixed_cma_reserve_enforced=True)),
            ('omitted-output',lambda r:r['transactions'].pop(0)),
            ('origin-binding',lambda r:r.update(configuration_application_build_raw_sha256='0'*64)),
        ]
        for name,mutate in mutations:
            with self.subTest(name=name):
                r=success('Chain');mutate(r)
                with self.assertRaises((ValueError,RuntimeError,AssertionError)):self.check(r)
    def test_original_failure_collects_without_credit(self):
        r=success('BuildID');r.update(status='FAIL_UNSAFE_RETAINED',gate_return_code=1,errors=['explicit unknown-owner fixture'],configuration_application_accepted=False,unknown_configuration_ownership=True,unsafe_dma_buffers_retained=True)
        self.assertEqual(self.check(r)[2]['gate_return_code'],1)
        with self.assertRaises(ValueError):collect.decode(exported(r).replace('export_rc=0','export_rc=1'),'BuildID','fake-manifest')
    def test_compare_mode_disabled(self):
        with self.assertRaises(ValueError):collect.decode('','Compare','fake-manifest')
    def test_all_frozen_fixtures(self):
        spec=json.loads((FOUND/'BOARD_CASES.json').read_bytes())
        for row in spec['files']:
            self.assertEqual((FOUND/row['path']).stat().st_size,row['bytes'])
            self.assertEqual(config.sha(FOUND/row['path']),row['sha256'])

if __name__=='__main__':unittest.main(verbosity=2)
