"""Small exact-integer oracle, adaptive retry and binding lifecycle fixtures."""
import ast
import __future__
import importlib.util
import json
import math
from pathlib import Path
import sys
import numpy as np
from m407_mlp_contract import chain_for
from m409_ftz_reference import linear_reference,SoftwareMLPBinding
from m120_group_reference import group_reference
from m355_reference import decode_records

ROOT=Path(__file__).resolve().parents[2]


def actual_host(root=ROOT):
    path=root/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime/contract_runtime.py'
    spec=importlib.util.spec_from_file_location('m409_actual_host',path)
    m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
    source=root/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime/board_runtime.py'
    tree=ast.parse(source.read_text(encoding='utf-8-sig'))
    cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='M120BoardRuntime')
    fn=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='_initial_scale_shift')
    fn.decorator_list=[]
    constants=[]
    names={'MAX_ACTIVATION_SCALE_SHIFT','MIN_ACTIVATION_SCALE_SHIFT','MAX_TRANSMITTED_ACTIVE_SCALE'}
    for x in tree.body:
        if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in x.targets):constants.append(x)
    ns=dict(np=np,math=math)
    exec(compile(ast.fix_missing_locations(ast.Module(body=constants+[fn],type_ignores=[])),str(source),'exec',flags=__future__.annotations.compiler_flag),ns)
    return m,ns['_initial_scale_shift']


def fixture(name='fixture',scale=.5):
    tile=dict(tile_index=0,row_start=0,valid_rows=32,rows_per_shard=8,shard_offsets=[0]*4,record_bytes_per_shard=272)
    chain=chain_for(dict(module=name,shape=[32,64],input_groups=1,bits=4,tiles=[tile]),0)
    tags=np.full(8,scale,'<f2').view(np.uint8).tobytes()
    window=tags+bytes([0x99])*256
    return chain,[window]*4


def main():
    host,initial=actual_host()
    chain,windows=fixture()
    values=np.full((40,64),64,np.float32)
    raws=[]
    answer,batches=linear_reference(chain,values,windows,initial,host.pack_chain_input,host.parse_chain_output,
                                    raw_sink=lambda *args:raws.append(args))
    assert len(batches)==2 and [x['rows'] for x in batches]==[32,8]
    assert all(x['attempted_shifts']==[6,5,4] and x['selected_shift']==4 for x in batches)
    # Independently compare all lanes against int32 group dots, FP16 and FTZ.
    for start,shift,packet,raw in raws:
        records,codes,scales=host.quantize_t32(values[start:start+32],1,shift)
        weight,ws=decode_records(windows[0],1,8,4)
        gold=group_reference(codes,scales,weight,ws,dot_mode='int32')
        u=gold.view(np.uint16).copy();u[((u&0x7c00)==0)&((u&0x03ff)!=0)]&=np.uint16(0x8000)
        decoded=host.parse_chain_output(chain,raw,output_scale_shift=0)[chain['module']]
        assert np.array_equal(decoded.view(np.uint32),np.tile(u.view(np.float16).astype(np.float32),(1,4)).view(np.uint32))
    tiny,small_windows=fixture(scale=float(np.float16(1e-5)))
    small,_=linear_reference(tiny,np.full((8,64),.001,np.float32),small_windows,initial,host.pack_chain_input,host.parse_chain_output)
    assert not small.any()
    exhausted=False
    try:linear_reference(chain,np.full((1,64),1e5,np.float32),windows,initial,host.pack_chain_input,host.parse_chain_output)
    except FloatingPointError:exhausted=True
    assert exhausted
    short=False
    try:linear_reference(chain,values,[b'']*4,initial,host.pack_chain_input,host.parse_chain_output)
    except ValueError:short=True
    assert short
    # Binding test uses a small explicit identity GELU substitute only for lifecycle,
    # not quality. Actual model replay later must retain the original MLP activation.
    class Value:
        def __init__(self,arr):self.arr=arr
        def detach(self):return self
        def cpu(self):return self
        def numpy(self):return self.arr
        def __add__(self,bias):return Value(self.arr+bias.value)
    class Bias:
        value=np.zeros(32,np.float32)
        def to(self,dtype):return self
    class Module:
        output_dtype='EXPLICIT_FP32';bias=Bias()
        def forward(self,x):return x
    torch=type('FixtureTorch',(),dict(float32='EXPLICIT_FP32',from_numpy=staticmethod(Value)))
    fc1,fc2=Module(),Module();mlp=type('FixtureMLP',(),dict(fc1=fc1,fc2=fc2))()
    chains={k:fixture(k)[0] for k in ('fc1','fc2')};ww={k:fixture(k)[1] for k in chains}
    binding=SoftwareMLPBinding(torch,mlp,chains,ww,initial,host.pack_chain_input,host.parse_chain_output)
    try:
        with binding:
            out=fc1.forward(Value(np.ones((2,64),np.float32)))
            assert out.arr.shape==(2,32)
            raise RuntimeError('intentional binding exception')
    except RuntimeError as error:assert 'intentional' in str(error)
    assert binding.restored and 'forward' not in fc1.__dict__ and 'forward' not in fc2.__dict__
    assert not any(n=='pynq' or n.startswith('pynq.') for n in sys.modules)
    print(json.dumps(dict(status='PASS_M409_SOFTWARE_ORACLE_COMPONENT_ONLY',complete_int32_reference_equal=True,
        original_shift_retry=[6,5,4],FP16_subnormal_FTZ=True,exhaustion_and_short_read_rejected=True,
        exception_instance_binding_restored=True,actual_host_functions=True,no_PYNQ=True,
        real_model_or_board=False,quality_pass=False,performance_pass=False)))


if __name__=='__main__':main()
