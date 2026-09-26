"""Extract only layer zero from the pinned Decode method without changing math.

AST is compared/transformed within one interpreter, never used as a cross-version
identity. Exact file SHA is the identity. No arithmetic statement is rewritten.
"""
import ast
import hashlib
import inspect
from pathlib import Path
import textwrap
from types import MethodType

SOURCE_SHA = 'fae70964171580dc8329700e99aa0b25f27b752e9d4274c5bae72fa19f30cf61'


def bind_layer_zero(model):
    method = model.decode.__func__
    path = Path(inspect.getfile(method))
    if hashlib.sha256(path.read_bytes()).hexdigest() != SOURCE_SHA:
        raise ValueError('Decode source file identity differs')
    tree = ast.parse(textwrap.dedent(inspect.getsource(method)))
    fn = tree.body[0]
    loops = [n for n in fn.body if isinstance(n, ast.For)]
    if len(loops) != 1 or ast.unparse(loops[0].iter) != 'range(LAYERS)':
        raise ValueError('Decode loop structure differs')
    if [ast.unparse(n) for n in fn.body[-3:]] != [
        "final = rms_norm(hidden, self.weight('model.language_model.norm.weight'))",
        'logits = self.runtime.lm_head(final)[0]',
        'return (int(np.argmax(logits)), logits)']:
        raise ValueError('Decode tail differs')
    loops[0].iter.args[0] = ast.Constant(value=1)
    fn.body[-3:] = [ast.Return(value=ast.Tuple(elts=[ast.Name(id='hidden',ctx=ast.Load()),
                                                  ast.Name(id='cache',ctx=ast.Load())],ctx=ast.Load()))]
    fn.name = 'decode_layer_zero'
    ast.fix_missing_locations(tree)
    namespace = dict(method.__globals__)
    exec(compile(tree, str(path)+'::layer-zero-probe', 'exec'), namespace)
    return MethodType(namespace[fn.name], model)
