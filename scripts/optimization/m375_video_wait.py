"""One default-disabled fixed159 Prefill observation, with no new workers."""
from contextlib import contextmanager
from decode_trace import DecodeTrace
from m372_future_wait import observe_runtime

FUTURE_SHA = '205acdb5fd87bc95cb20e986bccff404c1d558617bd54849d9e9947cd039d70f'


class VideoWaitDiagnostic:
    def __init__(self, model, runtime, contract, *, enabled=False):
        if not enabled:
            raise ValueError('Fixed-video wait observation disabled')
        self.model, self.runtime = model, runtime
        self.contract = [dict(x) for x in contract]
        if len(self.contract) != 154 or len({(x['layer'], x['family']) for x in self.contract}) != 154:
            raise ValueError('Fixed-video family contract differs')
        self.original_prefill = model.prefill
        self.trace = DecodeTrace(max_events=4096)
        self.observer = None
        self.started = self.running = False
        self.restored = None
        self.families = []

    def family(self, original, layer, name, values):
        index = len(self.families)
        if not self.running or index >= len(self.contract):
            raise RuntimeError('Observed family escaped bounded Prefill')
        expected = self.contract[index]
        if (layer, name) != (expected['layer'], expected['family']) or values.ndim != 2 or values.shape[0] != 159:
            raise RuntimeError('Fixed-video family identity/order/input differs')
        row = dict(layer=layer, family=name, chain_index=expected['chain_index'], input_shape=list(values.shape))
        self.families.append(row)
        with self.trace.span('family_call', **row):
            return original(layer, name, values)

    def prefill(self, hidden):
        if self.started or list(hidden.shape) != [159, 2560]:
            raise RuntimeError('Exactly one original fixed159 Prefill permitted')
        self.started = True
        saved = [(obj, name, name in vars(obj), vars(obj).get(name))
                 for obj, name in ((self.model, '_family'), (self.runtime, 'language_family_many'),
                                   (self.runtime, '_resolve_pending'))]
        original_family = self.model._family
        try:
            with observe_runtime(self.runtime, self.trace, enabled=True) as observer:
                self.observer = observer
                if observer.future_result_source_sha256 != FUTURE_SHA:
                    raise RuntimeError('Board-tested Future source differs')
                self.model._family = lambda layer, name, values: self.family(original_family, layer, name, values)
                self.running = True
                with self.trace.span('prefill_call'):
                    return self.original_prefill(hidden)
        finally:
            owned, prior = saved[0][2:]
            if owned:
                self.model._family = prior
            elif '_family' in vars(self.model):
                del self.model._family
            self.running = False
            self.restored = all((name in vars(obj)) == owned and (not owned or vars(obj)[name] is prior)
                                for obj, name, owned, prior in saved)
            if not self.restored:
                raise RuntimeError('Wait observation binding restoration failed')

    def report(self):
        if self.running or self.observer is None or not self.restored:
            raise RuntimeError('Wait observation is not closed')
        return dict(status='OBSERVED_FIXED_VIDEO_WAIT_ONLY', input_shape=[159,2560],
                    families=self.families, records=self.observer.records, summary=self.observer.summary(),
                    trace=self.trace.report(), bindings_restored=self.restored,
                    future_result_source_sha256=self.observer.future_result_source_sha256,
                    new_workers=0, extra_cma_allocations=0, performance_eligible=False,
                    scope='Original language Futures only; synchronous retry parsing and LM head excluded. Condition.wait includes wakeup/scheduling and is nested in result wall.')
