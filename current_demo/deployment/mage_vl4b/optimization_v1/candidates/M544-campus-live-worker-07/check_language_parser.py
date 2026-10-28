"""Actual frozen parse/resolver, independent wires and six language families."""
import sys,json,hashlib,importlib.util,unittest,copy,platform,traceback,contextlib,io,time
from pathlib import Path
import numpy as np
TASK=Path(__file__).resolve().parent;ROOT=TASK;OPT=TASK
OLD=TASK
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(library,reference,out):
    sys.path[:0]=[str(TASK),str(OLD)]
    from language_parser_profiler import ParserAB
    args=list(sys.argv);sys.argv=[str(OLD/'check_runtime.py'),str(reference),str(library)]
    spec=importlib.util.spec_from_file_location('frozen_original_runtime_parser_tests',OLD/'check_runtime.py');prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
    prior.ParserAB=ParserAB
    families=('q','kv','qkv','attention_out','gate_up','mlp_down')
    class Tests(prior.Tests):
        def installed(self):
            r=prior.runtime();p=ParserAB(r,prior.expected['parse'],prior.expected['resolve'],native_library=library);p.install();return r,p
        def test_six_families_full_and_tail_uint32(self):
            r,p=self.installed();implementations={}
            for arm in ('A','B'):
                p.begin(arm)
                for family,width in zip(families,(4096,2048,6144,2560,9216,2560)):
                    for count in (1,31,32):
                        for shift in (0,3,6,10):
                            rows=(width+31)//32*8
                            c,w,t,expected=prior.fixture(width,rows,count,shift=shift);c['family']=family
                            buf=p.buffers[(count+shift)%2];buf[:len(w)]=w
                            self.assertTrue(r._parse_buffer(c,buf,t,1,count,shift));self.assertTrue(np.array_equal(t['gate'].view(np.uint32),expected.view(np.uint32)))
                            implementations[arm,family]=p.rows[-1]['implementation']
                p.end()
            self.assertTrue(all(implementations['B',f]=='C_gate_up' for f in families))
            self.assertTrue(all(implementations['A',f]==('C_gate_up' if f=='gate_up' else 'original_numpy') for f in families))
            p.restore()
        def test_six_family_retry_exhaustion_and_exceptions(self):
            original=prior.fixture
            try:
                for family in families:
                    def fixture(*args,**kwargs):
                        c,w,t,e=original(*args,**kwargs);c['family']=family;return c,w,t,e
                    prior.fixture=fixture;super().test_nonfinite_retry_and_exhaustion_original_resolver()
            finally:prior.fixture=original
        def test_head_not_switched_and_unknown_family_not_native(self):
            r,p=self.installed();p.begin('B')
            for family in ('lm_head','vision_fc1','unknown'):
                c,w,t,expected=prior.fixture();c['family']=family;r.output_buffer[:len(w)]=w
                self.assertTrue(r._parse_buffer(c,r.output_buffer,t,1,31,3));self.assertEqual(p.rows[-1]['implementation'],'original_numpy')
            p.end();p.restore()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests);stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);sys.argv=args
    report=dict(status='PASS_ALL_LANGUAGE_C_BIT_EXACT_COMPONENT_NOT_BOARD' if result.wasSuccessful() else 'FAIL_ALL_LANGUAGE_C_COMPONENT',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),test_log=stream.getvalue(),families=list(families),library_sha256=sha(library),reference_parser_sha256=sha(reference/'m455_output_parser02.py'),machine=platform.machine(),native_implementation='same frozen C core; C_gate_up label retained as implementation provenance',original_retry_AST_observer_only=True,model_forwards=0,Overlay=0,DMA=0,performance_conclusion=None)
    Path(out).open('x',encoding='utf8').write(json.dumps(report,indent=2)+'\n');print(stream.getvalue(),flush=True);print(report['status'],flush=True);return 0 if result.wasSuccessful() else 1
if __name__=='__main__':
    p=OPT/'candidates/M523-PS3072-ttft01/private_runtime'
    raise SystemExit(run(OLD/'gate_up_native_x86.so',p,OPT/'runs/M532-language-C-parser-host-02/COMPONENT.json'))
