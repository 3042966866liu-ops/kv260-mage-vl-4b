"""Draft full Prefill borrowed-result adapter; no board or package creation."""
from m351_workflow import HERE,BASE,sha,atomic

def main():
    old=BASE/'candidates/M392-silu-layer-02/m392_silu_scope.py';assert sha(old)==sha(HERE/'m392_silu_scope.py')
    s=old.read_text(encoding='utf-8').replace('M392','M393').replace('_m392_lease','_m393_lease')
    s=s.replace('from m389_silu_workspace import SiluWorkspace','from m393_silu_workspace import SiluWorkspace')
    s=s.replace('self.workspace=None;self.workspace_ref=None;self.buffer_ref=None','self.workspace=None;self.workspace_ref=None;self.buffer_ref=None;self.workspace_bytes=0')
    s=s.replace('self.workspace_ref=weakref.ref(self.workspace);self.buffer_ref=weakref.ref(self.workspace._buffer)','self.workspace_ref=weakref.ref(self.workspace);self.buffer_ref=weakref.ref(self.workspace._buffer);self.workspace_bytes=int(self.workspace._buffer.nbytes)')
    start=s.index('    def bind(self,module,generated):');end=s.index('        count=0',start)
    s=s[:start]+'''    def bind(self,module):
        import copy
        import hashlib
        from pathlib import Path
        source=Path(module.__file__).read_bytes()
        if hashlib.sha256(source).hexdigest()!='24f419ea8e0f130cefc8eb51f916dca3fb945b84f0dc8e73dec9f5376be3ad09':raise RuntimeError('Actual original Prefill source differs')
        original=ast.parse(source.decode('utf-8'))
        cls=next(n for n in original.body if isinstance(n,ast.ClassDef) and n.name=='M241VideoLanguageModel')
        original_fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='prefill')
        fn=copy.deepcopy(original_fn);tree=ast.Module(body=[fn],type_ignores=[])
        loop=next(n for n in fn.body if isinstance(n,ast.For))
'''+s[end:]
    s=s.replace("namespace=dict(vars(module));namespace['LAYERS']=1;namespace['_m393_lease']=self.lease","namespace=dict(vars(module));namespace['_m393_lease']=self.lease")
    s=s.replace("return namespace['one_layer']","return namespace['prefill']").replace("original=namespace['one_layer']","original=namespace['prefill']")
    s=s.replace("workspace_bytes=6187008","workspace_bytes=self.workspace_bytes")
    atomic(HERE/'m393_silu_scope.py',s.encode('utf-8'))
    w=(BASE/'candidates/M389-silu-workspace-component-01/m389_silu_workspace.py').read_text(encoding='utf-8')
    w=w.replace('M389 disabled by default','M393 disabled by default')
    w=w.replace('if tuple(shape) != (159, 9728):','if tuple(shape) not in ((30,9728),(159,9728)):')
    w=w.replace('Only the fixed component geometry is admitted','Only fixed30 text or fixed159 video geometry admitted')
    atomic(HERE/'m393_silu_workspace.py',w.encode('utf-8'))
    print('M393_DRAFT_FULL_PREFILL_SCOPE_READY')

if __name__=='__main__':main()
