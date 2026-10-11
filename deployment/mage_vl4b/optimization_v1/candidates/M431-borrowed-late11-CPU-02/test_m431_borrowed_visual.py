"""Explicit fake DMA/MMIO/policy, actual33MiB geometry; no FPGA evidence."""
import copy,hashlib,json,tempfile
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from m431_borrowed_visual import BorrowedVisual,SIZES

class Buffer(np.ndarray):
    def __new__(cls,size):
        x=np.zeros(size,np.uint8).view(cls);x.syncs=[];return x
    def sync_to_device(self):self.syncs.append('to')
    def sync_from_device(self):self.syncs.append('from')
    def freebuffer(self):raise AssertionError('Borrower attempted release')

def main():
    buffers=[Buffer(n) for n in SIZES];kernel=SimpleNamespace(writes=[],write=lambda reg,value:kernel.writes.append((reg,value)))
    rt=SimpleNamespace(staged_buffers=buffers[:4],input_buffer=buffers[4],output_buffer=buffers[5],output_buffer_alt=buffers[6],kernel=kernel,_programmed_config=123,_programmed_weight_addresses=(1,2,3,4))
    snapshot=dict(ap_ctrl=4,ap_return=0x4d333537,mm2s_dmasr=4098,s2mm_dmasr=4098,kernel_read_error='',return_read_error='',dma_read_error='')
    recv=SimpleNamespace(target=None,calls=[])
    def receive(b,nbytes):recv.target=b;recv.calls.append(nbytes)
    rt.dma=SimpleNamespace(recvchannel=SimpleNamespace(transfer=receive),sendchannel=SimpleNamespace(transfer=lambda b,nbytes:None))
    policy=SimpleNamespace(sealed=True,buffer_bytes=list(SIZES),ever=True,completed=True,active=False,build=0x4d333537,checks=[])
    policy.safe=lambda:not policy.active and policy.completed
    policy.capture=lambda label,check:policy.checks.append(label)
    payload=b'\x12'*131072
    def wait(*unused):recv.target[:len(payload)]=np.frombuffer(payload,np.uint8);return copy.deepcopy(snapshot)
    base=SimpleNamespace(REG_POINTERS=(16,28,40,52),REG_CONFIG=64,REG_AP_CTRL=0,physical_address=lambda b:id(b),write_u64=lambda k,r,v:k.write(r,v),wait_transaction=wait)
    chain=dict(input_bytes=163856,output_bytes=len(payload),config='0x10440');packet=b'\x34'*chain['input_bytes']
    ref={(13,'fc2',start,6):dict(input_bytes=len(packet),output_bytes=len(payload),packet_sha256=hashlib.sha256(packet).hexdigest(),raw_sha256=hashlib.sha256(payload).hexdigest()) for start in (0,32)}
    rejects=[]
    def reject(label,f):
        try:f()
        except (RuntimeError,ValueError,KeyError):rejects.append(label)
        else:raise AssertionError('Rejected condition accepted: '+label)
    def borrower(**kw):return BorrowedVisual(rt,policy,base,{},enabled=True,**kw)
    reject('default-off',lambda:BorrowedVisual(rt,policy,base,{}))
    reject('language-active',lambda:borrower(language_active=lambda:True))
    policy.sealed=False;reject('allocator-unsealed',borrower);policy.sealed=True
    policy.ever=False;reject('initial-zero-not-minimal-proof',borrower);policy.ever=True
    policy.active=True;reject('active-DMA',borrower);policy.active=False
    policy.completed=False;reject('completion-unproved',borrower);policy.completed=True
    with borrower(numerical_reference=ref) as owner:
        ids=owner.ids
        assert owner.submit(13,'fc2',chain,0,6,packet)==payload
        assert recv.target is buffers[5] and owner.ids==ids and not policy.active and policy.completed
        assert owner.rows[0]['completed_snapshot']==snapshot
        assert owner.submit(13,'fc2',chain,32,6,packet)==payload and recv.target is buffers[6]
        good_sha=ref[(13,'fc2',0,6)]['raw_sha256'];ref[(13,'fc2',0,6)]['raw_sha256']='0'*64
        reject('wire-SHA',lambda:owner.submit(13,'fc2',chain,0,6,packet));ref[(13,'fc2',0,6)]['raw_sha256']=good_sha
        reject('out-of-layer',lambda:owner.submit(24,'fc2',chain,0,6,packet))
        reject('out-of-row',lambda:owner.submit(13,'fc2',chain,392,6,packet))
        reject('packet-SHA',lambda:owner.submit(13,'fc2',chain,0,6,b'\x35'*len(packet)))
        reject('transfer-size',lambda:owner.submit(13,'fc2',dict(chain,input_bytes=1),0,6,packet))
        rt.output_buffer_alt=buffers[5];reject('buffer-identity',owner.check);rt.output_buffer_alt=buffers[6]
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent.parent) as temp:
            root=Path(temp);rows=[]
            for i in range(4):p=root/str(i);p.write_bytes(b'a'*16);rows.append(dict(relative_file=str(i),bytes=16,file_bytes=16,offset=0))
            assert owner.stage(13,'fc2',chain,rows,root)['bytes']==64
            reject('short-stage',lambda:owner.stage(13,'fc2',chain,[dict(rows[0],bytes=17)]+rows[1:],root))
    assert rt._programmed_config is None and rt._programmed_weight_addresses is None and not owner.entered
    rt._programmed_config=123
    reject('parse-reject-context',lambda:run_reject(borrower))
    assert rt._programmed_config is None and not policy.active
    bad=copy.deepcopy(snapshot);bad['ap_return']=0
    base.wait_transaction=lambda *unused:bad
    with borrower() as unsafe:
        reject('wrong-Build-retains-owner',lambda:unsafe.submit(13,'fc2',chain,0,6,packet))
    assert unsafe.retained and unsafe.entered and policy.active and not policy.completed
    policy.active=False;policy.completed=True;base.wait_transaction=wait
    base.wait_transaction=lambda *unused:(_ for _ in ()).throw(TimeoutError('EXPLICIT fake active timeout'))
    unsafe=borrower();unsafe.__enter__()
    try:unsafe.submit(13,'fc2',chain,0,6,packet)
    except TimeoutError:pass
    else:raise AssertionError('Timeout not propagated')
    unsafe.__exit__(None,None,None);assert unsafe.retained and policy.active
    assert all(int(b.nbytes)==n for b,n in zip(buffers,SIZES))
    result=dict(fake_DMA_MMIO_memory=True,real_array_geometry_bytes=sum(SIZES),extra_allocate_or_free_calls=0,negative_checks=rejects,timeout_preserves_original_owner=True,static_cache_invalidated=True,actual_PL_or_capacity_proven=False)
    print('M431_COMPONENT='+json.dumps(result,sort_keys=True))

def run_reject(factory):
    with factory():raise ValueError('EXPLICIT post-parse numeric rejection')

if __name__=='__main__':main()
