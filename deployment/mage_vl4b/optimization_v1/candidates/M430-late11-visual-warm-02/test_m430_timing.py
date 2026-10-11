"""Actual frozen wrapper/encoder/M207 + exact oracle, synthetic small MLP.

All24 boundaries use the real392x1024 shape; synthetic weights, narrow MLP
and Attention are explicit. This validates orchestration, not model quality.
"""
import ast, __future__, hashlib, json, sys, threading, time
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
import numpy as np

def component(root):
    import torch
    from m408_target_component04 import actual_class
    from m355_reference import decode_records
    from m407_mlp_contract import chain_for
    from m409_ftz_reference import SoftwareMLPBinding
    from test_m409_ftz_reference import actual_host
    from m426_range02 import RangeScope, SELECTED
    p=actual_class(torch,root/'tmp/m223_realtime/m223_realtime_delta/m206_ps_vision_runtime.py','M206ProgressLayer',dict(_base=SimpleNamespace(_TorchModule=torch.nn.Module),_rss_mib=lambda:0.,threading=threading,time=time))
    b=actual_class(torch,root/'tmp/m227_runtime_base/m227_runtime_base_patch/ps_vision_runtime.py','M196PrecisionBoundary',dict(_TorchModule=torch.nn.Module))
    linear=actual_class(torch,root/'tmp/m223_realtime/m223_realtime_delta/m207_ps_vision_runtime.py','M207FP32GemmW4Linear',dict(_base=SimpleNamespace(_TorchModule=torch.nn.Module)))
    model=root/'deployment/mage_vl4b/m181_m120_video_board_candidate/ps_vision_payload/modeling_mage_vl.py'
    cls=next(n for n in ast.parse(model.read_text(encoding='utf-8-sig')).body if isinstance(n,ast.ClassDef) and n.name=='MageVLVisionEncoderLayer')
    fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='forward');ns={}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(model),'exec',flags=__future__.annotations.compiler_flag),ns)
    class Attention(torch.nn.Module):
        def forward(self,hidden_states,**unused):return hidden_states*.03125,None
    class MLP(torch.nn.Module):
        def __init__(self):
            super().__init__();self.fc1=torch.nn.Linear(1024,64);self.fc2=torch.nn.Linear(64,1024)
        def forward(self,x):return self.fc2(torch.nn.functional.gelu(self.fc1(x)))
    class Encoder(torch.nn.Module):
        def __init__(self):
            super().__init__();self.mlp=MLP();self.layer_norm1=torch.nn.LayerNorm(1024);self.layer_norm2=torch.nn.LayerNorm(1024);self.self_attn=Attention()
        forward=ns['forward']
    torch.manual_seed(426);layers=torch.nn.ModuleList();cases={};targets={};inputs={}
    for i in range(24):
        inner=Encoder();dtype=torch.bfloat16 if i<2 else torch.float32;inner.to(dtype)
        layers.append(p(inner if i<2 else b(inner,dtype,torch.bfloat16),index=i,heartbeat_seconds=30.,run_elapsed=lambda:0.))
        if i<2:continue
        targets[i]=inner;chains={};windows={}
        for k,rows,columns in (('fc1',64,1024),('fc2',1024,64)):
            groups=columns//64;per=rows//4;size=groups*(per//8)*272
            tile=dict(tile_index=0,row_start=0,valid_rows=rows,rows_per_shard=per,shard_offsets=[0]*4,record_bytes_per_shard=size)
            c=chain_for(dict(module=k,shape=[rows,columns],input_groups=groups,bits=4,tiles=[tile]),i*2+(k=='fc2'));chains[k]=c
            window=(np.full(8,.0078125,'<f2').tobytes()+bytes([0x9a])*256)*(groups*per//8);windows[k]=[window]*4
            codes,scales=decode_records(window,groups,per,4)
            weight=np.tile((codes.astype(np.float32)*scales.astype(np.float32)[...,None]).transpose(1,0,2).reshape(per,columns),(4,1))
            class Store:
                def __init__(self,w):self.w=w
                def decode(self,name):return self.w.copy()
            mod=linear(torch,Store(weight),k,columns,rows,True,torch.float32)
            mod.bias=torch.nn.Parameter(torch.arange(rows,dtype=torch.float32)*(.000013*i),requires_grad=False)
            setattr(inner.mlp,k,mod)
        cases[i]=dict(chains=chains,windows=windows)
    host,initial=actual_host(root)
    def forward():
        x=((torch.arange(392*1024).reshape(1,392,1024)%137-68).float()*.013).to(torch.bfloat16)
        for layer in layers:x=layer(x)[0]
        return x
    def clean():
        return all('forward' not in getattr(targets[i].mlp,k).__dict__ for i in targets for k in ('fc1','fc2')) and all(not l._forward_hooks and not l._forward_pre_hooks for l in layers)
    boundary=[];loads=[]
    def sink(i,a):boundary.append((i,hashlib.sha256(a.tobytes()).hexdigest()))
    def load(i):loads.append(i);return cases[i]
    import copy
    from m429_pl_range import SavedWireCheck,SELECTED as late
    from m430_timed_scope import TimedPLRangeScope,LightBatchCheck
    class PLRangeScope(TimedPLRangeScope):
        def after(self,index,value):
            super().after(index,value)
            output=value[0] if isinstance(value,tuple) else value
            self.sink(index,output.detach().float().cpu().numpy()[0])
    wire={};rejected=[]
    class CaptureScope(RangeScope):
        def before(self,index):
            if self.active is not None or index!=len(self.seen):raise RuntimeError('Order differs')
            if index in self.selected:
                case=self.load_case(index)
                binding=SoftwareMLPBinding(torch,targets[index].mlp,case['chains'],case['windows'],initial,
                    host.pack_chain_input,host.parse_chain_output,
                    raw_sink=lambda part,start,shift,packet,raw:wire.__setitem__((index,part,start,shift),(packet,raw)))
                self.active=(index,binding);binding.__enter__();self.peak_live_layer_scopes=1
    with torch.inference_mode():
        with RangeScope(torch,layers,targets,late,'original',load,initial,host,sink,lambda x:None):original=forward()
        before=tuple(boundary);boundary.clear();loads.clear()
        with CaptureScope(torch,layers,targets,late,'software',load,initial,host,sink,lambda x:None) as oracle:expected=forward()
        references=copy.deepcopy(oracle.batches);expected_boundaries=tuple(boundary)
        assert oracle.complete and clean() and len(wire)==286
        submits=[];stages=[]
        def submit(index,part,chain,start,shift,packet):
            key=(index,part,start,shift);assert packet==wire[key][0];submits.append(key);return wire[key][1]
        guard=SavedWireCheck(references,submit);boundary.clear();loads.clear()
        with PLRangeScope(torch,layers,targets,load,initial,host,sink,lambda x:None,
                          lambda i,p,c:stages.append((i,p)),guard) as scope:actual=forward()
        guard.require_complete()
        assert torch.equal(actual,expected) and tuple(boundary)==expected_boundaries and tuple(boundary[:13])==before[:13]
        assert clean() and scope.restored and scope.complete and scope.peak_live_layer_scopes==1
        assert loads==list(late) and stages==[(i,p) for i in late for p in ('fc1','fc2')] and len(submits)==286
    def reject(label,fn):
        try:fn()
        except (ValueError,RuntimeError):rejected.append(label)
        else:raise AssertionError('Invalid accepted '+label)
        assert clean()
    for label,edit in [('missing-layer',lambda r:r.pop('13')),('extra-layer',lambda r:r.__setitem__('12',r['13'])),
            ('missing-part',lambda r:r['13'].pop('fc2')),('short-part',lambda r:r['13']['fc1'].pop()),
            ('wrong-start',lambda r:r['13']['fc1'][0].__setitem__('start',32)),
            ('wrong-tail',lambda r:r['13']['fc1'][-1].__setitem__('rows',32)),
            ('retry',lambda r:r['13']['fc1'][0].__setitem__('physical_reference_attempts',2)),
            ('initial',lambda r:r['13']['fc1'][0].__setitem__('initial_shift',-1)),
            ('bool-shift',lambda r:r['13']['fc1'][0].__setitem__('selected_shift',True)),
            ('zero-bytes',lambda r:r['13']['fc1'][0].__setitem__('input_bytes',0)),
            ('bad-SHA',lambda r:r['13']['fc1'][0].__setitem__('raw_sha256','g'*64))]:
        ref=copy.deepcopy(references);edit(ref);reject(label,lambda ref=ref:SavedWireCheck(ref,submit))
    key=(13,'fc1',0,references['13']['fc1'][0]['selected_shift']);packet,raw=wire[key];chain=cases[13]['chains']['fc1']
    def attempt(callback=submit,packet_value=packet,part='fc1',start=0,chain_value=chain):
        g=SavedWireCheck(references,callback);return g(13,part,chain_value,start,key[3],packet_value)
    count=len(submits)
    reject('packet-byte',lambda:attempt(packet_value=bytes([packet[0]^1])+packet[1:]))
    reject('packet-short',lambda:attempt(packet_value=packet[:-1]))
    reject('part-order',lambda:attempt(part='fc2'));reject('batch-order',lambda:attempt(start=32))
    reject('output-geometry',lambda:attempt(chain_value=dict(chain,output_bytes=1)))
    assert len(submits)==count
    reject('output-byte',lambda:attempt(callback=lambda *x:bytes([raw[0]^1])+raw[1:]))
    reject('output-short',lambda:attempt(callback=lambda *x:raw[:-1]))
    reject('incomplete',lambda:SavedWireCheck(references,submit).require_complete())
    def fail_second(index,part,chain,start,shift,packet):
        if index==14:raise RuntimeError('Explicit completed fake transaction failure')
        return submit(index,part,chain,start,shift,packet)
    def interrupted():
        with torch.inference_mode(),PLRangeScope(torch,layers,targets,load,initial,host,sink,lambda x:None,
              lambda *x:None,SavedWireCheck(references,fail_second)):forward()
    reject('second-layer-restoration',interrupted)
    light=LightBatchCheck(references,submit)
    for index in late:
        for part in ('fc1','fc2'):
            for ref in references[str(index)][part]:
                packet,raw=wire[(index,part,ref['start'],ref['selected_shift'])]
                assert light(index,part,cases[index]['chains'][part],ref['start'],ref['selected_shift'],packet)==raw
    light.require_complete();light_negative=[]
    packet,raw=wire[key]
    def light_reject(name,fn):
        try:fn()
        except (ValueError,RuntimeError):light_negative.append(name)
        else:raise AssertionError('Invalid timed schedule accepted:'+name)
    def call_light(index=13,part='fc1',start=0,shift=key[3],packet_value=packet,chain_value=chain,callback=submit):
        return LightBatchCheck(references,callback)(index,part,chain_value,start,shift,packet_value)
    light_reject('order',lambda:call_light(index=14));light_reject('part',lambda:call_light(part='fc2'))
    light_reject('start',lambda:call_light(start=32));light_reject('shift',lambda:call_light(shift=-1))
    light_reject('input-size',lambda:call_light(packet_value=packet[:-1]))
    light_reject('geometry',lambda:call_light(chain_value=dict(chain,output_bytes=1)))
    light_reject('output-size',lambda:call_light(callback=lambda *x:raw[:-1]))
    light_reject('incomplete',lambda:LightBatchCheck(references,submit).require_complete())
    return dict(timed_light_negative_checks=light_negative,full_output_exact=True,all24_boundaries_exact=True,unchanged_prefix_through12=True,
        complete_wire_batches=286,staged_windows=22,peak_live_layer_scopes=1,restored=clean(),
        actual_frozen_wrappers_encoder_M207_and_PL_binding=True,synthetic_narrow_weights_and_attention=True,
        fake_PL_submit=True,no_DMA_or_Overlay=True,negative_checks=rejected,model_quality_or_performance=False)
