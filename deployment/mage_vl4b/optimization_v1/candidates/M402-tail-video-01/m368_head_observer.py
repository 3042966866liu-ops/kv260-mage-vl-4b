"""Instrument the frozen head executor's physical boundaries, without editing it."""
import ast
import copy
import hashlib
import inspect
import textwrap
import types
from board_safety import safe_to_release


class HeadObserver:
    def __init__(self, policy, chains):
        self.policy = policy
        self.chains = copy.deepcopy(chains)

    def before(self, chain, input_bytes, output_bytes):
        p = self.policy
        if chain not in self.chains or chain.get('layer') is not None or chain.get('family', 'lm_head') != 'lm_head':
            raise RuntimeError('Frozen head chain identity differs')
        if input_bytes != int(chain['input_bytes']) or output_bytes != int(chain['output_bytes']):
            raise RuntimeError('Head transaction byte count differs')
        p.capture('before-physical-launch:head-original-execute', True)
        if p.ever and not p.safe():
            raise RuntimeError('Previous transaction completion unproven')
        p.result.setdefault('transactions', []).append(dict(method='head-original-execute', chain_index=chain['chain_index'], layer=None, family='lm_head', input_bytes=input_bytes, output_bytes=output_bytes))
        p.active = p.ever = True
        p.completed = False

    def after(self, snapshot):
        p = self.policy
        if not p.active or not safe_to_release(snapshot) or snapshot['ap_return'] != p.build:
            raise RuntimeError('Head physical completion safety/build differs')
        p.active = False
        p.completed = True
        p.capture('after-physical-launch:head-original-execute', True)


def instrument_source(source):
    """Exactly two observation calls, inside every original retry iteration."""
    original = ast.parse(textwrap.dedent(source), feature_version=(3, 10))
    tree = copy.deepcopy(original)
    before = ast.parse('_m366_head_observer.before(chain, input_bytes, output_bytes)').body[0]
    after = ast.parse('_m366_head_observer.after(snapshot)').body[0]
    recv = ast.parse('self.dma.recvchannel.transfer(self.output_buffer, nbytes=output_bytes)').body[0]
    count = ast.parse('self.host_calls += 1').body[0]
    hits = [0, 0]

    class Insert(ast.NodeTransformer):
        def visit_Expr(self, node):
            if ast.dump(node) == ast.dump(recv):
                hits[0] += 1
                return [copy.deepcopy(before), node]
            return self.generic_visit(node)

        def visit_AugAssign(self, node):
            if ast.dump(node) == ast.dump(count):
                hits[1] += 1
                return [node, copy.deepcopy(after)]
            return self.generic_visit(node)

    tree = Insert().visit(tree)
    if hits != [1, 1]:
        raise RuntimeError('Frozen executor observation anchors differ')
    stripped = copy.deepcopy(tree)

    class Strip(ast.NodeTransformer):
        def visit_Expr(self, node):
            if ast.dump(node) in (ast.dump(before), ast.dump(after)):
                return None
            return self.generic_visit(node)

    stripped = Strip().visit(stripped)
    if ast.dump(stripped) != ast.dump(original):
        raise RuntimeError('Head executor mathematical/control AST changed')
    return ast.fix_missing_locations(tree)


def bind(original, policy, chains):
    function = original.__func__
    if function.__code__.co_freevars:
        raise RuntimeError('Unexpected executor closure')
    source = textwrap.dedent(inspect.getsource(function))
    tree = instrument_source(source)
    namespace = dict(function.__globals__)
    namespace['_m366_head_observer'] = HeadObserver(policy, chains)
    exec(compile(tree, '<m366-observed-frozen-head-executor>', 'exec'), namespace)
    observed = types.MethodType(namespace[function.__name__], original.__self__)
    proof = dict(original_module=function.__module__, original_function=function.__qualname__, original_function_source_sha256=hashlib.sha256(source.encode('utf-8')).hexdigest(), removed_observation_calls_ast_equals_original=True, inserted_observation_calls=2, every_retry_physical_boundary=True, exact_frozen_head_chains=len(chains))
    return observed, proof
