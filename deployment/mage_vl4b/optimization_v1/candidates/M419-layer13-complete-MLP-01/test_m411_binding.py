"""Actual Torch native392-row small fixture and real file staging; no hardware."""
import hashlib,json,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'deployment/mage_vl4b/optimization_v1/candidates/M409-saved-MLP-reference-01'
sys.path.insert(0,str(OLD))
from m411_mlp_binding import PLMLPBinding,decision,stage_windows
def component(root=ROOT,temporary_root=None):
    import torch
    from transformers.models.siglip.modeling_siglip import SiglipMLP
    from transformers.models.siglip.configuration_siglip import SiglipVisionConfig
    from m408_target_component04 import actual_class
    from test_m409_ftz_reference import actual_host,fixture
    from m409_ftz_reference import SoftwareMLPBinding
    from m355_reference import decode_records,full_reference
    cls=actual_class(torch,root/'tmp/m223_realtime/m223_realtime_delta/m207_ps_vision_runtime.py','M207FP32GemmW4Linear',dict(_base=SimpleNamespace(_TorchModule=torch.nn.Module)))
    host,initial=actual_host(root);chains={k:fixture(k,scale=.03125)[0] for k in ('fc1','fc2')};windows={k:fixture(k,scale=.03125)[1] for k in chains}
    # fixture width32 must feed nextG1=64: extend each shard to16 rows, actual chain64.
    from m407_mlp_contract import chain_for
    tile=dict(tile_index=0,row_start=0,valid_rows=64,rows_per_shard=16,shard_offsets=[0]*4,record_bytes_per_shard=544)
    chains={k:chain_for(dict(module=k,shape=[64,64],input_groups=1,bits=4,tiles=[tile]),i) for i,k in enumerate(('fc1','fc2'))}
    window=(np.full(8,.03125,'<f2').tobytes()+bytes([0x99])*256)*2;windows={k:[window]*4 for k in chains}
    codes,scales=decode_records(window,1,16,4);weight=np.tile((codes.astype(np.float32)*scales.astype(np.float32)[...,None]).reshape(16,64),(4,1))
    class Store:
        def decode(self,name):return weight.copy()
    mlp=SiglipMLP(SiglipVisionConfig(hidden_size=64,intermediate_size=64,hidden_act='gelu'))
    for k in chains:
        linear=cls(torch,Store(),k,64,64,True,torch.float32);linear.bias=torch.nn.Parameter(torch.arange(64,dtype=torch.float32)*.0001,requires_grad=False);setattr(mlp,k,linear)
    x=torch.from_numpy(((np.arange(392*64)%31-15)*.013).astype(np.float32).reshape(1,392,64));staged=[];calls=[];saved={}
    def sink(part,start,shift,packet,raw):saved[(part,start,shift)]=(packet,raw)
    def submit(part,c,start,shift,packet):
        calls.append((part,start,shift));return full_reference(c,windows[part],c['stage_base_words'],packet)
    with torch.inference_mode():
        software=SoftwareMLPBinding(torch,mlp,chains,windows,initial,host.pack_chain_input,host.parse_chain_output,raw_sink=sink)
        with software:expected=mlp(x)
        binding=PLMLPBinding(torch,mlp,chains,initial,host,lambda part,c:staged.append(part),submit,saved)
        with binding:answer=mlp(x)
        assert torch.equal(answer,expected) and answer.shape==(1,392,64) and binding.restored and staged==['fc1','fc2']
        assert len(calls)==26 and [b['rows'] for b in binding.batches['fc2']]==[32]*12+[8]
        failures=0
        def raise_submit(*unused):raise RuntimeError('EXPLICIT retained hardware substitute failure')
        tests=[(x,raise_submit,None),(torch.ones(2,392,64),submit,None),(x.double(),submit,None),(x*float('nan'),submit,None),(x,submit,{k:(p,b'wrong') for k,(p,r) in saved.items()})]
        for arr,method,expect in tests:
            checker=PLMLPBinding(torch,mlp,chains,initial,host,lambda *a:None,method,expect)
            try:
                with checker:mlp(arr)
            except (RuntimeError,ValueError):failures+=1
            else:raise AssertionError('Bad native input/submission/raw accepted')
            assert checker.restored and 'forward' not in mlp.fc1.__dict__ and 'forward' not in mlp.fc2.__dict__
    # Actual staging implementation: own regular files, four fake CPU buffers only.
    class Buffer(np.ndarray):
        def __new__(cls):return np.zeros(544,np.uint8).view(cls)
        def sync_to_device(self):self.synced=True
    with tempfile.TemporaryDirectory(dir=temporary_root or root/'tmp') as temp:
        root=Path(temp);rows=[];owner=SimpleNamespace(buffers=[Buffer() for _ in range(4)])
        for i in range(4):
            p=root/f'w{i}';p.write_bytes(b'prefix'+window);rows.append(dict(relative_file=p.name,file_bytes=p.stat().st_size,offset=6,bytes=544))
        row=stage_windows(owner,'fc1',rows,root);assert row['bytes']==4*544 and all(bytes(b)==window and b.synced for b in owner.buffers)
        (root/'w1').write_bytes(b'short')
        try:stage_windows(owner,'fc1',rows,root)
        except RuntimeError:failures+=1
        else:raise AssertionError('Weight size change accepted')
    good=[dict(variant=v,elapsed_ns=1000 if v=='A' else 800) for v in 'ABBABAAB'];assert decision(good)['performance_pass']
    noisy=[dict(variant=v,elapsed_ns=1000 if v=='A' else 800) for v in 'ABBABAAB'];noisy[0]['elapsed_ns']=1500;assert not decision(noisy)['performance_pass']
    small=[dict(variant=v,elapsed_ns=1000 if v=='A' else 970) for v in 'ABBABAAB'];assert not decision(small)['performance_pass']
    return dict(actual_Torch_M207_Siglip_GELU=True,native392_rows_and_original_T32_32_8=True,full_software_reference_equal=True,finite_original_retry=True,
        bindings_restored_on_all_failures=True,negative_checks=failures,actual_four_file_read_copy_sync=True,predeclared_order_noise_5percent_rejections=True,
        submit_explicit_PS_software_substitute=True,buffer_sync_explicit_fake=True,real_model_quality_or_PL=False,performance_evidence=False)
if __name__=='__main__':print('M411_BINDING_COMPONENT='+json.dumps(component()))
