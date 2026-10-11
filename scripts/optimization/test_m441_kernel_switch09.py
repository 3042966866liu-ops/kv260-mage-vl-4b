"""Actual switch adapter with explicitly fake Overlay, DMA and memory lifecycle."""
import copy,json
from types import SimpleNamespace as NS
from unittest.mock import patch
import numpy as np
import m351_workflow as w
from m441_host_io08 import atomic
from m441_kernel_switch09 import KernelSwitch

class Buffer(np.ndarray):
    def sync_to_device(self):pass
    def sync_from_device(self):pass

def component():
    shapes=(6963200,)*4+(389152,2621440,2621440)
    buffers=[np.zeros(n,np.uint8).view(Buffer) for n in shapes]
    packet=bytes(2576);golden=bytes(4096);checks=[]
    def create():
        pending={};env=[];overlays=[]
        kernel=NS(write=lambda *unused:None)
        def transfer(rx,nbytes):pending['rx']=rx;pending['bytes']=nbytes
        dma=NS(recvchannel=NS(transfer=transfer),sendchannel=NS(transfer=lambda *a,**kw:None))
        overlay=NS(mage_m120_m89x2_0=kernel,axi_dma_prefill=dma)
        rt=NS(overlay=overlay,kernel=kernel,dma=dma,staged_buffers=buffers[:4],input_buffer=buffers[4],output_buffer=buffers[5],output_buffer_alt=buffers[6],_programmed_config=123,_programmed_weight_addresses=(1,2,3,4))
        policy=NS(build=0x4d343431,active=False,completed=True,ever=True,sealed=True,capture=lambda *unused:None)
        policy.safe=lambda:not policy.active and policy.completed
        def snapshot(*unused):return dict(ap_ctrl=4,ap_return=policy.build,mm2s_dmasr=4098,s2mm_dmasr=4098,kernel_read_error='',return_read_error='',dma_read_error='')
        def wait(*unused):
            assert pending['bytes']==4096 and bytes(buffers[4][:2576])==packet
            pending['rx'][:4096]=0
            return snapshot()
        base=NS(BUILD_ID=policy.build,REG_POINTERS=(16,28,40,52),REG_CONFIG=64,REG_AP_CTRL=0,physical_address=lambda b:id(b)&0x7fffffff,transaction_snapshot=snapshot,wait_transaction=wait,write_u64=lambda *unused:None)
        server=NS(BUILD_ID='0x4D343431');result=dict(released_buffers=[])
        def environment(v,n):env.append((v,n));return v
        def loader(path):overlays.append(path);return overlay
        switch=KernelSwitch(rt,policy,base,result,enabled=True,load_overlay=loader,environment=environment,patch=lambda o,k,v:setattr(o,k,v),video_server=server,packet=packet,golden=golden)
        return switch,policy,base,env,overlays,rt,result
    s,p,b,e,o,rt,r=create()
    assert s.select('B',1) is False and not e and not o
    assert s.select('A',2) and b.BUILD_ID==p.build==0x4d333537 and p.safe()
    assert s.select('B',3) and p.build==0x4d343431 and p.safe()
    assert rt._programmed_config is None and rt._programmed_weight_addresses is None
    assert len(r['kernel_transitions'])==2 and all(x['completed'] and x['full_output_exact'] and x['extra_DMA']==0 for x in r['kernel_transitions'])
    assert len(s.history)==2 and tuple(id(x) for x in buffers)==s.ids
    checks.extend(['same-B-does-not-program','A-B-legal-minimal-complete','full-output-and-Build','original-seven-identities','cache-invalidated','old-bindings-retained'])
    def reject(label,alter):
        q,p,b,e,o,rt,r=create();alter(q,p,b,e,o,rt,r)
        try:q.select('A',1)
        except (RuntimeError,TimeoutError):checks.append(label)
        else:raise AssertionError(label)
    reject('active-prior-DMA',lambda q,p,*unused:setattr(p,'active',True))
    reject('incomplete-prior',lambda q,p,*unused:setattr(p,'completed',False))
    reject('changed-buffer',lambda q,p,b,e,o,rt,r:setattr(rt,'output_buffer_alt',buffers[5]))
    reject('released-owner',lambda q,p,b,e,o,rt,r:r['released_buffers'].append(1))
    reject('active-language',lambda q,p,b,e,o,rt,r:r.update(language_scope_active=True))
    reject('bad-prior-build',lambda q,p,b,*unused:setattr(b,'transaction_snapshot',lambda *a:dict(ap_ctrl=4,ap_return=0,mm2s_dmasr=4098,s2mm_dmasr=4098)))
    with patch('m441_kernel_switch09.threading.enumerate',lambda:[NS(name='m238-parse_0')]):reject('retained-parser',lambda *unused:None)
    for name,fail in [('programming-error',True),('wrong-new-return',False)]:
        q,p,b,e,o,rt,r=create()
        if fail:
            def broken(path):raise RuntimeError('explicit Overlay fixture failure')
            q.load_overlay=broken
        else:b.wait_transaction=lambda *unused:dict(ap_ctrl=4,ap_return=0,mm2s_dmasr=4098,s2mm_dmasr=4098)
        try:q.select('A',1)
        except RuntimeError:pass
        else:raise AssertionError(name)
        assert p.active and not p.completed and not p.safe() and not r['released_buffers'] and not r['kernel_transitions'][0]['completed']
        checks.append(name+'-retains-unknown-owner')
    try:KernelSwitch(None,None,None,None)
    except RuntimeError:checks.append('disabled-default')
    else:raise AssertionError('enabled by default')
    out=w.BASE/'runs/M441-kernel-switch-component-09'
    v=dict(status='PASS_M441_KERNEL_SWITCH_CPU_COMPONENT_ONLY',checks=checks,adapter_sha256=w.sha(w.HERE/'m441_kernel_switch09.py'),fake_Overlay_DMA_MMIO=True,actual_seven_NumPy_buffers_bytes=sum(shapes),original_owner_no_allocate_or_free_API=True,not_board_capability_or_performance=True)
    atomic(out/'RESULT.json',w.encoded(v),immutable=True);d=w.sha(out/'RESULT.json')
    w.sync('latest_m441_kernel_switch_component',dict(status=v['status'],result=(out/'RESULT.json').relative_to(w.ROOT).as_posix(),sha256=d),f'## M441 性能隔离核绑定组件09（2026-10-09）\n\nSHA {d}；实际默认关闭adapter及七普通NumPy数组，明确fake Overlay/DMA/MMIO。{len(checks)}项旧owner完成/线程/地址/释放拒绝、合法最小全输出/Build、缓存失效、programming与新Build失败保留通过；无分配/释放API，切换在请求计时外。仅CPU组件，尚非板端切换/性能，视频完整数值闭合前不启动性能。')
    print(v['status'],d,len(checks))

if __name__=='__main__':component()
