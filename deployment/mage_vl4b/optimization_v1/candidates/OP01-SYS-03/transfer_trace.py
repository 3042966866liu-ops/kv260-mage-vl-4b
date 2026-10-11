"""Instrument pinned original statements, retaining file/chunk/copy semantics."""
import ast
from contextlib import contextmanager
import hashlib
import inspect
import textwrap

EXPECTED_AST='abbc9792563c2c302c0cc4c07118f63f61448aa076e21bd101b6a525edba1f25'


def instrument(original, trace, source=None):
    tree=ast.parse(textwrap.dedent(source or inspect.getsource(original)))
    function=tree.body[0]
    digest=hashlib.sha256(ast.dump(function,include_attributes=False).encode()).hexdigest()
    if digest!=EXPECTED_AST:
        raise RuntimeError('Unreviewed weight-copy implementation; no instrumentation installed')
    class AddSpans(ast.NodeTransformer):
        counts={}
        def tagged(self,node,label):
            self.counts[label]=self.counts.get(label,0)+1
            wrapper=ast.parse(f'with _decode_transfer_trace.span("{label}"): pass').body[0]
            wrapper.body=[node]
            return ast.copy_location(wrapper,node)
        def visit_Assign(self,node):
            if isinstance(node.targets[0],ast.Name) and node.targets[0].id=='block':
                return self.tagged(node,'weight_file_read')
            if isinstance(node.targets[0],ast.Subscript):
                return self.tagged(node,'weight_cma_copy')
            return node
        def visit_Expr(self,node):
            value=node.value
            if isinstance(value,ast.Call) and isinstance(value.func,ast.Attribute) and value.func.attr=='sync_to_device':
                return self.tagged(node,'weight_cache_sync')
            return node
    transform=AddSpans();tree=transform.visit(tree);ast.fix_missing_locations(tree)
    if transform.counts!={'weight_file_read':1,'weight_cma_copy':1,'weight_cache_sync':1}:
        raise RuntimeError('Unexpected trace injection count')
    namespace=dict(original.__globals__);namespace['_decode_transfer_trace']=trace
    exec(compile(tree,'<pinned-weight-transfer-trace>','exec'),namespace)
    return namespace[function.name]


@contextmanager
def trace_transfer(module,trace):
    original=module.copy_window_to_buffer
    replacement=instrument(original,trace)
    module.copy_window_to_buffer=replacement
    try:
        yield
    finally:
        module.copy_window_to_buffer=original
