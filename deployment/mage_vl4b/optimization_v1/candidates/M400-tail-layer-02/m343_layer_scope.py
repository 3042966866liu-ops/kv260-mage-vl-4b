"""Extract the unchanged M241 layer loop; exclude final norm and LM head."""
import ast
import hashlib
import textwrap

M241_SHA = '24f419ea8e0f130cefc8eb51f916dca3fb945b84f0dc8e73dec9f5376be3ad09'


def derive(source):
    if hashlib.sha256(source).hexdigest() != M241_SHA:
        raise RuntimeError('M241 source identity mismatch')
    text = source.decode('utf-8')
    tree = ast.parse(text)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'M241VideoLanguageModel')
    fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'prefill')
    loop = next(n for n in fn.body if isinstance(n, ast.For))
    if ast.unparse(loop.target) != 'layer' or ast.unparse(loop.iter) != 'range(LAYERS)':
        raise RuntimeError('Unexpected layer boundary')
    lines = text.splitlines(keepends=True)
    result = textwrap.dedent(''.join(lines[fn.lineno - 1:loop.end_lineno]))
    # Only the signature/name and the return boundary change. All layer statements
    # and original imports/functions remain identical to the accepted module.
    first, rest = result.split('\n', 1)
    result = 'def one_layer(self, hidden):\n' + rest + '    return hidden, KVCache(keys, values)\n'
    generated = ast.parse(result).body[0]
    if ast.dump(loop, include_attributes=False) != ast.dump(generated.body[-2], include_attributes=False):
        raise RuntimeError('Layer arithmetic changed during extraction')
    return result


def bind(module, generated):
    if derive(open(module.__file__, 'rb').read()) != generated:
        raise RuntimeError('Frozen layer extraction mismatch')
    namespace = dict(vars(module))
    namespace['LAYERS'] = 1
    exec(compile(generated, '<m343-frozen-M241-layer0>', 'exec'), namespace)
    return namespace['one_layer']
