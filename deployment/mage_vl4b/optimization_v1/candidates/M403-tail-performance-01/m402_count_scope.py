"""Default-off exact-input stream contract; never changes board evidence."""
import ast
import hashlib
import inspect
from pathlib import Path
import threading

SOURCE_SHA='fae70964171580dc8329700e99aa0b25f27b752e9d4274c5bae72fa19f30cf61'

def validate(original):
    path=Path(inspect.getsourcefile(original))
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA or original.__name__!='expected_physical_calls':
        raise RuntimeError('Frozen original count source differs')
    tree=ast.parse(raw.decode('utf-8-sig'))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='expected_physical_calls')
    namespace=dict(original.__globals__)
    future=ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future,fn],type_ignores=[])),str(path),'exec'),namespace)
    proof=namespace['expected_physical_calls']
    for field in ('co_code','co_consts','co_names','co_varnames','co_freevars'):
        if getattr(original.__code__,field)!=getattr(proof.__code__,field):raise RuntimeError('Original count code identity differs')
    if original(159,1)!=778 or original(30,1)!=162:raise RuntimeError('Original count values differ')
    return dict(original_source_sha256=SOURCE_SHA,original159_calls=778,original30_calls=162,code_equal=True)

class VideoCountScope:
    def __init__(self,server,resident,*,enabled=False):
        if not enabled:raise RuntimeError('M402 stream adapter disabled by default')
        self.server=server;self.resident=resident;self.original=server.expected_physical_calls
        self.proof=validate(self.original);self.thread=threading.get_ident();self.called=0;self.closed=False
        if not resident():raise RuntimeError('Complete resident runtime required')
        server.expected_physical_calls=self.count
    def count(self,tokens,generated):
        if self.closed or self.called or threading.get_ident()!=self.thread or not self.resident():
            raise RuntimeError('Inactive/stale/cross-thread count scope')
        if type(tokens) is not int or type(generated) is not int or (tokens,generated)!=(159,1):
            raise RuntimeError('Only exact159/one-token contract admitted')
        if self.original(tokens,generated)!=778:raise RuntimeError('Original count changed')
        self.called+=1
        return 778-3*4
    def close(self):
        if self.closed:return
        if self.called!=1 or threading.get_ident()!=self.thread or not self.resident() or self.server.expected_physical_calls!=self.count:
            raise RuntimeError('Count binding completion not proven; retain scope')
        self.server.expected_physical_calls=self.original
        if self.server.expected_physical_calls is not self.original:raise RuntimeError('Count binding restore differs')
        self.server=self.resident=self.original=None;self.closed=True
    def report(self):
        return dict(proof=self.proof,accepted_calls=self.called,original_expected=778,candidate_expected=766,
                    closed=self.closed,binding_restored=self.closed,board_evidence_changed=False)
