"""Deterministic, stdlib-only M400 source guard for use before Overlay load."""
import ast
import copy
import hashlib
from pathlib import Path
import textwrap

M241_SHA = '24f419ea8e0f130cefc8eb51f916dca3fb945b84f0dc8e73dec9f5376be3ad09'
SELECT = '        attended, residual = _m400_select(self, layer, attended, residual)\n'


def derive(source):
    if hashlib.sha256(source).hexdigest() != M241_SHA:
        raise RuntimeError('Original M241 source SHA differs')
    text = source.decode('utf-8')
    tree = ast.parse(text)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'M241VideoLanguageModel')
    fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'prefill')
    loop = next(n for n in fn.body if isinstance(n, ast.For))
    expected_iter = ast.parse('range(LAYERS)', mode='eval').body
    if not isinstance(loop.target, ast.Name) or loop.target.id != 'layer' or ast.dump(loop.iter) != ast.dump(expected_iter):
        raise RuntimeError('Original layer boundary differs')
    lines = text.splitlines(keepends=True)
    extracted = textwrap.dedent(''.join(lines[fn.lineno-1:loop.end_lineno]))
    _, rest = extracted.split('\n', 1)
    base = 'def one_layer(self, hidden):\n'+rest+'    return hidden, KVCache(keys, values)\n'
    anchor = '        projected = self._family(layer, "attention_out", attended)\n'
    boundary = '    for layer in range(LAYERS):\n'
    if base.count(anchor) != 1 or base.count(boundary) != 1:
        raise RuntimeError('Pinned source anchors differ')
    candidate = base.replace(boundary, '    for layer in range(35, 36):\n').replace(anchor, SELECT+anchor)
    original_tree = ast.parse(base)
    restored = copy.deepcopy(ast.parse(candidate))
    original_loop = next(n for n in original_tree.body[0].body if isinstance(n, ast.For))
    restored_loop = next(n for n in restored.body[0].body if isinstance(n, ast.For))
    selected = [i for i, n in enumerate(restored_loop.body) if isinstance(n, ast.Assign)
                and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name)
                and n.value.func.id == '_m400_select']
    if len(selected) != 1:
        raise RuntimeError('Exactly one tail boundary required')
    restored_loop.body.pop(selected[0])
    restored_loop.iter = copy.deepcopy(original_loop.iter)
    # Both trees are parsed here, by this interpreter; no cross-version AST artifact.
    if ast.dump(restored, include_attributes=False) != ast.dump(original_tree, include_attributes=False):
        raise RuntimeError('Original arithmetic changed beyond tail boundary/range')
    compile('from __future__ import annotations\n'+candidate, '<m400-source-guard-02>', 'exec')
    return candidate


def validate(source, frozen, expected_frozen_sha):
    if hashlib.sha256(frozen).hexdigest() != expected_frozen_sha:
        raise RuntimeError('Frozen source SHA differs')
    if frozen != derive(source).encode('utf-8'):
        raise RuntimeError('Deterministic extracted source differs')
    return dict(original_source_sha256=M241_SHA, frozen_sha256=expected_frozen_sha,
                deterministic_source_equal=True, same_interpreter_AST_arithmetic_equal=True,
                uses_ast_unparse=False, imports_numpy_or_pynq=False)


if __name__ == '__main__':
    import json
    import sys
    if len(sys.argv) != 4:
        raise SystemExit('original-source frozen-source expected-frozen-sha')
    print(json.dumps(validate(Path(sys.argv[1]).read_bytes(), Path(sys.argv[2]).read_bytes(), sys.argv[3])))
