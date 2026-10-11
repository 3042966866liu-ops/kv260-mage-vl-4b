"""Stdlib deterministic complete Prefill source guard; no hardware imports."""
import ast
import copy
import hashlib
import textwrap
M241_SHA='24f419ea8e0f130cefc8eb51f916dca3fb945b84f0dc8e73dec9f5376be3ad09'
ANCHOR='        projected = self._family(layer, "attention_out", attended)\n'
SELECT='        if layer == LAYERS - 1:\n            attended, residual = _m397_select(self, layer, attended, residual)\n'

def derive(source):
    if hashlib.sha256(source).hexdigest()!=M241_SHA:raise RuntimeError('Original M241 source SHA differs')
    text=source.decode('utf-8');tree=ast.parse(text)
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='M241VideoLanguageModel')
    fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='prefill')
    base=textwrap.dedent(''.join(text.splitlines(keepends=True)[fn.lineno-1:fn.end_lineno]))
    if base.count(ANCHOR)!=1:raise RuntimeError('Exactly one original projection anchor required')
    candidate=base.replace(ANCHOR,SELECT+ANCHOR)
    old=ast.parse(base);new=ast.parse(candidate);restored=copy.deepcopy(new)
    loop=next(n for n in restored.body[0].body if isinstance(n,ast.For))
    inserts=[i for i,n in enumerate(loop.body) if isinstance(n,ast.If) and ast.dump(n,include_attributes=False)==ast.dump(ast.parse(SELECT.strip().replace('\n            ','\n    ')).body[0],include_attributes=False)]
    if len(inserts)!=1:raise RuntimeError('Exactly one final layer selector required')
    loop.body.pop(inserts[0])
    if ast.dump(restored,include_attributes=False)!=ast.dump(old,include_attributes=False):raise RuntimeError('Original Prefill changed beyond one selector')
    compile('from __future__ import annotations\n'+candidate,'<m401-source-precheck>','exec')
    return candidate

def validate(source,frozen,expected):
    if hashlib.sha256(frozen).hexdigest()!=expected or frozen!=derive(source).encode('utf-8'):raise RuntimeError('Full Prefill frozen source differs')
    return dict(original_source_sha256=M241_SHA,frozen_sha256=expected,deterministic_source_equal=True,
                same_interpreter_AST_arithmetic_equal=True,uses_ast_unparse=False,imports_numpy_or_pynq=False,
                full_layers=36,LM_head_preserved=True,inserted_tail_boundaries=1)
