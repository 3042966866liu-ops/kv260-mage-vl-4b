"""Default-off isolated final layer; full Attention/KV, original last T32 tail."""
import ast
import copy
import json
from pathlib import Path
import numpy as np
from m343_layer_scope import derive as original_layer
from m397_last_layer_tail_scope import LastLayerTailScope
from m399_tail_chain_scope import TailChainScope, RetainedChainOwnerError, identity, digest, PLAN
from m398_reference_capture import SHAPES
from m368_video_contract import tensor


def derive(source):
    tree = ast.parse(original_layer(source))
    fn = tree.body[0]
    loop = next(n for n in fn.body if isinstance(n, ast.For))
    original = copy.deepcopy(loop)
    loop.iter = ast.parse('range(35, 36)', mode='eval').body
    i = next(i for i, n in enumerate(loop.body)
             if isinstance(n, ast.Assign) and ast.unparse(n) == "projected = self._family(layer, 'attention_out', attended)")
    loop.body.insert(i, ast.parse('attended, residual = _m400_select(self, layer, attended, residual)').body[0])
    stripped = copy.deepcopy(loop)
    stripped.body.pop(i)
    stripped.iter = copy.deepcopy(original.iter)
    if ast.dump(stripped, include_attributes=False) != ast.dump(original, include_attributes=False):
        raise RuntimeError('Original layer arithmetic changed beyond range and tail boundary')
    return ast.unparse(ast.fix_missing_locations(tree))+'\n'


class TailLayerScope(TailChainScope):
    def __init__(self, model, policy, resident, reference_path, reference_sha, *, enabled=False):
        if not enabled:
            raise RuntimeError('M400 disabled by default')
        super().__init__(model, policy, resident, reference_path, reference_sha, enabled=True)
        r = json.loads(self.reference_path.read_text(encoding='utf-8'))
        if identity(self.reference_path) != self.raw_identity:
            raise RuntimeError('Reference changed while reading full layer metadata')
        self.original_qkv = next(x for x in r['video_result']['families'] if x['layer']==35 and x['family']=='qkv')
        self.expected_kv = dict(key=r['video_result']['keys'][35], value=r['video_result']['values'][35])
        self.tail = LastLayerTailScope(model, policy, resident, tokens=159, enabled=True)
        self.bindings=[]; self.family_rows=[]; self.result=None; self.invoked=False
        self.original_family=model._family
        self.had_instance_family='_family' in vars(model)
        self.instance_family=vars(model).get('_family')
        self.observer=None

    def load(self, name):
        if name in self.maps:
            return self.maps[name]
        if name == 'logits':
            raise RuntimeError('Single layer must not load or execute LM head')
        f=self.fixtures[name]; path=self.reference_path.parent/(name+'.npy')
        start=0 if name in ('attended_full','residual_full') else 158 if name=='final_norm' else 128
        if f['path']!=str(path) or f['tensor']['shape']!=list(SHAPES[name]) or f['tensor']['dtype']!='float32' or f['original_token_start']!=start:
            raise RuntimeError('Layer fixture contract differs: '+name)
        before=identity(path)
        if before[2]!=f['file_bytes'] or digest(path)!=f['file_sha256']:
            raise RuntimeError('Fixture file SHA differs: '+name)
        a=np.load(path,allow_pickle=False,mmap_mode='r'); self.maps[name]=a; self.identities[name]=before
        if a.dtype!=np.float32 or a.shape!=SHAPES[name] or not a.flags.c_contiguous or not np.isfinite(a).all() or tensor(a)!=f['tensor'] or identity(path)!=before:
            raise RuntimeError('Layer NPY identity/tensor differs: '+name)
        return a

    def exact(self, name, actual):
        expected=self.load(name)
        if actual.dtype!=np.float32 or actual.shape!=expected.shape or not np.array_equal(actual.view(np.uint32), expected.view(np.uint32)):
            raise RuntimeError('Complete tensor bitwise mismatch: '+name)
        return tensor(actual)

    def select(self, model, layer, attended, residual):
        self.barrier()
        self.exact('attended_full',attended); self.exact('residual_full',residual)
        return self.tail.select(model,layer,attended,residual)

    def observe(self, layer, family, values):
        expected_order=('qkv','attention_out','gate_up','mlp_down')
        if self.closed or self.retained or layer!=35 or len(self.family_rows)>=4 or family!=expected_order[len(self.family_rows)]:
            raise RetainedChainOwnerError('Unexpected layer family/order')
        self.barrier()
        if family=='qkv':
            if tensor(values)!=self.original_qkv['input']:
                raise RuntimeError('Full159 QKV input differs')
        else:
            plan=next(p for p in PLAN if p[0]==family)
            self.exact(plan[1],values)
        output=self.original_family(layer,family,values)
        self.barrier()
        metadata={k:tensor(v) for k,v in output.items()}
        if family=='qkv':
            if metadata!=self.original_qkv['output']:
                raise RuntimeError('Complete original QKV tensor SHA differs')
        else:
            prefix='model.language_model.layers.35.'
            if set(output)!={prefix+k for k in plan[2]}:
                raise RuntimeError('Tail family output keys differ')
            for key,name in plan[2].items():
                self.exact(name,output[prefix+key])
        self.check_unchanged()
        self.family_rows.append(dict(layer=layer,family=family,input=tensor(values),output=metadata))
        return output

    def run(self, module, generated):
        if self.closed or self.retained or self.invoked:
            raise RetainedChainOwnerError('Only one isolated layer invocation allowed')
        self.invoked=True
        try:
            self.barrier()
            if generated!=derive(Path(module.__file__).read_bytes()):
                raise RuntimeError('Generated final layer source differs')
            namespace=dict(vars(module)); namespace['_m400_select']=self.select
            exec(compile('from __future__ import annotations\n'+generated,'<m400-frozen-last-layer>', 'exec'),namespace)
            self.bindings.append(namespace)
            self.observer=self.observe
            self.model._family=self.observer
            hidden,kv=namespace['one_layer'](self.model,self.load('residual_full'))
            self.barrier()
            if len(self.family_rows)!=4 or len(kv.keys)!=1 or len(kv.values)!=1 or len(self.tail.selected)!=1:
                raise RuntimeError('Full final layer family/KV inventory incomplete')
            actual_kv=dict(key=tensor(kv.keys[0]),value=tensor(kv.values[0]))
            if actual_kv!=self.expected_kv:
                raise RuntimeError('Full159 final layer KV SHA differs')
            hidden_metadata=self.exact('hidden_tail',hidden)
            final=module.rms_norm(hidden[-1:],self.model.weight('model.language_model.norm.weight'))
            norm_metadata=self.exact('final_norm',final)
            self.check_unchanged()
            self.result=dict(families=list(self.family_rows),key=actual_kv['key'],value=actual_kv['value'],
                             attended_full=self.fixtures['attended_full']['tensor'],hidden_tail=hidden_metadata,final_norm=norm_metadata,
                             full_QKV_KV_SHA_equal=True,full_attention_and_tail_tensors_bitwise_equal=True,
                             last_layer=35,original_tokens=159,tail_start=128,tail_tokens=31,
                             grouped_attention_calls=1,LM_head_executed=False)
            del hidden,kv,final
            return dict(self.result)
        except BaseException as exc:
            self.retained=True
            raise RetainedChainOwnerError('Layer consumer/reference failure; retain scope, maps, original DMA and process') from exc

    def close(self):
        if self.closed:
            return
        if self.retained:
            raise RetainedChainOwnerError('Failed layer owner cannot be released')
        try:
            self.barrier(); self.check_unchanged()
            if self.observer is not None:
                if self.model._family is not self.observer:
                    raise RuntimeError('Family observer ownership changed')
                if self.had_instance_family:
                    self.model._family=self.instance_family
                else:
                    del self.model._family
            self.observer=None; self.original_family=None; self.instance_family=None
            for namespace in self.bindings:
                namespace.pop('_m400_select',None)
            self.bindings.clear()
            self.tail.close(); self.tail=None
            super().close()
        except BaseException as exc:
            self.retained=True
            raise RetainedChainOwnerError('Layer close failed; retain owner and maps') from exc

    def report(self):
        return dict(closed=self.closed,retained=self.retained,invoked=self.invoked,
                    reference_sha256=self.reference_sha,reference_files_checked=len(self.identities),
                    reference_maps_released=not self.maps,binding_callback_removed=not self.bindings,
                    original_family_restored=self.observer is None,family_rows=list(self.family_rows),
                    layer_result=self.result,extra_DMA=0,parser_workers=1,PS_prefetch=False,SiLU_workspace=False,
                    candidate_full_model_executed=False,performance_pass=False)
