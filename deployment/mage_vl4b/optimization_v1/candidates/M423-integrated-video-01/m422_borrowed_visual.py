"""Default-off visual transactions borrow the original seven language buffers.

No allocation, buffer release or Overlay operation is available in this adapter.
The original runtime and StagePolicy remain the resource and completion owners.
"""
import hashlib
import numpy as np
from board_safety import safe_to_release

SIZES=(6963200,6963200,6963200,6963200,389152,2621440,2621440)

class BorrowedVisual:
    def __init__(self,runtime,policy,base,record,*,enabled=False,numerical_reference=None,language_active=lambda:False):
        if enabled is not True:raise RuntimeError('Borrowed visual disabled by default')
        self.runtime,self.policy,self.base,self.record=runtime,policy,base,record
        self.buffers=tuple(runtime.staged_buffers)+(runtime.input_buffer,runtime.output_buffer,runtime.output_buffer_alt)
        self.ids=tuple(id(x) for x in self.buffers);self.language_active=language_active
        self.reference=numerical_reference;self.rows=[];self.staging=[];self.entered=False;self.retained=False
        self.check()
    def check(self):
        current=tuple(self.runtime.staged_buffers)+(self.runtime.input_buffer,self.runtime.output_buffer,self.runtime.output_buffer_alt)
        if tuple(id(x) for x in current)!=self.ids or tuple(int(x.nbytes) for x in current)!=SIZES:raise RuntimeError('Original seven DMA identities/geometry changed')
        if not self.policy.sealed or tuple(self.policy.buffer_bytes)!=SIZES or self.language_active():raise RuntimeError('Sealed idle language scope required')
        if not self.policy.ever or not self.policy.completed or not self.policy.safe():raise RuntimeError('Same-overlay completed transaction proof required')
    def __enter__(self):
        if self.entered:raise RuntimeError('Borrow scope already active')
        self.check();self.entered=True;return self
    def stage(self,index,part,chain,windows,root):
        from m411_mlp_binding import stage_windows
        if not self.entered or index not in (12,13) or part not in ('fc1','fc2') or len(windows)!=4:raise RuntimeError('Only layers12+13 four Linear stages')
        self.check()
        if any(x['bytes']>b.nbytes for x,b in zip(windows,self.buffers[:4])):raise ValueError('Visual staged window exceeds borrowed port')
        self.policy.capture('before-visual-stage:'+str(index)+':'+part,True)
        row=stage_windows(self,part,windows,root);row['layer']=index;self.staging.append(row)
        self.policy.capture('after-visual-stage:'+str(index)+':'+part,True)
        return row
    def submit(self,index,part,chain,start,shift,packet):
        if not self.entered or index not in (12,13) or part not in ('fc1','fc2') or start not in range(0,392,32):raise RuntimeError('Visual batch escaped fixed scope')
        self.check();key=(index,part,start,shift)
        expected=None if self.reference is None else self.reference[key]
        if len(packet)!=chain['input_bytes'] or len(packet)>self.buffers[4].nbytes or chain['output_bytes']>min(x.nbytes for x in self.buffers[5:]):raise ValueError('Borrowed DMA transfer size differs')
        if expected is not None and (len(packet)!=expected['input_bytes'] or hashlib.sha256(packet).hexdigest()!=expected['packet_sha256']):raise RuntimeError('Saved combination full packet SHA differs')
        self.policy.capture('before-visual-submit:'+str(index)+':'+part,True)
        tx=self.buffers[4];rx=self.buffers[5+len(self.rows)%2]
        tx[:len(packet)]=np.frombuffer(packet,np.uint8);tx.sync_to_device();rx[:chain['output_bytes']]=0xa5;rx.sync_to_device()
        for register,b in zip(self.base.REG_POINTERS,self.buffers[:4]):self.base.write_u64(self.runtime.kernel,register,self.base.physical_address(b))
        self.runtime.kernel.write(self.base.REG_CONFIG,int(chain['config'],16))
        pending=dict(layer=index,part=part,start=start,shift=shift,input_bytes=len(packet),output_bytes=chain['output_bytes'])
        self.record.setdefault('visual_transactions',[]).append(pending)
        self.policy.active=self.policy.ever=True;self.policy.completed=False
        self.runtime.dma.recvchannel.transfer(rx,nbytes=chain['output_bytes']);self.runtime.kernel.write(self.base.REG_AP_CTRL,1);self.runtime.dma.sendchannel.transfer(tx,nbytes=len(packet))
        observed=self.base.wait_transaction(self.runtime.kernel,self.runtime.dma,10.)
        if not safe_to_release(observed) or observed['ap_return']!=self.policy.build:raise RuntimeError('Borrowed visual completion/build unsafe; retain original owner')
        self.policy.active=False;self.policy.completed=True;rx.sync_from_device()
        raw=bytes(memoryview(rx)[:chain['output_bytes']]);pending['completed']=True;pending['completed_snapshot']=observed
        if expected is not None and (len(raw)!=expected['output_bytes'] or hashlib.sha256(raw).hexdigest()!=expected['raw_sha256']):raise RuntimeError('Saved combination full wire SHA differs')
        self.rows.append(pending);self.policy.capture('after-visual-submit:'+str(index)+':'+part,True)
        return raw
    def __exit__(self,*unused):
        # Visual writes invalidate the software register cache, even after a
        # numerical rejection. Never restore stale pre-visual cache values.
        self.runtime._programmed_weight_addresses=None;self.runtime._programmed_config=None
        if self.policy.active or not self.policy.safe():
            self.retained=True
            return False
        self.check();self.entered=False
        return False
