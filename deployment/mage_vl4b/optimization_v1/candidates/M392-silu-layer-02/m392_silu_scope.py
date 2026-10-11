"""Isolated original layer-loop binder with one borrowed mlp_down workspace.

No frozen release file is changed. Consumers remain synchronous; a failed
consumer or barrier retains the owner and blocks DMA cleanup.
"""
import ast
from contextlib import contextmanager
import threading
import weakref
from m389_silu_workspace import SiluWorkspace

class RetainedSiluOwnerError(RuntimeError):pass

class SiluLayerScope:
    def __init__(self,model,policy,resident,*,enabled=False):
        if not enabled:raise RuntimeError('M392 disabled by default')
        if not resident() or not policy.safe():raise RuntimeError('Complete runtime/minimal completion required')
        self.model=model;self.policy=policy;self.resident=resident
        self.workspace=None;self.workspace_ref=None;self.buffer_ref=None
        self.bindings=[];self.retained=False;self.calls=0;self.closed=False;self.events=[]
    @contextmanager
    def lease(self,model,gate,up):
        if model is not self.model or self.closed or self.retained:raise RetainedSiluOwnerError('Wrong/busy closed scope')
        try:
            self.barrier('before-silu')
            if self.workspace is None:
                self.workspace=SiluWorkspace(gate.shape,enabled=True)
                self.workspace_ref=weakref.ref(self.workspace);self.buffer_ref=weakref.ref(self.workspace._buffer)
            with self.workspace.lease(gate,up) as value:
                yield value
                self.barrier('after-mlp-down-before-reuse')
            self.calls+=1
        except BaseException as exc:
            self.retained=True
            raise RetainedSiluOwnerError('Consumer/barrier failed; retain workspace/DMA owner') from exc
    def barrier(self,label):
        self.policy.capture(label,True)
        if not self.resident() or not self.policy.safe() or any(t.name.startswith(('m238-parse','m238-pack')) for t in threading.enumerate()):
            raise RetainedSiluOwnerError('DMA, complete runtime or original futures not drained')
        self.events.append(label)
    def bind(self,module,generated):
        from m343_layer_scope import derive
        from pathlib import Path
        if generated!=derive(Path(module.__file__).read_bytes()):raise RuntimeError('Frozen original layer source differs')
        tree=ast.parse(generated);fn=tree.body[0];loop=next(n for n in fn.body if isinstance(n,ast.For))
        count=0
        for i,n in enumerate(loop.body):
            if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='down_input':
                nxt=loop.body[i+1]
                if ast.unparse(n.value)!='silu(gate_up[f\'{prefix}.mlp.gate_proj\']) * gate_up[f\'{prefix}.mlp.up_proj\']':raise RuntimeError('Original activation changed')
                if ast.unparse(nxt)!="down = self._family(layer, 'mlp_down', down_input)":raise RuntimeError('Original consumer boundary changed')
                replacement=ast.parse("with _m392_lease(self, gate_up[f'{prefix}.mlp.gate_proj'], gate_up[f'{prefix}.mlp.up_proj']) as down_input:\n    down = self._family(layer, 'mlp_down', down_input)\n").body[0]
                # The exact consumer statement is reused, including all original retry paths.
                replacement.body[0]=nxt
                loop.body[i:i+2]=[replacement];count+=1;break
        if count!=1:raise RuntimeError('Expected exactly one activation/consumer pair')
        ast.fix_missing_locations(tree)
        namespace=dict(vars(module));namespace['LAYERS']=1;namespace['_m392_lease']=self.lease
        exec(compile(tree,'<m392-only-SiLU-workspace>', 'exec'),namespace)
        self.bindings.append(namespace)
        original=namespace['one_layer']
        def invoke(model,hidden):
            if self.closed or self.retained or model is not self.model:
                raise RetainedSiluOwnerError('Stale layer binding refused before any family')
            self.barrier('before-layer-workspace-scope')
            return original(model,hidden)
        return invoke
    def close(self):
        if self.retained or (self.workspace is not None and (self.workspace._active or self.workspace._retained)):
            raise RetainedSiluOwnerError('Consumer not complete; do not clear bindings/workspace')
        self.barrier('before-workspace-close')
        if self.workspace is not None:self.workspace.close();self.workspace=None
        for namespace in self.bindings:namespace.pop('_m392_lease',None)
        self.bindings.clear();self.model=None;self.resident=None;self.closed=True
        if self.buffer_ref is not None and self.buffer_ref() is not None:raise RetainedSiluOwnerError('Borrowed result still retained')
        if self.workspace_ref is not None and self.workspace_ref() is not None:raise RetainedSiluOwnerError('Workspace object still retained')
    def report(self):
        return dict(calls=self.calls,closed=self.closed,retained=self.retained,events=list(self.events),workspace_bytes=6187008,
                    workspace_object_released=self.workspace_ref is None or self.workspace_ref() is None,
                    workspace_buffer_released=self.buffer_ref is None or self.buffer_ref() is None,
                    binding_callback_removed=not self.bindings)
