"""Bounded diagnostic of one unchanged language Prefill; no hardware ownership.

The authorized caller owns package/preflight/overlay and numerical acceptance.
Serialize finalize() only AFTER the first-token timestamp. Host intervals are
not PL cycle measurements; worker times cannot be summed into request latency.
"""
from contextlib import ExitStack, contextmanager
import copy
import sys

from decode_trace import DecodeTrace, cache_geometry
from transfer_trace import trace_transfer


class PrefillDiagnostic:
    def __init__(self, model, runtime, base_module, *, trace_factory=DecodeTrace,
                 transfer_instrumenter=trace_transfer):
        self.model, self.runtime, self.base = model, runtime, base_module
        self.trace_factory = trace_factory
        self.transfer_instrumenter = transfer_instrumenter
        self.record = None
        self.trace = None

    def _counters(self):
        return {key: getattr(self.runtime, key) for key in
                ('host_calls', 'logical_calls', 'stage_bytes', 'stage_ms', 'scale_retry_count')}

    @contextmanager
    def _family(self):
        owned = '_family' in vars(self.model)
        prior = vars(self.model).get('_family')
        original = self.model._family
        def measured(layer, family, values):
            with self.trace.span('language_family', layer=int(layer), family=family,
                                 input_shape=list(values.shape)):
                return original(layer, family, values)
        self.model._family = measured
        try:
            yield
        finally:
            if owned:
                self.model._family = prior
            else:
                delattr(self.model, '_family')

    def prefill(self, hidden):
        if self.record is not None:
            raise RuntimeError('Bounded diagnosis permits one Prefill request')
        if len(hidden.shape) != 2 or hidden.shape[0] < 1:
            raise ValueError('Expected nonempty rank-2 hidden state')
        self.trace = self.trace_factory()
        self.record = dict(status='RUNNING', input_shape=list(hidden.shape),
                           counters_before=self._counters(),
                           phase_ms_before=copy.deepcopy(self.runtime.phase_ms),
                           numerical_acceptance=False, timing_eligible=False,
                           scope='Instrumented language Prefill only; excludes vision/loading')
        try:
            module = sys.modules[self.model.prefill.__func__.__module__]
            with ExitStack() as stack:
                stack.enter_context(self._family())
                stack.enter_context(self.transfer_instrumenter(self.base, self.trace))
                # Resolve globals from the defining Prefill module, not Decode.
                for attribute in ('rms_norm', 'apply_rope', 'causal_attention_grouped', 'silu'):
                    stack.enter_context(self.trace.wrap(module, attribute, 'ps_' + attribute))
                for attribute in ('_prepare_block', '_parse_buffer', '_parse_into_and_check',
                                  '_launch_prepacked', '_launch_once'):
                    stack.enter_context(self.trace.wrap(self.runtime, attribute, attribute))
                for target, attribute, name in (
                    (self.runtime, '_stage', 'weight_stage'),
                    (self.runtime, 'lm_head', 'lm_head'),
                    (self.base, 'chain_window', 'weight_window_lookup'),
                    (self.base, 'copy_window_to_buffer', 'file_read_copy_sync'),
                    (self.base, 'wait_transaction', 'device_completion_wait'),
                ):
                    stack.enter_context(self.trace.wrap(target, attribute, name))
                with self.trace.span('prefill_call'):
                    result = self.model.prefill(hidden)
            geometry = cache_geometry(result[2])
            if any(row['key_shape'][0] != hidden.shape[0] for row in geometry['layers']):
                raise ValueError('Prefill cache length does not match input tokens')
            self.record.update(status='RECORDED', cache_after=geometry,
                               output_token=int(result[0]))
            return result
        except BaseException as exc:
            self.record.update(status='FAIL', error=f'{type(exc).__name__}: {exc}')
            raise
        finally:
            self.record['counters_after'] = self._counters()
            self.record['counter_delta'] = {
                k: self.record['counters_after'][k] - v
                for k, v in self.record['counters_before'].items()}
            self.record['phase_ms_delta'] = {
                k: v - self.record['phase_ms_before'].get(k, 0)
                for k, v in self.runtime.phase_ms.items()}

    def finalize(self):
        if self.record is None:
            raise RuntimeError('No Prefill request recorded')
        record = dict(self.record)
        record['trace'] = self.trace.report()
        record['cross_thread_addition_allowed'] = False
        record['device_wait_is_pure_pl_compute'] = False
        return record

    def __getattr__(self, name):
        return getattr(self.model, name)
