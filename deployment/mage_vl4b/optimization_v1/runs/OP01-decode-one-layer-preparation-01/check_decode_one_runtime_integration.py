"""Exercise actual M238 method resolution and extracted layer on software doubles."""
import hashlib
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
from decode_one_runtime_adapter import runtime_class
from decode_one_layer_probe import bind_layer_zero

root = Path(__file__).resolve().parents[2]
base = root/'deployment/mage_vl4b'
sys.path.extend([str(base/'m242_m241_fixed_text_board_candidate'),
                 str(base/'m175_m120_fixed_text_candidate/runtime'),
                 str(base/'m181_m120_video_board_candidate')])
import board_runtime
from m238_prefill_runtime import M238PrefillRuntime
from m241_video_language_runtime import M241VideoLanguageModel
import video_language_runtime as vl

# Real M238 inheritance still dispatches config setup through the candidate override.
# No PYNQ constructor, allocation or overlay is invoked here.
cls = runtime_class(M238PrefillRuntime, SimpleNamespace(BUILD_ID=0x4F503131))
obj = cls.__new__(cls)
obj._programmed_weight_addresses = None; obj._programmed_config = None
writes=[]
obj.kernel = SimpleNamespace(write=lambda *args: writes.append(args))
chain=dict(config_u32='0x10428')
buffers=[SimpleNamespace(device_address=0x10000+i*0x1000) for i in range(4)]
with obj._one_token(np.zeros((1,2560),np.float32)):
    obj._program_static_registers(chain,buffers)
    obj._program_static_registers(chain,buffers)
assert writes[-1] == (0x80,0x1010428) and len(writes)==9
assert chain['config_u32']=='0x10428'

model=M241VideoLanguageModel.__new__(M241VideoLanguageModel)
model.embedding=np.ones((2,2560),np.float16)
model.weight=lambda name: np.ones(128 if '.q_norm.' in name or '.k_norm.' in name else 2560,np.float32)
calls=[]
def family(layer,family,values):
    calls.append((layer,family))
    prefix=f'model.language_model.layers.{layer}'
    widths={'q': [('self_attn.q_proj',4096)], 'kv':[('self_attn.k_proj',1024),('self_attn.v_proj',1024)],
            'attention_out':[('self_attn.o_proj',2560)],
            'gate_up':[('mlp.gate_proj',9728),('mlp.up_proj',9728)], 'mlp_down':[('mlp.down_proj',2560)]}
    return {prefix+'.'+name:np.full((1,width),.01,np.float32) for name,width in widths[family]}
model._family=family
keys=[np.zeros((3,8,128),np.float32) for _ in range(36)]
values=[x.copy() for x in keys]
cache=vl.KVCache(keys,values)
layer=bind_layer_zero(model)
hidden,out_cache=layer(1,cache)
assert hidden.shape==(1,2560) and np.isfinite(hidden).all()
assert [x.shape[0] for x in out_cache.keys]==[4]+[3]*35
assert [family for _,family in calls]==['q','kv','attention_out','gate_up','mlp_down']
assert all(index==0 for index,_ in calls)
reference_head=[]
model.runtime=SimpleNamespace(lm_head=lambda final: (reference_head.append(final.copy()) or np.zeros((1,4),np.float32)))
old_layers=vl.LAYERS
try:
    # Compare with the untouched Decode method under a one-layer software fixture.
    vl.LAYERS=1
    reference_cache=vl.KVCache([np.zeros((3,8,128),np.float32)],[np.zeros((3,8,128),np.float32)])
    model.decode(1,reference_cache)
finally:
    vl.LAYERS=old_layers
assert np.array_equal(reference_head[0],vl.rms_norm(hidden,model.weight('model.language_model.norm.weight')))
assert np.array_equal(reference_cache.keys[0],out_cache.keys[0])
assert np.array_equal(reference_cache.values[0],out_cache.values[0])
print('PASS_REAL_M238_DISPATCH_AND_LAYER_ZERO_EXTRACTION_OFFLINE_ONLY')
