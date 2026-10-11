"""Borrow the original seven buffers; diagnostic tensor hashes stay outside timers."""
from m432_request_visual import VisualProvider


class TimedVisualProvider(VisualProvider):
    def __init__(self, *args, enabled=False, **kwargs):
        if enabled is not True:
            raise RuntimeError('Timed visual candidate disabled by default')
        super().__init__(*args, **kwargs)
        self.enabled = True

    def __call__(self, index, *args, **kwargs):
        from m431_borrowed_visual import BorrowedVisual
        from m430_timed_scope import LightBatchCheck, TimedPLRangeScope
        if (getattr(self, 'enabled', False) is not True or index not in (0, 1) or self.disposed
                or self.current_owner is not None or self.current_scope is not None
                or self.result.get('language_scope_active', False)):
            raise RuntimeError('Timed visual scope/order/owner invalid')
        owner = scope = None
        def forward():
            self.result['vision_request_active'] = True
            try:
                call = getattr(self, 'original_vision_call', None)
                if call is None:
                    return self.engine.vision(*args, **kwargs)
                return call(self.engine.vision, *args, **kwargs)
            finally:
                self.result['vision_request_active'] = False
        try:
            if index == 0:
                visual = forward()
            else:
                with BorrowedVisual(self.runtime, self.policy, self.base, self.result, enabled=True,
                                    language_active=lambda: self.result.get('language_scope_active', False)) as owner:
                    self.current_owner = owner
                    guard = LightBatchCheck(self.reference, owner.submit)
                    scope = TimedPLRangeScope(self.torch, self.engine.vision.vision.encoder.layers, self.targets,
                        lambda i: dict(chains=self.cases[i]), self.initial, self.host,
                        lambda *unused: None, lambda label: None,
                        lambda i, part, c: owner.stage(i, part, c, self.windows[i][part], self.root), guard)
                    self.current_scope = scope
                    with scope:
                        visual = forward()
                    guard.require_complete()
                if (not scope.complete or not scope.restored or scope.peak_live_layer_scopes != 1
                        or owner.retained or owner.entered or len(owner.rows) != 286 or len(owner.staging) != 22
                        or sum(row['bytes'] for row in owner.staging) != 49020928):
                    raise RuntimeError('Borrowed complete visual timed lifecycle incomplete')
                self.result.update(visual_staging=owner.staging, borrowed_buffer_identity_preserved=True,
                    visual_static_cache_invalidated=self.runtime._programmed_config is None and self.runtime._programmed_weight_addresses is None,
                    visual_bindings_restored=scope.restored, peak_live_visual_layer_scopes=scope.peak_live_layer_scopes,
                    visual_matched_wire_batches=len(guard.seen))
            self.current_owner = self.current_scope = None
            return visual
        finally:
            if owner is not None and (owner.retained or self.policy.active):
                self.current_owner = owner
