"""Passive hook/dispatch/restoration component; toy math is not model quality."""
import types
import numpy as np
def check():
    import torch
    from vision_layer_profiler import VisionProfiler
    class Store:
        def __init__(self,w):self.weight=w
        def decode(self,name):return self.weight
    class Linear(torch.nn.Module):
        def __init__(self,ni,no):
            super().__init__();self.store=Store(np.arange(no*ni,dtype=np.float32).reshape(no,ni)*.001);self.bias=torch.zeros(no)
        def forward(self,x):return torch.nn.functional.linear(x,torch.from_numpy(self.store.decode('fixture')),self.bias)
    class Attention(torch.nn.Module):
        def __init__(self):super().__init__();self.qkv=Linear(4,12);self.proj=Linear(4,4)
        def forward(self,x):return self.proj(self.qkv(x)[...,:4])
    class MLP(torch.nn.Module):
        def __init__(self):super().__init__();self.fc1=Linear(4,8);self.fc2=Linear(8,4);self.activation_fn=torch.nn.GELU()
        def forward(self,x):return self.fc2(self.activation_fn(self.fc1(x)))
    class Core(torch.nn.Module):
        def __init__(self):
            super().__init__();self.self_attn=Attention();self.mlp=MLP();self.layer_norm1=torch.nn.LayerNorm(4);self.layer_norm2=torch.nn.LayerNorm(4)
        def forward(self,x):x=x+self.self_attn(self.layer_norm1(x));return (x+self.mlp(self.layer_norm2(x)),)
    class Wrapper(torch.nn.Module):
        def __init__(self,layer):super().__init__();self.layer=layer
        def forward(self,x):return self.layer(x)
    torch.set_num_threads(4);torch.manual_seed(534)
    a=Wrapper(Core());b=Wrapper(Wrapper(Core()));layers=[None,a,b];x=torch.randn(1,8,4)
    original=torch.nn.functional.linear;expected=[a(x)[0],b(x)[0]];old=dict(b.layer.layer.mlp.fc1.__dict__)
    profiler=VisionProfiler(torch,layers,(1,2));profiler.begin()
    actual=[a(x)[0],b(x)[0]]
    outside=Linear(4,4);outside_expected=original(x,torch.from_numpy(outside.store.weight),outside.bias)
    assert torch.equal(outside(x),outside_expected)
    # Shared decoded weights can also serve merger projections outside blocks.
    assert np.array_equal(a.layer.self_attn.qkv.store.decode('outside_fixture'),a.layer.self_attn.qkv.store.weight)
    report=profiler.end();assert report['outside_encoder']['cpu_linear']>0 and report['outside_encoder']['decode']>0
    assert all(torch.equal(x,y) for x,y in zip(actual,expected))
    assert all(r['counts']['cpu_linear:qkv']==r['counts']['decode:qkv']==1 for r in report['rows'])
    # Existing PL scopes override instance.forward, keeping Module hooks intact.
    module=b.layer.layer.mlp.fc1;module.forward=types.MethodType(lambda self,x:torch.zeros((*x.shape[:-1],8)),module)
    profiler.begin();a(x);b(x);sub=profiler.end();assert sub['rows'][1]['counts'].get('cpu_linear:fc1',0)==0 and sub['rows'][1]['counts']['module:fc1']==1
    del module.__dict__['forward'];profiler.close()
    assert torch.nn.functional.linear is original and all(torch.equal(y(x)[0],z) for y,z in zip((a,b),expected))
    assert all('decode' not in m.store.__dict__ for c in (a.layer,b.layer.layer) for m in (c.self_attn.qkv,c.self_attn.proj,c.mlp.fc1,c.mlp.fc2))
    model=torch.nn.Module();model.merger=MLP();model.embeddings=Linear(4,4)
    profiler=VisionProfiler(torch,layers,(1,2),vision_model=model);profiler.begin()
    model.embeddings(x);model.merger(x);a(x);b(x);outside=profiler.end()
    assert set(outside['outside_components'])=={'embeddings','merger'} and outside['outside_components']['merger']>0
    profiler.begin();model.merger(x)
    try:profiler.close()
    except AssertionError:pass
    else:raise AssertionError('Aborted observer silently closed without caller idle proof')
    admitted=[];profiler.close(idle=lambda:admitted.append(True));assert admitted==[True] and torch.nn.functional.linear is original
    return dict(status='PASS_PASSIVE_VISUAL_TIMERS_COMPONENT',math_fixture_bit_exact=True,PS_wrapper_topologies=2,encoder_before_after_shared_decode_and_merger_tested=True,aborted_observer_requires_caller_idle_proof=True,instance_forward_substitution_hooks_preserved=True,linear_decode_and_hook_identity_restored=True,model_forwards=0,Overlay=0,DMA=0)
