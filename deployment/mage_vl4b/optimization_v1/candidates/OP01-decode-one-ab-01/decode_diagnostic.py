"""One-step diagnostic wrapper around the unchanged real model.decode.

No file writes, tensor captures or replacement arithmetic during the call.
Board runner must serialize report AFTER the token-ready timestamp.
"""
from contextlib import ExitStack, contextmanager
import copy
import sys
from decode_trace import DecodeTrace, cache_geometry
from transfer_trace import trace_transfer


class DecodeDiagnostic:
    def __init__(self, model, runtime, base_module, *, transfer_instrumenter=trace_transfer,
                 detailed_runtime=True, checkpoint_directory=None, checkpoint_identity=None,
                 trace_factory=DecodeTrace):
        self.model, self.runtime, self.base = model, runtime, base_module
        self.transfer_instrumenter=transfer_instrumenter
        self.detailed_runtime=detailed_runtime
        self.records = []
        self.traces = []
        self.checkpoint_directory=checkpoint_directory
        self.checkpoint_identity=checkpoint_identity
        self.checkpoint=None
        self.trace_factory=trace_factory

    def prefill(self, hidden):
        result=self.model.prefill(hidden)
        if self.checkpoint_directory is not None:
            from decode_checkpoint import save_checkpoint
            token,_,cache=result
            self.checkpoint=save_checkpoint(self.checkpoint_directory,cache,int(token),self.checkpoint_identity)
        return result

    def finalize(self):
        # Explicitly after token-ready/request completion, never in Decode.
        for record,trace in zip(self.records,self.traces):
            record['trace']=trace.report()
        return dict(steps=self.records,checkpoint=self.checkpoint,timing_eligible=False)

    def _counters(self):
        return {key: getattr(self.runtime, key) for key in
                ('host_calls', 'logical_calls', 'stage_bytes', 'stage_ms', 'scale_retry_count')}

    @contextmanager
    def _family(self, trace):
        model = self.model
        owned = '_family' in vars(model)
        prior = vars(model).get('_family')
        original = model._family
        def measured(layer, family, values):
            with trace.span('language_family', layer=int(layer), family=family,
                            input_shape=list(values.shape)):
                return original(layer, family, values)
        model._family = measured
        try:
            yield
        finally:
            if owned: model._family = prior
            else: delattr(model, '_family')

    def decode(self, token, cache):
        if self.records:
            raise RuntimeError('Bounded diagnosis permits one Decode step')
        trace = self.trace_factory()
        self.traces.append(trace)
        record = dict(status='RUNNING', input_token=int(token),
                      cache_before=cache_geometry(cache), counters_before=self._counters(),
                      numerical_acceptance=False, timing_scope='Instrumented diagnostic only')
        self.records.append(record)
        if self.detailed_runtime:
            record['phase_ms_before']=copy.deepcopy(self.runtime.phase_ms)
        try:
            with ExitStack() as stack:
                stack.enter_context(self._family(trace))
                stack.enter_context(self.transfer_instrumenter(self.base,trace))
                if self.detailed_runtime:
                    # Resolve the defining module of the inherited Decode,
                    # rather than changing unrelated Prefill module globals.
                    module=sys.modules[self.model.decode.__func__.__module__]
                    for attribute in ('rms_norm','apply_rope','causal_attention','silu'):
                        stack.enter_context(trace.wrap(module,attribute,'ps_'+attribute))
                    for attribute in ('_prepare_block','_parse_buffer','_parse_into_and_check',
                                      '_launch_prepacked','_launch_once'):
                        stack.enter_context(trace.wrap(self.runtime,attribute,attribute))
                for target, attribute, name in (
                    (self.runtime, '_stage', 'weight_stage'),
                    (self.runtime, 'lm_head', 'lm_head'),
                    (self.base, 'chain_window', 'weight_window_lookup'),
                    (self.base, 'copy_window_to_buffer', 'file_read_copy_sync'),
                    (self.base, 'wait_transaction', 'device_completion_wait'),
                ):
                    stack.enter_context(trace.wrap(target, attribute, name))
                with trace.span('decode_call'):
                    result = self.model.decode(token, cache)
            record['cache_after'] = cache_geometry(cache)
            before = record['cache_before']; after = record['cache_after']
            if (before['cache_identity'] != after['cache_identity'] or
                    len(before['layers']) != len(after['layers']) or
                    any(b['key_shape'][0]+1 != a['key_shape'][0]
                        for b,a in zip(before['layers'],after['layers']))):
                raise ValueError('Decode did not extend the same cache by one')
            record['status'] = 'RECORDED'
            return result
        except BaseException as exc:
            record.update(status='FAIL', error=f'{type(exc).__name__}: {exc}')
            raise
        finally:
            record['counters_after'] = self._counters()
            record['counter_delta'] = {k:record['counters_after'][k]-v
                                       for k,v in record['counters_before'].items()}
            if self.detailed_runtime:
                record['phase_ms_delta']={key:value-record['phase_ms_before'].get(key,0)
                                          for key,value in self.runtime.phase_ms.items()}
                record['phase_note']='Counters can overlap; use per-thread interval tree for exclusive attribution'

    def __getattr__(self, name):
        return getattr(self.model, name)
