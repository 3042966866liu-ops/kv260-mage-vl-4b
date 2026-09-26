"""Instrument pinned original statements, retaining file/chunk/copy semantics."""
import ast
from contextlib import contextmanager
import hashlib
import inspect
import textwrap

EXPECTED_SOURCE='56825701b6bda461c87340986bd67165a7bca59d7652a055bbb7bb2d8b3597d9'


def instrument(original, trace, source=None):
    source=textwrap.dedent(source or inspect.getsource(original)).strip().replace('\r\n','\n')
    digest=hashlib.sha256(source.encode()).hexdigest()
    tree=ast.parse(source)
    function=tree.body[0]
    if digest!=EXPECTED_SOURCE:
        raise RuntimeError('Unreviewed weight-copy implementation; source_sha256='+digest)
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
