"""Observe the three original stable DMA dispatches without changing their AST.

No hardware imports. A failed or unresolved physical submission stays active;
the outer runner must retain its process, lock, Overlay and every buffer.
"""
import ast
import copy
import hashlib
import inspect
import textwrap
import time
import types

BUILD = 0x4D395832
METHODS = ('_launch_prepacked', '_launch_once', '_execute')


def completed(snapshot):
    for name in ('kernel_read_error', 'return_read_error', 'dma_read_error'):
        if snapshot.get(name) != '': return False
    for name in ('ap_ctrl', 'ap_return', 'mm2s_dmasr', 's2mm_dmasr'):
        if type(snapshot.get(name)) is not int or snapshot[name] < 0: return False
    if snapshot['ap_return'] != BUILD or not snapshot['ap_ctrl'] & 4: return False
    for channel in ('mm2s', 's2mm'):
        if snapshot.get(channel + '_error') is not False: return False
        status = snapshot[channel + '_dmasr']
        if not status & 3 or status & 0x770: return False
    return True


class TransactionGuard:
    def __init__(self, chains, snapshot_reader, check_before, result, clock=time.monotonic_ns):
        self.chains = copy.deepcopy(chains)
        self.snapshot_reader, self.check_before, self.result, self.clock = snapshot_reader, check_before, result, clock
        self.active = self.ever = self.complete = False
        self.current = None
        self.bindings = []

    def safe(self):
        if self.active: return False
        snapshot = self.snapshot_reader()
        if self.ever: return self.complete and completed(snapshot)
        return (all(snapshot.get(k) == '' for k in ('kernel_read_error', 'return_read_error', 'dma_read_error'))
            and snapshot.get('ap_ctrl') == 4 and snapshot.get('ap_return') == 0
            and snapshot.get('mm2s_dmasr') == snapshot.get('s2mm_dmasr') == 0
            and snapshot.get('mm2s_error') is False and snapshot.get('s2mm_error') is False)

    def before(self, method, chain, input_bytes, output_bytes):
        if method not in METHODS or chain not in self.chains:
            raise RuntimeError('Unregistered original stable dispatch or chain')
        if input_bytes != int(chain['input_bytes']) or output_bytes != int(chain['output_bytes']):
            raise RuntimeError('Original transaction byte count differs')
        self.check_before()  # Configuration, original owner identity, clocks, memory.
        if not self.safe(): raise RuntimeError('Previous or initial DMA state unproven')
        row = dict(method=method, chain_index=chain['chain_index'], layer=chain.get('layer'),
            family=chain.get('family', 'lm_head'), input_bytes=input_bytes, output_bytes=output_bytes,
            submitted_boundary_ns=self.clock(), completed=False)
        self.result.setdefault('transactions', []).append(row)
        self.current = row
        self.active = self.ever = True
        self.complete = False

    def after(self, snapshot):
        if not self.active or self.current is None or not completed(snapshot):
            raise RuntimeError('Physical completion or Build unproven; retain owners')
        self.current.update(completed=True, completed_boundary_ns=self.clock(), snapshot=copy.deepcopy(snapshot))
        self.active = False
        self.complete = True
        self.current = None

    def bind(self, runtime, method):
        if method not in METHODS or any(name == method for _, name, _, _ in self.bindings):
            raise RuntimeError('Invalid or repeated method binding')
        original = getattr(runtime, method)
        function = original.__func__
        if function.__code__.co_freevars: raise RuntimeError('Unexpected executor closure')
        source = textwrap.dedent(inspect.getsource(function))
        tree, proof = instrument(source, method)
        namespace = dict(function.__globals__); namespace['_m523_dma_guard'] = self
        exec(compile(tree, '<m523-observed-original-' + method + '>', 'exec'), namespace)
        observed = types.MethodType(namespace[function.__name__], runtime)
        present, previous = method in vars(runtime), vars(runtime).get(method)
        self.bindings.append((runtime, method, present, previous))
        setattr(runtime, method, observed)
        return proof

    def restore_methods(self):
        if not self.safe(): raise RuntimeError('Cannot unwind bindings of unknown DMA owner')
        for runtime, method, present, previous in reversed(self.bindings):
            if present: setattr(runtime, method, previous)
            else: delattr(runtime, method)
        self.bindings = []


def instrument(source, method):
    original = ast.parse(textwrap.dedent(source), feature_version=(3, 10))
    if len(original.body) != 1 or not isinstance(original.body[0], ast.FunctionDef) or original.body[0].name != method:
        raise RuntimeError('Exact named function required')
    recv_source = ('self.dma.recvchannel.transfer(self.output_buffer, nbytes=output_bytes)' if method == '_execute'
        else 'self.dma.recvchannel.transfer(output_buffer, nbytes=int(chain["output_bytes"]))')
    recv = ast.parse(recv_source).body[0]
    count = ast.parse('self.host_calls += 1').body[0]
    before = ast.parse('_m523_dma_guard.before(' + repr(method) + ', chain, input_bytes, int(chain["output_bytes"]))').body[0]
    after = ast.parse('_m523_dma_guard.after(snapshot)').body[0]
    hits = [0, 0]
    class Insert(ast.NodeTransformer):
        def visit_Expr(self, node):
            if ast.dump(node) == ast.dump(recv): hits[0] += 1; return [copy.deepcopy(before), node]
            return self.generic_visit(node)
        def visit_AugAssign(self, node):
            if ast.dump(node) == ast.dump(count): hits[1] += 1; return [node, copy.deepcopy(after)]
            return self.generic_visit(node)
    tree = Insert().visit(copy.deepcopy(original))
    if hits != [1, 1]: raise RuntimeError('Original receive/accounting anchors differ')
    class Strip(ast.NodeTransformer):
        def visit_Expr(self, node):
            if ast.dump(node) in (ast.dump(before), ast.dump(after)): return None
            return self.generic_visit(node)
    if ast.dump(Strip().visit(copy.deepcopy(tree))) != ast.dump(original):
        raise RuntimeError('Original mathematical/control AST changed')
    proof = dict(method=method, original_source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        inserted_calls=2, stripped_ast_equals_original=True, inside_each_original_retry=True)
    return ast.fix_missing_locations(tree), proof


def finalize_guard(action, must_retain, retain):
    """Evidence I/O must not unwind an unresolved programming or DMA owner."""
    try: return action()
    except BaseException:
        if must_retain(): retain()
        raise
