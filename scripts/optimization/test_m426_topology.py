"""Frozen M90 precision constructor loop; synthetic metadata, no model forward."""
import ast,json,threading,time
from types import SimpleNamespace

def component(root):
    import torch
    from m408_target_component04 import actual_class
    from m426_range02 import resolve,prefix_evidence
    progress=actual_class(torch,root/'tmp/m223_realtime/m223_realtime_delta/m206_ps_vision_runtime.py','M206ProgressLayer',dict(_base=SimpleNamespace(_TorchModule=torch.nn.Module),_rss_mib=lambda:0.,threading=threading,time=time))
    boundary=actual_class(torch,root/'tmp/m227_runtime_base/m227_runtime_base_patch/ps_vision_runtime.py','M196PrecisionBoundary',dict(_TorchModule=torch.nn.Module))
    linear=actual_class(torch,root/'tmp/m223_realtime/m223_realtime_delta/m207_ps_vision_runtime.py','M207FP32GemmW4Linear',dict(_base=SimpleNamespace(_TorchModule=torch.nn.Module)))
    class MageVLVisionEncoderLayer(torch.nn.Module):
        def __init__(self,index,dtype):
            super().__init__();self.layer_norm1=torch.nn.LayerNorm(1024,dtype=dtype);self.layer_norm2=torch.nn.LayerNorm(1024,dtype=dtype);self.mlp=torch.nn.Module()
            for part,columns,rows in (('fc1',1024,4096),('fc2',4096,1024)):
                name=f'encoder.layers.{index}.mlp.{part}';store=SimpleNamespace(entries={name:dict(module='model.visual.'+name)})
                m=linear(torch,store,name,columns,rows,True,dtype);m.bias=torch.nn.Parameter(torch.zeros(rows,dtype=dtype),requires_grad=False);setattr(self.mlp,part,m)
    vision=SimpleNamespace(encoder=SimpleNamespace(layers=torch.nn.ModuleList([MageVLVisionEncoderLayer(i,torch.bfloat16 if i<2 else torch.float32) for i in range(24)])))
    source=root/'tmp/m227_runtime_base/m227_runtime_base_patch/ps_vision_runtime.py'
    tree=ast.parse(source.read_text(encoding='utf-8'));loops=[n for n in ast.walk(tree) if isinstance(n,ast.For) and isinstance(n.target,ast.Tuple) and ast.unparse(n.iter)=='enumerate(vision.encoder.layers)']
    assert len(loops)==1
    # Execute the original constructor statements; metadata model is explicit.
    loop=loops[0];ns=dict(torch=torch,vision=vision,M196PrecisionBoundary=boundary,self=SimpleNamespace(fp32_layers=tuple(range(2,24)),bf16_layers=(),compute_dtype=torch.bfloat16))
    exec(compile(ast.fix_missing_locations(ast.Module(body=[loop],type_ignores=[])),str(source),'exec'),ns)
    assert all(type(vision.encoder.layers[i]) is MageVLVisionEncoderLayer for i in (0,1))
    assert all(type(vision.encoder.layers[i]) is boundary for i in range(2,24))
    vision.encoder.layers=torch.nn.ModuleList([progress(l,index=i,heartbeat_seconds=30.,run_elapsed=lambda:0.) for i,l in enumerate(vision.encoder.layers)])
    targets,evidence=resolve(vision,progress,boundary,linear,torch);prefix=prefix_evidence(vision,progress,boundary,linear,torch)
    assert list(targets)==list(range(2,24)) and len(evidence)==22 and not any(v['conversion_wrapper'] for v in prefix.values())
    rejected=[]
    def reject(label,do,undo):
        do()
        try:
            try:resolve(vision,progress,boundary,linear,torch)
            except RuntimeError:rejected.append(label)
            else:raise AssertionError('Wrong topology accepted '+label)
        finally:undo()
        resolve(vision,progress,boundary,linear,torch)
    outer=vision.encoder.layers[0];native=outer.layer
    reject('unexpected-prefix-wrapper',lambda:setattr(outer,'layer',boundary(native,torch.bfloat16,torch.bfloat16)),lambda:setattr(outer,'layer',native))
    norm=native.layer_norm1;old=norm.weight
    reject('prefix-norm-FP32',lambda:setattr(norm,'weight',torch.nn.Parameter(old.float())),lambda:setattr(norm,'weight',old))
    m=native.mlp.fc1;reject('prefix-Linear-FP32',lambda:setattr(m,'output_dtype',torch.float32),lambda:setattr(m,'output_dtype',torch.bfloat16))
    outer=vision.encoder.layers[2];wrapped=outer.layer
    reject('missing-selected-wrapper',lambda:setattr(outer,'layer',wrapped.layer),lambda:setattr(outer,'layer',wrapped))
    reject('selected-BF16',lambda:setattr(wrapped,'target_dtype',torch.bfloat16),lambda:setattr(wrapped,'target_dtype',torch.float32))
    reject('wrong-progress-index',lambda:setattr(outer,'index',3),lambda:setattr(outer,'index',2))
    m=wrapped.layer.mlp.fc1;reject('selected-geometry',lambda:setattr(m,'out_features',2048),lambda:setattr(m,'out_features',4096))
    entry=m.store.entries[m.name];name=entry['module'];reject('selected-store-binding',lambda:entry.update(module='wrong'),lambda:entry.update(module=name))
    return dict(actual_frozen_M90_constructor_loop=True,actual_frozen_M206_M196_M207=True,synthetic_metadata_no_model_forward=True,
        native_unwrapped_BF16_prefix=[0,1],selected_layers=list(targets),selected_FP32_to_BF16_wrappers=22,negative_checks=rejected)
