"""CPU-only numerical and scheduler tests using the actual frozen source AST."""
import ast
import concurrent.futures
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
import threading
import time
import types
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
from gate_up_profiler import ParserAB, source_sha

HERE = Path(__file__).resolve().parent
PACKAGE = Path(sys.argv[1]) if len(sys.argv)>1 else Path(r'C:\Users\30429\Desktop\TeLLMe_FPGA_2026\outputs\M455_7911s_code_20261023\M455_7911s_code\board_current419')
PRIVATE = PACKAGE
spec = importlib.util.spec_from_file_location('frozen_dense_parser', PRIVATE/'m455_output_parser02.py')
parser = importlib.util.module_from_spec(spec); spec.loader.exec_module(parser)
source = PRIVATE/'m236_prefill_runtime.py'
tree = ast.parse(source.read_text(encoding='utf-8'))
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name=='M236PrefillRuntime')
space = dict(np=np,time=time,M231PrefillRuntime=object,Future=concurrent.futures.Future,_PendingBlock=object,
             parse_into_and_check=parser.parse_into_and_check,
             base=types.SimpleNamespace(MIN_ACTIVATION_SCALE_SHIFT=0))
exec(compile(ast.Module(body=[cls],type_ignores=[]),str(source),'exec'),space)
Runtime = space['M236PrefillRuntime']
expected = dict(parse=source_sha(Runtime._parse_buffer),resolve=source_sha(Runtime._resolve_pending))


def fixture(valid=63, rows=16, count=31, start=1, shift=3):
    # Independent logical matrix -> documented block/token/shard/pair/lane wire.
    rng=np.random.default_rng(20261023)
    logical=rng.integers(-200,201,size=(32,4*rows)).astype(np.float16)
    wire=logical.reshape(32,4,rows//8,4,2).transpose(2,0,1,3,4).copy()
    desc=dict(rows_per_shard=rows,output_bytes=wire.nbytes,valid_rows=valid,module='gate',row_start=2)
    chain=dict(output_abi='m455-dense-fp16-block-token-shard-pair-v1',expected_build_id=0x4D343535,
               output_bytes=wire.nbytes,descriptors=[desc],family='gate_up',chain_index=0,layer=1)
    targets={'gate':np.full((start+count+1,valid+4),-777,dtype=np.float32)}
    reference=targets['gate'].copy()
    reference[start:start+count,2:2+valid]=np.ldexp(logical[:count,:valid].astype(np.float32),-shift)
    return chain,wire.view(np.uint8).ravel(),targets,reference


def runtime(capacity=32*4*2304*2*2):
    r=Runtime.__new__(Runtime)
    r.output_buffer=np.zeros(capacity,dtype=np.uint8)
    r.output_buffer_alt=np.zeros_like(r.output_buffer)
    r._family_key=lambda c:f"{c.get('layer')}:{c.get('family','lm_head')}"
    r.phase=[]
    r._record_phase=lambda c,p,t:r.phase.append((p,time.perf_counter()-t))
    r.fused_nonfinite_detections=r.pipeline_retry_launches=r.scale_retry_count=0
    r.scale_attempts=[];r.accepted=[]
    r._accept_shift=lambda *args:r.accepted.append(args)
    return r


class Tests(unittest.TestCase):
    def installed(self):
        r=runtime();p=ParserAB(r,expected['parse'],expected['resolve'],native_library=sys.argv[2]);p.install()
        return r,p

    def test_geometry_padding_and_all_shifts(self):
        r,p=self.installed()
        scratch_ids=tuple(map(id,p.scratch))
        for variant in ('A','B'):
            p.begin(variant)
            for rows,valid in ((8,1),(8,7),(8,8),(8,9),(8,31),(8,32),(16,63),(16,64),(2304,9216)):
                for count in (1,31,32):
                    for shift in (0,1,6,10):
                        c,w,t,reference=fixture(valid,rows,count,shift=shift)
                        slot=(count+shift)&1;b=p.buffers[slot];b[:len(w)]=w
                        self.assertTrue(r._parse_buffer(c,b,t,1,count,shift))
                        self.assertTrue(np.array_equal(t['gate'].view(np.uint32),reference.view(np.uint32)))
            result=p.end();self.assertTrue(result['successful'])
            self.assertEqual(result['calls'],108)
            self.assertGreater(result['copy_s'],0)
            self.assertEqual(tuple(map(id,p.scratch)),scratch_ids)
        p.restore();self.assertNotIn('_parse_buffer',r.__dict__)

    def test_nonfinite_retry_and_exhaustion_original_resolver(self):
        for variant in ('A','B'):
            r,p=self.installed();p.begin(variant)
            c,w,t,_=fixture(64,16,32,shift=1)
            good=w.copy();w.view(np.float16)[0]=np.inf;r.output_buffer[:len(w)]=w
            finite=r._parse_buffer(c,r.output_buffer,t,1,32,1)
            self.assertFalse(finite)
            def launch(chain,values,buffers,output,base,shift):
                self.assertEqual(shift,0);output[:len(good)]=good
            r._launch_once=launch
            future=concurrent.futures.Future();future.set_result(False)
            pending=types.SimpleNamespace(future=future,values=np.ones((32,1),np.float32),
                output_buffer=r.output_buffer,token_start=1,token_count=32,initial_shift=1,attempted_shifts=[1])
            r._resolve_pending(c,[],t,0,pending)
            self.assertEqual(pending.attempted_shifts,[1,0]);self.assertEqual(r.pipeline_retry_launches,1)
            self.assertEqual(len(r.accepted),1)
            result=p.end();self.assertEqual(len(result['waits']),1);self.assertEqual(result['calls'],2)
            p.begin(variant)
            pending.attempted_shifts=[0]
            with self.assertRaises(FloatingPointError):r._resolve_pending(c,[],t,0,pending)
            self.assertEqual(pending.attempted_shifts,[0]);p.end();p.restore()

    def test_padding_nonfinite_ignored(self):
        r,p=self.installed()
        for variant in ('A','B'):
            p.begin(variant)
            c,w,t,reference=fixture(1,8,1,shift=0)
            logical=w.view(np.float16).reshape(1,32,4,4,2).transpose(1,2,0,3,4)
            good=logical[0,0,0,0,0];logical[:]=np.nan;logical[0,0,0,0,0]=good
            r.output_buffer[:len(w)]=w
            self.assertTrue(r._parse_buffer(c,r.output_buffer,t,1,1,0))
            self.assertTrue(np.array_equal(t['gate'].view(np.uint32),reference.view(np.uint32)));p.end()
        p.restore()

    def test_different_slots_independent_and_same_slot_rejected(self):
        r,p=self.installed();p.begin('B')
        c,w,t,_=fixture();r.output_buffer[:len(w)]=w;r.output_buffer_alt[:len(w)]=w
        entered=threading.Event();release=threading.Event();real=p.native_parser.parse
        def blocking(*args):entered.set();self.assertTrue(release.wait(3));return real(*args)
        p.native_parser.parse=blocking
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            future=pool.submit(r._parse_buffer,c,r.output_buffer,t,1,31,3)
            self.assertTrue(entered.wait(3))
            with self.assertRaises(RuntimeError):r._parse_buffer(c,r.output_buffer,t,1,31,3)
            with self.assertRaises(RuntimeError):p.end()
            p.native_parser.parse=real
            other={'gate':np.full_like(t['gate'],-777)}
            self.assertTrue(r._parse_buffer(c,r.output_buffer_alt,other,1,31,3))
            self.assertFalse(np.may_share_memory(*p.scratch));release.set();self.assertTrue(future.result(3))
        p.end();p.restore()

    def test_error_propagation_and_source_guard(self):
        r,p=self.installed();p.begin('B')
        c,w,t,_=fixture();bad=dict(c,output_bytes=r.output_buffer.nbytes+1)
        with self.assertRaises(RuntimeError):r._parse_buffer(bad,r.output_buffer,t,1,31,3)
        self.assertFalse(p.end()['successful']);p.restore()
        with self.assertRaises(RuntimeError):ParserAB(r,'0'*64,expected['resolve'],native_library=sys.argv[2])
        r,p=self.installed();p.begin('A');f=concurrent.futures.Future();f.set_exception(ValueError('original error'))
        with self.assertRaisesRegex(ValueError,'original error'):p.future_result(c,f)
        self.assertFalse(p.end()['successful']);p.restore()


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report=dict(scope='CPU_ONLY_REAL_PARSER_AND_ORIGINAL_RETRY_AST_NO_DMA_OR_BOARD',
        tests=result.testsRun,passed=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),
        original_method_sha256=expected,board_forwards=0,performance_conclusion=None)
    Path(sys.argv[3]).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
