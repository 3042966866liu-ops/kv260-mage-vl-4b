"""Real Torch/Siglip MLP and original M207 small fixture, never quality proof."""
import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from m407_mlp_contract import chain_for
from m409_ftz_reference import linear_reference,SoftwareMLPBinding
from m355_reference import decode_records
from m120_group_reference import group_reference

def component(torch,root,host,initial):
    from transformers.models.siglip.modeling_siglip import SiglipMLP
    from transformers.models.siglip.configuration_siglip import SiglipVisionConfig
    from m408_target_component04 import actual_class
    source=root/'tmp/m223_realtime/m223_realtime_delta/m207_ps_vision_runtime.py'
    cls=actual_class(torch,source,'M207FP32GemmW4Linear',dict(_base=SimpleNamespace(_TorchModule=torch.nn.Module)))
    tile=dict(tile_index=0,row_start=0,valid_rows=64,rows_per_shard=16,shard_offsets=[0]*4,record_bytes_per_shard=544)
    chains={k:chain_for(dict(module=k,shape=[64,64],input_groups=1,bits=4,tiles=[tile]),i) for i,k in enumerate(('fc1','fc2'))}
    window=(np.full(8,.03125,'<f2').tobytes()+bytes([0x99])*256)*2
    windows={k:[window]*4 for k in chains}
    w,s=decode_records(window,1,16,4)
    weight=np.tile((w.astype(np.float32)*s.astype(np.float32)[...,None]).reshape(16,64),(4,1))
    class Store:
        def decode(self,name):return weight.copy()
    mlp=SiglipMLP(SiglipVisionConfig(hidden_size=64,intermediate_size=64,hidden_act='gelu'))
    for k in chains:
        linear=cls(torch,Store(),k,64,64,True,torch.float32)
        linear.bias=torch.nn.Parameter(torch.arange(64,dtype=torch.float32)*.0001,requires_grad=False)
        setattr(mlp,k,linear)
    x=torch.from_numpy(((np.arange(40*64)%31-15)*.013).astype(np.float32).reshape(1,40,64))
    def integer(chain,arr):
        result=[]
        for start in range(0,len(arr),32):
            part=arr[start:start+32];shift=initial(part)
            _,codes,scales=host.quantize_t32(part,1,shift)
            y=group_reference(codes,scales,w,s,dot_mode='int32')
            u=y.view(np.uint16).copy();mask=((u&0x7c00)==0)&((u&0x3ff)!=0);u[mask]&=np.uint16(0x8000)
            z=u.view(np.float16).astype(np.float32)*np.float32(2.**-shift)
            result.append(np.tile(z[:len(part)],(1,4)))
        return torch.from_numpy(np.concatenate(result))
    with torch.inference_mode():
        one=integer(chains['fc1'],x.numpy()[0])+mlp.fc1.bias
        two=integer(chains['fc2'],mlp.activation_fn(one).numpy())+mlp.fc2.bias
        original=mlp(x).clone()
        binding=SoftwareMLPBinding(torch,mlp,chains,windows,initial,host.pack_chain_input,host.parse_chain_output)
        with binding:answer=mlp(x)
        assert answer.shape==(1,40,64) and torch.equal(answer[0],two)
        assert binding.calls=={'fc1':1,'fc2':1} and binding.restored
        assert [r['rows'] for r in binding.batches['fc1']]==[32,8]
        assert torch.equal(mlp(x),original)
        bads=(torch.ones(2,3,64),torch.ones(1,1,3,64),torch.ones(1,3,64,dtype=torch.float64),torch.full((1,3,64),float('nan')))
        rejected=0
        for bad in bads:
            check=SoftwareMLPBinding(torch,mlp,chains,windows,initial,host.pack_chain_input,host.parse_chain_output)
            try:
                with check:mlp(bad)
            except ValueError:rejected+=1
            else:raise AssertionError('Invalid native input accepted')
            assert check.restored
    return dict(real_Torch_CPU=True,actual_M207_class=True,actual_SiglipMLP_GELU=True,
        native_single_batch_preserved=True,independent_int32_full_output_equal=True,
        T32_partial_rows=[32,8],nonzero_bias_PS_add=True,invalid_native_inputs_rejected=rejected,
        bindings_restored=True,real_model_or_PL=False,quality_pass=False,performance_pass=False)

if __name__=='__main__':
    import json,sys,torch
    from test_m409_ftz_reference import actual_host
    h,initial=actual_host()
    print('M409_TORCH_COMPONENT='+json.dumps(component(torch,Path(__file__).resolve().parents[2],h,initial)))
