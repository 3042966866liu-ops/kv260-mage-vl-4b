"""CPU fake-device failure-path checks; no FPGA/ABI/performance evidence."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import numpy as np
from owned_buffer_release import OwnedBufferRelease

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

class Retained(Exception):pass

class Buffer(np.ndarray):
    def __new__(cls,size,address,state):
        obj=np.zeros(size,np.uint8).view(cls);obj.physical_address=address
        obj.released=False;obj.state=state;return obj
    def sync_to_device(self):pass
    def sync_from_device(self):pass
    def freebuffer(self):
        if self.state['active']:raise AssertionError('Active fake DMA freed')
        self.released=True

class ProbeTest(unittest.TestCase):
    def exercise(self,*,failure=None):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);stable=root/'stable';(stable/'runtime').mkdir(parents=True)
            (stable/'runtime/board_runtime.py').write_text('# fake runtime',encoding='utf-8')
            pkg=root/'candidate';pkg.mkdir()
            for location in (pkg,stable):
                (location/'overlay').mkdir()
                (location/'overlay/m120_m89x2_t32.bit').write_bytes(b'fake bit fixture')
            (pkg/'HARDWARE_CLOSURE.json').write_text(json.dumps(dict(status='PASS_ALL_NEW_CIRCUIT_PREREQUISITES')),encoding='utf-8')
            (pkg/'build_packet.bin').write_bytes(bytes(16));(pkg/'build_golden.bin').write_bytes(bytes(16))
            (pkg/'BOARD_CASES.json').write_text(json.dumps(dict(files=[],stable_sources={},build_config='0x00010201')),encoding='utf-8')
            boot=root/'boot';boot.write_bytes(b'unchanged');cmd=root/'cmd';cmd.write_text('fixed',encoding='utf-8')
            state=dict(active=False,complete=False,expected=0,loads=[],buffers=[],waits=0,retained_export=False,low_memory_once=failure=='memory')
            fcntl=types.ModuleType('fcntl');fcntl.LOCK_EX=1;fcntl.LOCK_NB=2;fcntl.flock=lambda *a:None
            measurement=types.ModuleType('measurement')
            import hashlib
            measurement.sha256=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
            measurement.write_json=lambda path,data:Path(path).write_text(json.dumps(data),encoding='utf-8')
            helper=types.ModuleType('m341_build_id_gate');helper.ROOT=root;helper.STABLE=stable;helper.STABLE_SHA='fake-stable-sha'
            helper.verify_self=lambda *a:None;helper.service_stopped=lambda:dict(stopped=True)
            common=types.ModuleType('m120_board_common');common.KERNEL_NAME='kernel';common.DMA_NAME='dma'
            observer=types.ModuleType('m357_completion_observer')
            class ObservationFailure(Exception):
                def __init__(self):self.evidence={'active_timeout':True}
            observer.ObservationFailure=ObservationFailure
            base=types.ModuleType('board_runtime');base.__file__=str(stable/'runtime/board_runtime.py')
            base.LOW_END=0x80000000;base.REG_POINTERS=(16,24,32,40);base.REG_CONFIG=48;base.REG_AP_CTRL=0
            base.physical_address=lambda b:b.physical_address;base.write_u64=lambda *a:None
            def snapshot(*a):
                return dict(ap_ctrl=4 if not state['active'] else 1,ap_return=state['expected'] if state['complete'] else 0,
                    mm2s_dmasr=4098 if state['complete'] else 0,s2mm_dmasr=4098 if state['complete'] else 0,
                    kernel_read_error='',return_read_error='',dma_read_error='',mm2s_error=False,s2mm_error=False)
            base.transaction_snapshot=snapshot
            def wait_observed(reader,submitted,**kwargs):
                state['waits']+=1
                if failure=='timeout' and state['waits']==1:raise ObservationFailure()
                state['active']=False;state['complete']=True
                state['buffers'][-1][:]=1 if failure=='output' and state['waits']==1 else 0
                return snapshot(),dict(wait_ns=1000,expected_build=kwargs['expected_build_id'])
            observer.wait_observed=wait_observed
            pynq=types.ModuleType('pynq')
            class Channel:
                def transfer(self,*a,**kw):state['active']=True
            class Kernel:
                def write(self,*a):pass
            class Overlay:
                def __init__(self,path,**kw):
                    if state['active']:raise AssertionError('Active fake DMA Overlay replaced')
                    state['loads'].append(str(path));state['complete']=False
                    state['expected']=0x4d395832 if str(stable) in str(path) else 0x4d333537
                    self.kernel=Kernel();self.dma=types.SimpleNamespace(sendchannel=Channel(),recvchannel=Channel())
            def allocate(shape,**kw):
                obj=Buffer(shape[0],0x10000000+len(state['buffers'])*0x10000,state);state['buffers'].append(obj);return obj
            pynq.Overlay=Overlay;pynq.allocate=allocate;pynq.Clocks=types.SimpleNamespace(**{'fclk'+str(i)+'_mhz':100.0 for i in range(4)})
            exporter=types.ModuleType('m357_export_result')
            def emit(*a):state['retained_export']=True
            exporter.emit_saved=emit
            modules=dict(fcntl=fcntl,measurement=measurement,m341_build_id_gate=helper,m120_board_common=common,
                m357_completion_observer=observer,board_runtime=base,pynq=pynq,m357_export_result=exporter)
            with patch.dict(sys.modules,modules):
                spec=importlib.util.spec_from_file_location('m357_probe_tested',HERE/'m357_board_probe.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
                m.HERE=pkg;m.EVIDENCE=root/'evidence'
                original_path=Path
                m.Path=lambda value:boot if str(value)=='/boot/firmware/boot.scr.uimg' else cmd if str(value)=='/proc/cmdline' else original_path(value)
                def memory():
                    if state['low_memory_once']:state['low_memory_once']=False;return dict(CmaFree=1,MemAvailable=1<<30,Cached=0)
                    return dict(CmaFree=256<<20,MemAvailable=1<<30,Cached=0)
                m.meminfo=memory
                def sleep(*a):raise Retained()
                original_open=m.os.open;fake_lock_fds=[]
                def lock_open(path,*a,**kw):
                    fd=original_open(root/'execution.lock' if str(path)=='/tmp/tellme_kv260_execution.lock' else path,*a,**kw)
                    if str(path)=='/tmp/tellme_kv260_execution.lock':fake_lock_fds.append(fd)
                    return fd
                with patch.object(m.os,'open',lock_open),patch.object(m.os,'geteuid',return_value=0,create=True),patch.object(m.subprocess,'run',return_value=types.SimpleNamespace(returncode=0)),patch.object(m.time,'sleep',sleep),patch.object(sys,'argv',['probe','fake-sha','BuildID','--enable-candidate-gate']):
                    if failure=='timeout':
                        with self.assertRaises(Retained):m.main()
                        state['fake_lock_retained']=True
                        # Harness teardown only: the production path kept its lock.
                        for fd in fake_lock_fds:os.close(fd)
                    else:m.main()
            result=json.loads((root/'evidence/BuildID/BOARD_RESULT.json').read_text(encoding='utf-8'))
            return result,state
    def test_success_restores_stable(self):
        r,s=self.exercise();self.assertEqual(r['status'],'PASS_M357_BUILDID');self.assertTrue(r['stable_restored']);self.assertEqual(len(s['loads']),2);self.assertTrue(all(b.released for b in s['buffers']))
    def test_numeric_failure_safe_restore(self):
        r,s=self.exercise(failure='output');self.assertEqual(r['gate_return_code'],1);self.assertTrue(r['stable_restored']);self.assertFalse(r['unsafe_dma_buffers_retained']);self.assertEqual(len(s['loads']),2);self.assertEqual(r['physical_transactions_started'],2)
    def test_memory_failure_no_submission_then_restore(self):
        r,s=self.exercise(failure='memory');self.assertEqual(r['gate_return_code'],1);self.assertTrue(r['stable_restored']);self.assertEqual(r['physical_transactions_started'],1);self.assertTrue(all(b.released for b in s['buffers']))
    def test_active_timeout_retains_every_buffer_and_overlay(self):
        r,s=self.exercise(failure='timeout');self.assertEqual(r['status'],'FAIL_UNSAFE_RETAINED');self.assertTrue(s['retained_export']);self.assertTrue(s['fake_lock_retained']);self.assertEqual(len(s['loads']),1);self.assertTrue(all(not b.released for b in s['buffers']));self.assertEqual(r['physical_transactions_started'],1)
        diagnostic=r['failure_diagnostics'];self.assertEqual(diagnostic['chain_identity'],'minimal-zero')
        self.assertEqual((diagnostic['input_bytes'],diagnostic['output_bytes']),(16,16))
        self.assertEqual((diagnostic['ap_ctrl'],diagnostic['ap_return'],diagnostic['mm2s_dmasr'],diagnostic['s2mm_dmasr']),(1,0,0,0))
        self.assertTrue(diagnostic['unsafe_dma_buffers_retained'])

if __name__=='__main__':unittest.main()
