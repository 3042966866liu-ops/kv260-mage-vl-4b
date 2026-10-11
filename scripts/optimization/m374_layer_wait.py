"""One bounded single-layer observation; no hardware ownership or new workers."""
from contextlib import contextmanager
from decode_trace import DecodeTrace
from m372_future_wait import observe_runtime

FAMILIES = ('q','kv','attention_out','gate_up','mlp_down')
FUTURE_SHA = '205acdb5fd87bc95cb20e986bccff404c1d558617bd54849d9e9947cd039d70f'

class LayerWaitDiagnostic:
    def __init__(self, runtime, *, enabled=False):
        if not enabled: raise ValueError('Single-layer wait observation disabled')
        self.runtime=runtime; self.trace=DecodeTrace(max_events=256)
        self.observer=None; self.running=False; self.started=False
        self.families=[]; self.restored=None

    @contextmanager
    def family(self, layer, name, values):
        if not self.running or layer!=0 or len(self.families)>=5 or name!=FAMILIES[len(self.families)]:
            raise RuntimeError('Observed layer/family sequence escaped')
        self.families.append(name)
        with self.trace.span('family_call', layer=layer, family=name, input_shape=list(values.shape)):
            yield

    def run(self, call):
        if self.started: raise RuntimeError('One observed layer permitted')
        self.started=True
        names=('language_family_many','_resolve_pending')
        prior={n:(n in vars(self.runtime),vars(self.runtime).get(n)) for n in names}
        try:
            with observe_runtime(self.runtime,self.trace,enabled=True) as observer:
                self.observer=observer
                if observer.future_result_source_sha256!=FUTURE_SHA: raise RuntimeError('Board-tested Future source differs')
                self.running=True
                with self.trace.span('layer_call'):
                    return call()
        finally:
            self.running=False
            self.restored=all((n in vars(self.runtime))==owned and (not owned or vars(self.runtime)[n] is value)
                              for n,(owned,value) in prior.items())
            if not self.restored: raise RuntimeError('Runtime binding restoration failed')

    def report(self):
        if self.running or self.observer is None or not self.restored: raise RuntimeError('Observation not closed')
        return dict(status='OBSERVED_LAYER_WAIT_ONLY',families=self.families,records=self.observer.records,
            summary=self.observer.summary(),trace=self.trace.report(),bindings_restored=self.restored,
            future_result_source_sha256=self.observer.future_result_source_sha256,
            new_workers=0,extra_cma_allocations=0,performance_eligible=False,
            scope='Condition.wait includes wakeup/scheduling; nested in result wall. Worker time cannot be added.')
