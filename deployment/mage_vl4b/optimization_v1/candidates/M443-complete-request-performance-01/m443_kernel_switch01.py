"""Default-off comparison-only Overlay binding; never allocate or release DMA.

All switching and legal-minimal proofs are outside complete-request timers.
Unproven transitions deliberately leave the original owner retained.
"""
import threading
import numpy as np
from board_safety import safe_to_release

class KernelSwitch:
    def __init__(self,runtime,policy,base,result,*,enabled=False,load_overlay=None,environment=None,patch=None,video_server=None,packet=None,golden=None):
        if enabled is not True:raise RuntimeError('Kernel comparison switch disabled')
        self.runtime,self.policy,self.base,self.result=runtime,policy,base,result
        self.load_overlay,self.environment,self.patch,self.video_server=load_overlay,environment,patch,video_server
        self.packet,self.golden=packet,golden
        if len(packet)!=2576 or len(golden)!=4096:raise RuntimeError('Frozen legal-minimal fixture differs')
        self.buffers=tuple(runtime.staged_buffers)+(runtime.input_buffer,runtime.output_buffer,runtime.output_buffer_alt)
        self.ids=tuple(id(b) for b in self.buffers);self.addresses=tuple(base.physical_address(b) for b in self.buffers)
        self.history=[];result['kernel_transitions']=[]

    def verify_owned_idle(self):
        current=tuple(self.runtime.staged_buffers)+(self.runtime.input_buffer,self.runtime.output_buffer,self.runtime.output_buffer_alt)
        if tuple(id(b) for b in current)!=self.ids or tuple(self.base.physical_address(b) for b in current)!=self.addresses:raise RuntimeError('Original seven owners changed')
        if tuple(b.nbytes for b in current)!=(6963200,)*4+(389152,2621440,2621440):raise RuntimeError('Original seven geometry changed')
        if not self.policy.sealed or not self.policy.ever or not self.policy.completed or not self.policy.safe():raise RuntimeError('Completed original owner required')
        if self.result.get('language_scope_active') or self.result.get('vision_request_active') or self.result['released_buffers']:raise RuntimeError('Active or released request scope')
        if any(t.name.startswith(('m238-parse','m238-pack')) for t in threading.enumerate()):raise RuntimeError('Request worker retained')
        s=self.base.transaction_snapshot(self.runtime.kernel,self.runtime.dma)
        if not safe_to_release(s) or s['ap_return']!=self.policy.build:raise RuntimeError('Original completed Build proof required')
        return s

    def select(self,variant,index):
        if variant not in ('A','B'):raise ValueError('Frozen two Build variants only')
        before=self.verify_owned_idle();build=0x4d343431 if variant=='A' else 0x4d343433
        if self.policy.build==build:return False
        # This callback runs exact same-TTY/root package and XRT environment preflight.
        path=self.environment(variant,index)
        self.policy.capture('before-untimed-kernel-switch:'+str(index),True)
        row=dict(index=index,variant=variant,from_build=self.policy.build,to_build=build,before_snapshot=before,completed=False)
        self.result['kernel_transitions'].append(row)
        self.policy.prepare_programming(path,index,variant)
        self.history.append((self.runtime.overlay,self.runtime.kernel,self.runtime.dma))
        # A programming failure is an unknown transition; keep the original seven owners.
        self.policy.active=True;self.policy.completed=False
        overlay=self.load_overlay(path,download=True)
        self.runtime.overlay=overlay;self.runtime.kernel=overlay.mage_m120_m89x2_0;self.runtime.dma=overlay.axi_dma_prefill
        self.policy.build=build;self.patch(self.base,'BUILD_ID',build);self.patch(self.video_server,'BUILD_ID',f'0x{build:08X}')
        self.runtime._programmed_weight_addresses=None;self.runtime._programmed_config=None
        current=tuple(self.runtime.staged_buffers)+(self.runtime.input_buffer,self.runtime.output_buffer,self.runtime.output_buffer_alt)
        if tuple(id(b) for b in current)!=self.ids or tuple(self.base.physical_address(b) for b in current)!=self.addresses:raise RuntimeError('Overlay changed original buffers')
        for b in current[:4]:b[:144]=0;b.sync_to_device()
        tx,rx=current[4:6];tx[:len(self.packet)]=np.frombuffer(self.packet,np.uint8);tx.sync_to_device()
        rx[:len(self.golden)]=0xa5;rx.sync_to_device()
        for register,b in zip(self.base.REG_POINTERS,current[:4]):self.base.write_u64(self.runtime.kernel,register,self.base.physical_address(b))
        self.runtime.kernel.write(self.base.REG_CONFIG,0x10201)
        self.result['kernel_switch_minimal_attempts']=self.result.get('kernel_switch_minimal_attempts',0)+1
        self.runtime.dma.recvchannel.transfer(rx,nbytes=len(self.golden));self.runtime.kernel.write(self.base.REG_AP_CTRL,1);self.runtime.dma.sendchannel.transfer(tx,nbytes=len(self.packet))
        observed=self.base.wait_transaction(self.runtime.kernel,self.runtime.dma,10.)
        if not safe_to_release(observed) or observed['ap_return']!=build:raise RuntimeError('New Overlay minimal completion unsafe')
        self.policy.active=False;self.policy.completed=True;rx.sync_from_device()
        if bytes(memoryview(rx)[:len(self.golden)])!=self.golden:raise RuntimeError('New Overlay full minimal output differs')
        self.runtime._programmed_weight_addresses=None;self.runtime._programmed_config=None
        row.update(completed=True,completed_snapshot=observed,full_output_exact=True,original_buffer_identities_preserved=True,extra_DMA=0,outside_request_timer=True)
        self.policy.capture('after-untimed-kernel-switch:'+str(index),True)
        self.verify_owned_idle()
        return True
