"""Capture only missing original layer35 fixtures. No numerical change or DMA.

The original full159 Prefill is source-bound; three observation calls strip back
to its exact AST. Arrays are serialized synchronously and never retained here.
"""
import ast
import copy
import hashlib
import os
from pathlib import Path
import shutil
import threading
import numpy as np
from m368_video_contract import tensor
from measurement import sha256

SOURCE_SHA='24f419ea8e0f130cefc8eb51f916dca3fb945b84f0dc8e73dec9f5376be3ad09'
SHAPES={'attended_full':(159,4096),'residual_full':(159,2560),
        'attention_out_input_tail':(31,4096),'attention_out_output_tail':(31,2560),
        'gate_up_input_tail':(31,2560),'gate_tail':(31,9728),'up_tail':(31,9728),
        'mlp_down_input_tail':(31,9728),'mlp_down_output_tail':(31,2560),
        'hidden_tail':(31,2560),'final_norm':(1,2560),'logits':(151936,)}
PAYLOAD_BYTES=sum(int(np.prod(s))*4 for s in SHAPES.values())

class RetainedReferenceOwnerError(RuntimeError):pass

class LastLayerReferenceCapture:
    def __init__(self,model,policy,resident,destination,*,enabled=False):
        if not enabled:raise RuntimeError('M398 disabled by default')
        self.model=model;self.policy=policy;self.resident=resident;self.destination=Path(destination)
        self.fixtures={};self.bindings=[];self.closed=False;self.retained=False;self.invoked=False
        self.last_families=[];self.steps=[]
        self.barrier()
        if not self.destination.is_dir() or shutil.disk_usage(self.destination).free<64<<20:raise RuntimeError('Existing evidence dir and64MiB disk margin required')
        if any((self.destination/(n+'.npy')).exists() or (self.destination/(n+'.npy.part')).exists() for n in SHAPES):raise RuntimeError('Immutable fixture already exists')
    def barrier(self):
        if not self.resident() or not self.policy.safe() or any(t.name.startswith(('m238-pack','m238-parse')) for t in threading.enumerate()):
            raise RetainedReferenceOwnerError('Complete runtime, original futures and safe DMA required')
    def save(self,name,value):
        if self.closed or self.retained or name not in SHAPES or name in self.fixtures:raise RuntimeError('Unexpected/duplicate fixture')
        self.barrier()
        a=np.asarray(value)
        if a.dtype!=np.float32 or a.shape!=SHAPES[name] or not a.flags.c_contiguous or not np.isfinite(a).all():raise RuntimeError('Actual fixture layout/finite contract differs: '+name)
        before=tensor(a);path=self.destination/(name+'.npy');part=path.with_suffix('.npy.part')
        if path.exists() or part.exists():raise RuntimeError('Cannot overwrite original fixture')
        with part.open('xb') as f:
            np.save(f,a,allow_pickle=False);f.flush();os.fsync(f.fileno())
        # Validate exact NPY tensor semantics without materializing another array.
        saved=np.load(part,allow_pickle=False,mmap_mode='r')
        try:
            if tensor(saved)!=before or tensor(a)!=before:raise RuntimeError('Saved tensor or source changed')
        finally:saved._mmap.close();del saved
        if not a.nbytes<part.stat().st_size<=a.nbytes+512:raise RuntimeError('NPY header/size differs')
        os.replace(part,path)
        self.fixtures[name]=dict(path=str(path),file_bytes=path.stat().st_size,file_sha256=sha256(path),tensor=before,
                                 original_token_start=128 if name.endswith('_tail') or name in ('gate_tail','up_tail','hidden_tail') else 158 if name in ('final_norm','logits') else 0)
        if sum(r['file_bytes'] for r in self.fixtures.values())>16<<20:raise RuntimeError('Fixture file budget exceeded')
        self.policy.capture('after-reference-fixture:'+name,True)
    def attention(self,model,layer,attended,residual):
        if model is not self.model:raise RuntimeError('Wrong model owner')
        if layer==35:
            self.steps.append('full-attention')
            self.save('attended_full',attended);self.save('residual_full',residual)
    def family(self,layer,name,values,output):
        if layer!=35 or name not in ('attention_out','gate_up','mlp_down'):return
        if self.last_families!=list(('attention_out','gate_up','mlp_down')[:len(self.last_families)]) or name!=('attention_out','gate_up','mlp_down')[len(self.last_families)]:raise RuntimeError('Last-layer family sequence differs')
        self.last_families.append(name)
        prefix='model.language_model.layers.35'
        self.save(name+'_input_tail',values[128:])
        if name=='attention_out':self.save('attention_out_output_tail',output[prefix+'.self_attn.o_proj'][128:])
        elif name=='gate_up':
            self.save('gate_tail',output[prefix+'.mlp.gate_proj'][128:]);self.save('up_tail',output[prefix+'.mlp.up_proj'][128:])
        else:self.save('mlp_down_output_tail',output[prefix+'.mlp.down_proj'][128:])
    def hidden(self,model,hidden):
        if model is not self.model or hidden.shape!=(159,2560):raise RuntimeError('Full original hidden must remain')
        self.steps.append('full-hidden');self.save('hidden_tail',hidden[128:])
    def final(self,model,final):
        if model is not self.model:raise RuntimeError('Wrong final owner')
        self.steps.append('original-final-norm');self.save('final_norm',final)
    def bind(self,module):
        if self.closed or self.retained or self.bindings:raise RuntimeError('One live original binding required')
        raw=Path(module.__file__).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA:raise RuntimeError('Frozen Prefill source differs')
        cls=next(n for n in ast.parse(raw.decode('utf-8')).body if isinstance(n,ast.ClassDef) and n.name=='M241VideoLanguageModel')
        original=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='prefill');fn=copy.deepcopy(original)
        loop=next(n for n in fn.body if isinstance(n,ast.For))
        before=next(i for i,n in enumerate(loop.body) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='projected')
        hook=ast.parse('_m398_attention(self, layer, attended, residual)').body[0];loop.body.insert(before,hook)
        final_i=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='final')
        fn.body.insert(final_i,ast.parse('_m398_hidden(self, hidden)').body[0])
        fn.body.insert(final_i+2,ast.parse('_m398_final(self, final)').body[0])
        stripped=copy.deepcopy(fn)
        def remove(body):
            body[:]=[n for n in body if not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id.startswith('_m398_'))]
            for n in body:
                if isinstance(n,ast.For):remove(n.body)
        remove(stripped.body)
        if ast.dump(stripped,include_attributes=False)!=ast.dump(original,include_attributes=False):raise RuntimeError('Capture modifies original math/control')
        ns=dict(vars(module));ns.update(_m398_attention=self.attention,_m398_hidden=self.hidden,_m398_final=self.final)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'<m398-unchanged-prefill-observations>','exec'),ns)
        self.bindings.append(ns);original_call=ns['prefill']
        def invoke(model,hidden):
            if self.invoked or self.closed or self.retained or model is not self.model or hidden.shape!=(159,2560):raise RetainedReferenceOwnerError('Wrong/stale original request')
            self.barrier();self.invoked=True
            try:
                answer=original_call(model,hidden)
                self.save('logits',answer[1])
                if self.last_families!=['attention_out','gate_up','mlp_down'] or set(self.fixtures)!=set(SHAPES) or self.steps!=['full-attention','full-hidden','original-final-norm']:raise RuntimeError('Capture incomplete')
                if any(a.shape!=(159,8,128) for a in answer[2].keys+answer[2].values) or len(answer[2].keys)!=36 or len(answer[2].values)!=36:raise RuntimeError('Full original KV incomplete')
                self.barrier();return answer
            except BaseException as exc:
                self.retained=True
                raise RetainedReferenceOwnerError('Capture failed; retain process, original DMA and owner') from exc
        return invoke
    def close(self):
        if self.closed:return
        if self.retained:raise RetainedReferenceOwnerError('Failed capture owner retained')
        self.barrier()
        for ns in self.bindings:
            for k in ('_m398_attention','_m398_hidden','_m398_final'):ns.pop(k,None)
        self.bindings.clear();self.model=self.policy=self.resident=None;self.closed=True
    def report(self):
        return dict(fixtures=dict(self.fixtures),file_count=len(self.fixtures),payload_bytes=PAYLOAD_BYTES,
                    file_bytes=sum(r['file_bytes'] for r in self.fixtures.values()),file_budget_bytes=16<<20,
                    last_families=list(self.last_families),steps=list(self.steps),closed=self.closed,retained=self.retained,
                    binding_callback_removed=not self.bindings,additional_dma_allocations=0,source_hooks=3,
                    removed_hooks_ast_equals_original=True,candidate_tail_not_executed=True)
