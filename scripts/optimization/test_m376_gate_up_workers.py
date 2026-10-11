"""Real frozen NumPy parser and Futures; synthetic packets, explicit fake DMA."""
import ast
from collections import defaultdict
from concurrent.futures import Future,ThreadPoolExecutor
from dataclasses import dataclass
import json
from pathlib import Path
import threading
import time
from types import SimpleNamespace
import unittest
import numpy as np
from m376_gate_up_workers import GateUpWorkers

HERE=Path(__file__).resolve().parent
if (HERE/'m238_prefill_runtime.py').exists():FROZEN=HERE
else:FROZEN=HERE.parents[1]/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7/deployment/mage_vl4b/m242_m241_fixed_text_board_candidate'

def method(file,name,env):
    path=FROZEN/file;tree=ast.parse(path.read_text(encoding='utf-8'))
    node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name)
    node.decorator_list=[]
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),env)
    return env[name]

@dataclass
class Pending:
    future:Future
    values:object
    output_buffer:object
    token_start:int
    token_count:int
    initial_shift:int
    attempted_shifts:list

ENV=dict(np=np,time=time,ThreadPoolExecutor=ThreadPoolExecutor,_PendingBlock=Pending,
         base=SimpleNamespace(MIN_ACTIVATION_SCALE_SHIFT=0))
HALF=method('m231_prefill_runtime.py','_half_values_strided',ENV)
WIDTHS=method('m231_prefill_runtime.py','_output_widths',ENV)
ENV.update(_half_values_strided=HALF,_output_widths=WIDTHS)
FAMILY=method('m238_prefill_runtime.py','language_family_many',ENV)
RESOLVE=method('m236_prefill_runtime.py','_resolve_pending',ENV)
PARSE=method('m236_prefill_runtime.py','_parse_buffer',ENV)
INTO=method('m236_prefill_runtime.py','_parse_into_and_check',ENV)
RECORD=method('m230_prefill_runtime.py','_record_phase',ENV)
OLD_INTO=method('m231_prefill_runtime.py','_parse_into',ENV)

CHAIN=dict(layer=0,family='gate_up',chain_index=3,groups=1,output_bytes=8192,expected_macros=1,
 descriptors=[dict(module='gate_proj',row_start=0,valid_rows=32,rows_per_shard=8,output_bytes=4096),
              dict(module='up_proj',row_start=0,valid_rows=32,rows_per_shard=8,output_bytes=4096)])

def packet(chain,seed,bad=False):
    words=chain['output_bytes']//8;raw=np.zeros((words,8),np.uint8)
    values=(((np.arange(words*2,dtype=np.int64)+seed)%2046)-1023)
    bits=(values.astype(np.float32)/np.float32(257)).astype('<f2').view('<u2').reshape(words,2)
    raw[:,:2]=bits[:,0].reshape(-1,1).view(np.uint8).reshape(-1,2)
    raw[:,4:6]=bits[:,1].reshape(-1,1).view(np.uint8).reshape(-1,2)
    if bad:raw[0,:2]=np.frombuffer(np.float16(np.inf).tobytes(),np.uint8)
    return raw.tobytes()

class FakeDMA:
    language_family_many=FAMILY
    _resolve_pending=RESOLVE
    _parse_buffer=PARSE
    _parse_into_and_check=staticmethod(INTO)
    _record_phase=RECORD
    def __init__(self,chain=CHAIN,retry=False):
        self.chain=chain;self.retry=retry;self.output_buffer=np.empty(chain['output_bytes'],np.uint8)
        self.output_buffer_alt=np.empty_like(self.output_buffer)
        self.weight_mode='staged-low-cma';self.language_layout=object()
        self.family_stage_count=defaultdict(int);self.family_output_allocations=defaultdict(int)
        self.family_t32_blocks=defaultdict(int);self.family_phase_ms=defaultdict(lambda:defaultdict(float))
        self.phase_ms=defaultdict(float);self.phase_calls=defaultdict(int)
        self.pack_prefetch_submissions=self.pack_prefetch_wait_ms=self.pack_prefetch_compute_ms=0
        self.pipeline_reuse_waits=self.pipeline_submissions=self.pipeline_retry_launches=0
        self.fused_nonfinite_detections=self.scale_retry_count=0
        self.host_calls=self.logical_calls=self.expected_macros=self.logical_expected_macros=0
        self.scale_shift_counts=defaultdict(int);self.scale_attempts=[];self.stages=0;self.launches=[]
    def _language_chain(self,layer,family):
        c=dict(self.chain,layer=layer,family=family);return c
    def _family_key(self,c):return str(c['layer'])+':'+c['family']
    def _stage(self,*a):self.stages+=1;return ['fake-weight']*4,0
    def _initial_scale_shift(self,x):return 2
    def _prepare_block(self,c,x,start,offset,shift):
        return SimpleNamespace(values=x,token_start=start,token_count=len(x),initial_shift=shift,pack_ms=0.0)
    def _emit(self,c,x,out,shift):
        seed=int(x[0,0]);bad=self.retry and seed in (0,32) and shift==2
        out[:]=np.frombuffer(packet(c,seed,bad),np.uint8)
        self.launches.append((seed,shift,id(out)));self.host_calls+=1;self.expected_macros+=c['expected_macros']
    def _launch_prepacked(self,c,p,weights,out):self._emit(c,p.values,out,p.initial_shift)
    def _launch_once(self,c,x,weights,out,offset,shift):self._emit(c,x,out,shift)
    _accept_shift=method('m236_prefill_runtime.py','_accept_shift',ENV)

def inputs(n,width=64):
    x=np.zeros((n,width),np.float32);x[:,0]=np.arange(n);return x

def equal(a,b):
    assert a.keys()==b.keys()
    for name in a:np.testing.assert_array_equal(a[name].view(np.uint32),b[name].view(np.uint32))

class Tests(unittest.TestCase):
    def tearDown(self):
        ENV['_half_values_strided']=HALF
        ENV['ThreadPoolExecutor']=ThreadPoolExecutor
        self.assertFalse(any(t.name.startswith(('m238-parse','m238-pack')) for t in threading.enumerate()))
    def run_variant(self,n,workers,retry=False,family='gate_up',chain=CHAIN):
        r=FakeDMA(chain,retry=retry);scope=GateUpWorkers(r,workers=workers,enabled=True)
        with scope:answer=r.language_family_many(0,family,inputs(n,chain['groups']*64))
        self.assertTrue(scope.report()['bindings_restored']);return r,answer
    def test_default_disabled_and_invalid_width(self):
        for kw in ({},{'enabled':True,'workers':3},{'enabled':True,'workers':True}):
            r=FakeDMA()
            with self.assertRaises(ValueError):GateUpWorkers(r,**kw)
            self.assertNotIn('language_family_many',vars(r))
    def test_source_drift_rejected_before_patch(self):
        r=FakeDMA();r._resolve_pending=lambda *a:None
        with self.assertRaises(RuntimeError):GateUpWorkers(r,enabled=True)
        self.assertNotIn('language_family_many',vars(r))
    def test_exact_tail_sizes_and_retry_counts(self):
        for n in (1,17,32,33,64,65,159):
            for retry in (False,True):
                a,reference=self.run_variant(n,1,retry)
                b,actual=self.run_variant(n,2,retry)
                equal(actual,reference)
                for name in ('scale_attempts','logical_calls','host_calls','scale_retry_count','pipeline_retry_launches',
                             'fused_nonfinite_detections','phase_calls','family_output_allocations','family_t32_blocks'):
                    self.assertEqual(getattr(a,name),getattr(b,name),name)
                self.assertEqual(b.stages,1)
                self.assertEqual(b.phase_calls['parse'],b.host_calls)
    def test_independent_original_parser_reference(self):
        r,out=self.run_variant(159,2,True)
        expected={k:np.full_like(v,np.nan) for k,v in out.items()}
        for start in range(0,159,32):
            OLD_INTO(CHAIN,packet(CHAIN,start),expected,start,min(32,159-start),1 if start in (0,32) else 2)
        equal(out,expected)
    def test_two_real_tasks_overlap_and_write_disjoint_rows(self):
        barrier=threading.Barrier(2);lock=threading.Lock();active=0;maximum=0;seen=set()
        def halves(raw):
            nonlocal active,maximum
            # First descriptor per output buffer enters a real two-thread barrier.
            identity=id(raw.obj)
            with lock:
                first=identity not in seen;seen.add(identity);active+=1;maximum=max(maximum,active)
            try:
                if first:barrier.wait(3)
                return HALF(raw)
            finally:
                with lock:active-=1
        ENV['_half_values_strided']=halves
        r,out=self.run_variant(64,2)
        self.assertEqual(maximum,2);self.assertEqual(len(seen),2)
        self.assertEqual(r.phase_calls['parse'],2)
        self.assertTrue(all(np.isfinite(v).all() for v in out.values()))
        ENV['_half_values_strided']=HALF
        expected={k:np.full_like(v,np.nan) for k,v in out.items()}
        for start in (0,32):OLD_INTO(CHAIN,packet(CHAIN,start),expected,start,32,2)
        equal(out,expected)
    def test_dma_reuse_only_after_future_and_retry_confirmation(self):
        pending={};checks=[]
        class TrackingPool(ThreadPoolExecutor):
            def submit(self,fn,*args,**kw):
                f=super().submit(fn,*args,**kw)
                if self._thread_name_prefix=='m238-parse':pending[id(args[1])]=f
                return f
        class CheckedDMA(FakeDMA):
            def _emit(self,c,x,out,shift):
                if id(out) in pending:
                    checks.append(pending[id(out)].done())
                    if not pending[id(out)].done():raise AssertionError('DMA overwrote active parser')
                return super()._emit(c,x,out,shift)
        ENV['ThreadPoolExecutor']=TrackingPool
        r=CheckedDMA(retry=True);scope=GateUpWorkers(r,enabled=True)
        with scope:r.language_family_many(0,'gate_up',inputs(159))
        self.assertEqual(r.pipeline_retry_launches,2)
        self.assertEqual(len(checks),5);self.assertTrue(all(checks))
    def test_retry_one_output_while_other_parser_is_active(self):
        second_started=threading.Event();allow_second=threading.Event();observed=[]
        r=FakeDMA(retry=True);old_launch=r._launch_once
        def retry_launch(*a):
            observed.append(second_started.is_set() and not allow_second.is_set())
            allow_second.set();return old_launch(*a)
        r._launch_once=retry_launch
        def halves(raw):
            if raw.obj is r.output_buffer_alt and not allow_second.is_set():
                second_started.set()
                if not allow_second.wait(3):raise RuntimeError('Retry ownership probe deadline')
            if raw.obj is r.output_buffer and not allow_second.is_set():
                if not second_started.wait(3):raise RuntimeError('Second parser not started')
            return HALF(raw)
        ENV['_half_values_strided']=halves
        scope=GateUpWorkers(r,enabled=True)
        with scope:out=r.language_family_many(0,'gate_up',inputs(64))
        self.assertTrue(observed[0]);self.assertEqual(r.pipeline_retry_launches,2)
        self.assertTrue(all(np.isfinite(v).all() for v in out.values()))
    def test_phase_counts_with_forced_interleaving(self):
        class SlowDict(defaultdict):
            def __getitem__(self,key):
                value=super().__getitem__(key)
                if key=='parse':time.sleep(.001)
                return value
        r=FakeDMA();r.phase_calls=SlowDict(int)
        with GateUpWorkers(r,enabled=True):
            for _ in range(8):r.language_family_many(0,'gate_up',inputs(159))
        self.assertEqual(r.phase_calls['parse'],40)
    def test_actual_largest_gate_up_geometry(self):
        fixture=HERE/'GATE_UP_FIXTURE.json'
        if fixture.exists():chain=json.loads(fixture.read_text(encoding='utf-8'))['chain']
        else:
            contract=HERE.parents[1]/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json'
            chains=json.loads(contract.read_text(encoding='utf-8'))['chains']
            chain=max((c for c in chains if c.get('family')=='gate_up'),key=lambda c:c['output_bytes'])
        a,expected=self.run_variant(159,1,True,chain=chain)
        b,actual=self.run_variant(159,2,True,chain=chain)
        equal(actual,expected);self.assertEqual(a.scale_attempts,b.scale_attempts)
        self.assertEqual(b.phase_calls['parse'],b.host_calls)
    def test_non_gate_up_stays_original_single_worker(self):
        r=FakeDMA();scope=GateUpWorkers(r,enabled=True)
        with scope:out=r.language_family_many(0,'q',inputs(159))
        self.assertEqual(scope.report()['gate_up_calls'],0)
        self.assertEqual(r.phase_calls['parse'],5)
    def test_parser_exception_joins_workers_restores_bindings(self):
        r=FakeDMA();r.language_family_many=r.language_family_many;r._record_phase=r._record_phase
        prior=(r.language_family_many,r._record_phase)
        def fail(raw):raise ValueError('explicit real parser primitive failure')
        ENV['_half_values_strided']=fail
        scope=GateUpWorkers(r,enabled=True)
        with self.assertRaisesRegex(ValueError,'primitive failure'):
            with scope:r.language_family_many(0,'gate_up',inputs(159))
        self.assertIs(r.language_family_many,prior[0]);self.assertIs(r._record_phase,prior[1])
        self.assertTrue(scope.restored)
    def test_repeated_requests_keep_only_two_outputs(self):
        r=FakeDMA();ids=(id(r.output_buffer),id(r.output_buffer_alt));scope=GateUpWorkers(r,enabled=True)
        with scope:
            for _ in range(12):r.language_family_many(0,'gate_up',inputs(159))
        self.assertEqual(ids,(id(r.output_buffer),id(r.output_buffer_alt)))
        self.assertEqual(r.phase_calls['parse'],60)
        self.assertEqual(scope.report()['gate_up_calls'],12)
        self.assertFalse(any(isinstance(v,Future) for v in vars(scope).values()))

if __name__=='__main__':unittest.main()
