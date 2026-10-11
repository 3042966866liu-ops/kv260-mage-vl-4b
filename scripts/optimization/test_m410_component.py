"""Real saved-byte/host-pack fixtures and explicitly fake DMA ownership paths."""
import hashlib,importlib.util,json,sys,tempfile,types
from pathlib import Path
from unittest.mock import patch
import numpy as np
from m410_saved_case import load_case,read_exact
from test_m409_ftz_reference import actual_host,fixture
from owned_buffer_release import OwnedBufferRelease

ROOT=Path(__file__).resolve().parents[2]

def main():
    host,_=actual_host();chain,windows=fixture('fc2');chain['module']='fc2'
    with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
        folder=Path(temp);values=np.ones((392,64),np.float32)
        np.save(folder/'gelu.npy',values,allow_pickle=False);arr=(folder/'gelu.npy').read_bytes()
        packet=host.pack_chain_input(chain,values[:32],chain['stage_base_words'],activation_scale_shift=6)
        golden=bytes(chain['output_bytes']);(folder/'fc2_000_shift6.packet').write_bytes(packet);(folder/'fc2_000_shift6.raw').write_bytes(golden)
        records=[]
        for i,w in enumerate(windows):
            p=folder/f'w{i}.bin';p.write_bytes(w)
            records.append(dict(path=p.name,relative_file=p.name,offset=0,bytes=len(w),file_bytes=len(w),sha256=hashlib.sha256(w).hexdigest()))
        r=dict(status='PASS_M409_SAVED_MLP_EXACT_SOFTWARE_REFERENCE',gate_return_code=0,local_exact_arithmetic_screen_pass=True,bindings_restored=True,visual_owner_closed=True,logical_reference_calls=26,
            reference_batches={'fc2':[dict(start=0,rows=32,selected_shift=6,packet_sha256=hashlib.sha256(packet).hexdigest(),raw_sha256=hashlib.sha256(golden).hexdigest())]},
            artifacts=[dict(path='gelu.npy',bytes=len(arr),sha256=hashlib.sha256(arr).hexdigest())],candidate_tensors={'gelu':dict(shape=[392,64],sha256=hashlib.sha256(values.tobytes()).hexdigest())},
            windows={'fc2':[{k:v for k,v in row.items() if k in ('path','offset','bytes','sha256')} for row in records]})
        blob=json.dumps(r).encode();(folder/'RESULT.json').write_bytes(blob)
        spec=dict(reference_directory=str(folder),reference_result_bytes=len(blob),reference_raw_sha256=hashlib.sha256(blob).hexdigest(),cases={'Descriptor':dict(part='fc2',chain=chain,shift=6,windows=records)})
        got=load_case(spec,'Descriptor',folder,host);assert got[1]==packet and got[2]==golden and got[3]==windows
        rejected=0
        for p in (folder/'RESULT.json',folder/'gelu.npy',folder/'fc2_000_shift6.packet',folder/'fc2_000_shift6.raw',folder/'w0.bin'):
            saved=p.read_bytes();p.write_bytes(saved[:-1]+bytes([saved[-1]^1]))
            try:load_case(spec,'Descriptor',folder,host)
            except RuntimeError:rejected+=1
            else:raise AssertionError('Corrupt saved input/weight accepted')
            p.write_bytes(saved)
        try:read_exact(folder/'w0.bin',len(windows[0])+1,'0'*64)
        except RuntimeError:rejected+=1
        else:raise AssertionError('Bad size accepted')
    # Load actual Owner class with explicit fake board helper imports only.
    helper=types.ModuleType('m341_build_id_gate');helper.verify_self=helper.service_stopped=lambda *a:None;helper.STABLE=ROOT;helper.STABLE_SHA='fake';helper.ROOT=ROOT
    common=types.ModuleType('m120_board_common');common.KERNEL_NAME='kernel';common.DMA_NAME='dma'
    fake_fcntl=types.ModuleType('fcntl') # Explicit Linux-only API substitute for Windows component test.
    observer_spec=importlib.util.spec_from_file_location('m357_completion_observer',ROOT/'deployment/mage_vl4b/optimization_v1/candidates/M357-private-activation-01/m357_completion_observer.py')
    observer=importlib.util.module_from_spec(observer_spec);observer_spec.loader.exec_module(observer)
    with patch.dict(sys.modules,dict(m341_build_id_gate=helper,m120_board_common=common,fcntl=fake_fcntl,m357_completion_observer=observer)):
        spec=importlib.util.spec_from_file_location('m410_actual_owner_test',ROOT/'scripts/optimization/m410_probe.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    modes=('success','wire-mismatch','recv-fail','send-fail','timeout','sync-fail','memory-fail')
    checks=[]
    for failure in modes:
        state=dict(active=False,done=False,freed=0,reads=0)
        class Buffer(np.ndarray):
            def __new__(cls,size):return np.zeros(size,np.uint8).view(cls)
            def sync_to_device(self):pass
            def sync_from_device(self):
                if failure=='sync-fail':raise RuntimeError('EXPLICIT sync fail')
            def freebuffer(self):
                assert not owner.active;state['freed']+=1
        class Channel:
            def __init__(self,kind):self.kind=kind
            def transfer(self,*a,**kw):
                state['active']=True
                if failure==self.kind+'-fail':raise RuntimeError('EXPLICIT '+self.kind+' submission fail')
        def snapshot(*a):
            state['reads']+=1
            return dict(ap_ctrl=4,ap_return=0x4d333537 if state['done'] else 0,mm2s_dmasr=4098 if state['done'] else 0,s2mm_dmasr=4098 if state['done'] else 0,mm2s_error=False,s2mm_error=False,kernel_read_error='',return_read_error='',dma_read_error='')
        base=types.SimpleNamespace(REG_POINTERS=(16,24,32,40),REG_CONFIG=128,REG_AP_CTRL=0,LOW_END=0x80000000,
            transaction_snapshot=snapshot,physical_address=lambda b:0x10000000,write_u64=lambda *a:None)
        r=dict(transactions=[],memory=[],allocations=[],releases=[],physical_transactions_started=0)
        owner=mod.Owner(base,r);owner.kernel=types.SimpleNamespace(write=lambda *a:None);owner.dma=types.SimpleNamespace(recvchannel=Channel('recv'),sendchannel=Channel('send'));owner.expected=0x4d333537
        owner.buffers=[Buffer(16) for _ in range(6)]
        for b in owner.buffers:b.freebuffer=OwnedBufferRelease(b.freebuffer,owner.safe,lambda:r['releases'].append(1))
        def wait(*a,**kw):
            if failure=='timeout':raise TimeoutError('EXPLICIT active fake timeout')
            state['done']=True;state['active']=False;owner.buffers[-1][:]=1 if failure=='wire-mismatch' else 0
            return snapshot(),dict(wait_ns=1000)
        with patch.object(mod,'meminfo',return_value=dict(CmaFree=(32 if failure=='memory-fail' else 256)<<20,MemAvailable=1<<30,Cached=0)),patch.object(mod,'wait_observed',side_effect=wait):
            try:owner.transact(bytes(16),bytes(16),1,'EXPLICIT fixture')
            except (RuntimeError,TimeoutError,MemoryError):assert failure!='success'
            else:assert failure=='success'
        if failure in ('recv-fail','send-fail','timeout'):
            assert owner.active and not owner.safe()
            try:owner.release()
            except RuntimeError:pass
            else:raise AssertionError('Unresolved fake DMA released')
            assert len(owner.buffers)==6 and state['freed']==0
        else:
            if failure=='memory-fail':assert not owner.ever and r['physical_transactions_started']==0
            assert owner.safe();kept=list(owner.buffers);owner.release();reads=state['reads']
            for b in kept:b.freebuffer()
            assert state['freed']==6 and state['reads']==reads
        checks.append(dict(case=failure,active_retention_or_safe_idempotent_release=True))
    print('M410_COMPONENT='+json.dumps(dict(actual_saved_bytes_and_original_pack=True,saved_corruption_rejected=rejected,
        actual_Owner_failure_cases=checks,all_buffers_retained_on_active_submission_failure=True,
        idempotent_release_no_extra_MMIO=True,explicit_fake_MMIO_DMA=True,board_or_performance_evidence=False)))
if __name__=='__main__':main()
