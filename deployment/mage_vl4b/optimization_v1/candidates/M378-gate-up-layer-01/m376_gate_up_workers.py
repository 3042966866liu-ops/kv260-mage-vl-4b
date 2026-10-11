"""Default-disabled, instance-local two-worker gate_up schedule experiment.

The only scheduler AST change is the parse executor's worker limit. The
original packer, parser, output slots, resolve/retry and drain order remain.
"""
import ast
import copy
import hashlib
import inspect
import textwrap
import threading
import time
from types import MethodType

PINNED = {
    'language_family_many': '6bcb23fb211b1d411802380799d0a1998d081579811cc8a72635ad01053407f7',
    '_resolve_pending': '7798fae8ad951d777d6d1a46cf89650517f4a7a35d01b7c2d1376f401ff00e55',
    '_parse_buffer': '4692cc33264b87f613ae472e6fd1357a1ac45d93c7aca21071a065777b273686',
    '_parse_into_and_check': 'f1f6047ac16650765c42336c10d4c345d22d55116c16d4963092c98350306595',
    '_record_phase': 'ad6cafb8d2680fb605ad6475f2723b9f78d83f1edafd0e17faf8f98303ae50bc',
}

def normalized(function):
    try:source=textwrap.dedent(inspect.getsource(function)).strip().replace('\r\n', '\n')
    except (OSError,TypeError) as exc:raise RuntimeError('Runtime source unavailable') from exc
    lines=source.splitlines()
    starts=[i for i,line in enumerate(lines) if line.startswith('def ')]
    if len(starts)!=1:raise RuntimeError('Runtime source is not one reviewed function')
    return '\n'.join(lines[starts[0]:])

class GateUpWorkers:
    def __init__(self, runtime, *, workers=2, enabled=False):
        if enabled is not True or type(workers) is not int or workers not in (1, 2):
            raise ValueError('Explicit gate_up worker variant 1 or2 required')
        sources = {n: normalized(getattr(runtime,n)) for n in PINNED}
        if any(hashlib.sha256(s.encode('utf-8')).hexdigest()!=PINNED[n] for n,s in sources.items()):
            raise RuntimeError('Unreviewed runtime source; no bindings changed')
        tree=ast.parse(sources['language_family_many']); original=copy.deepcopy(tree)
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and
               isinstance(n.func,ast.Name) and n.func.id=='ThreadPoolExecutor' and
               any(k.arg=='thread_name_prefix' and isinstance(k.value,ast.Constant) and
                   k.value.value=='m238-parse' for k in n.keywords)]
        if len(calls)!=1:raise RuntimeError('Parse executor identity ambiguous')
        keyword=next(k for k in calls[0].keywords if k.arg=='max_workers')
        if not isinstance(keyword.value,ast.Constant) or keyword.value.value!=1:
            raise RuntimeError('Original parse width differs')
        previous=copy.deepcopy(keyword.value)
        keyword.value=ast.Constant(workers)
        changed=copy.deepcopy(tree)
        keyword.value=previous
        if ast.dump(tree)!=ast.dump(original):raise RuntimeError('Scheduler change escaped worker limit')
        namespace=dict(runtime.language_family_many.__func__.__globals__)
        exec(compile(ast.fix_missing_locations(changed),'<m376-pinned-worker-limit-only>','exec'),namespace)
        self.runtime=runtime;self.workers=workers;self.owner=threading.get_ident()
        self.candidate=namespace['language_family_many']
        self.original_family=runtime.language_family_many
        self.original_record=runtime._record_phase
        self.lock=threading.Lock();self.active=False;self.entered=False;self.restored=False
        self.gate_up_calls=0

    def _family(self, runtime, layer, family, values):
        if threading.get_ident()!=self.owner or self.active:
            raise RuntimeError('One foreground family owner required')
        if family!='gate_up':return self.original_family(layer,family,values)
        self.active=True
        try:
            output=self.candidate(runtime,layer,family,values)
            self.gate_up_calls+=1
            return output
        finally:
            # The pinned executor context joins both parser workers first,
            # including error paths. A stuck worker keeps this call/process.
            self.active=False

    def _record(self, runtime, chain, phase, started):
        if chain.get('family')!='gate_up' or phase!='parse':
            return self.original_record(chain,phase,started)
        elapsed=(time.perf_counter()-started)*1000.0
        with self.lock:
            runtime.phase_ms[phase]+=elapsed
            runtime.phase_calls[phase]+=1
            runtime.family_phase_ms[runtime._family_key(chain)][phase]+=elapsed

    def __enter__(self):
        if self.entered or threading.get_ident()!=self.owner:raise RuntimeError('Scope is single use')
        self.entered=True
        self.prior={n:(n in vars(self.runtime),vars(self.runtime).get(n))
                    for n in ('language_family_many','_record_phase')}
        self.bound_family=MethodType(self._family,self.runtime)
        self.bound_record=MethodType(self._record,self.runtime)
        self.runtime.language_family_many=self.bound_family
        self.runtime._record_phase=self.bound_record
        return self

    def __exit__(self,*exc):
        if self.active:raise RuntimeError('Family workers still owned; retain runtime')
        if (self.runtime.language_family_many is not self.bound_family or
                self.runtime._record_phase is not self.bound_record):
            raise RuntimeError('Bindings changed by another owner; retain runtime')
        for name,(owned,value) in self.prior.items():
            if owned:setattr(self.runtime,name,value)
            else:delattr(self.runtime,name)
        self.restored=True

    def report(self):
        if not self.restored:raise RuntimeError('Worker scope not restored')
        return dict(scope='gate_up parse executor width only; original parser and retries',
                    parse_workers=self.workers,gate_up_calls=self.gate_up_calls,
                    bindings_restored=True,extra_dma_allocations=0,
                    pending_output_slots=2,statistics_lock=True,
                    source_sha256=dict(PINNED),performance_pass=False)
